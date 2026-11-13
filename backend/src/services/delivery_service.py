"""投递执行：把日报按渠道发出去，并把每次尝试写回投递任务。

语义约定：
  - 只有 status != sent 的任务会被尝试；已送达的一律跳过（不重发、不新增记录）。
  - 每次尝试 attempts + 1；失败把原因写进 last_error，成功清空。
  - 全部任务送达后日报才进入 published（见 refresh_report_status）。

真实渠道：配置 FEISHU_WEBHOOK_URL / WECOM_WEBHOOK_URL / EMAIL_WEBHOOK_URL 后走真实
HTTP 投递（5 秒超时，超时/非 2xx 记为失败原因）；未配置时模拟成功，演示环境可直接跑通。
DELIVERY_FAIL_CHANNELS=wecom,email 可注入失败，用于演示「超时 → 失败 → 单路重试」链路。
"""
from __future__ import annotations

import json
import socket
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from src.config.settings import settings
from src.constants.enums import DeliveryStatus, ReportStatus
from src.models.report_delivery import ReportDelivery
from src.models.report_issue import ReportIssue
from src.utils.logger import get_logger
from src.utils.timeutil import utcnow

logger = get_logger("delivery")


class DeliveryError(Exception):
    """单路投递失败，message 就是给用户看的失败原因。"""


def _webhook_urls() -> dict[str, str]:
    return {
        "feishu": settings.feishu_webhook_url,
        "email": settings.email_webhook_url,
        "wecom": settings.wecom_webhook_url,
    }


def _fail_injected_channels() -> set[str]:
    return {item.strip() for item in settings.delivery_fail_channels.split(",") if item.strip()}


def _build_payload(report: ReportIssue) -> dict:
    return {
        "msg_type": "daily_report",
        "title": report.title,
        "report_date": report.report_date.isoformat(),
        "metric_code": report.metric_code,
        "conclusion": report.conclusion,
        "markdown": report.markdown,
    }


def _post_webhook(url: str, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urlrequest.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urlrequest.urlopen(req, timeout=settings.delivery_timeout_seconds) as resp:
            if resp.status >= 400:
                raise DeliveryError(f"渠道返回 HTTP {resp.status}")
    except HTTPError as exc:
        raise DeliveryError(f"渠道返回 HTTP {exc.code}") from exc
    except (URLError, socket.timeout, TimeoutError) as exc:
        reason = getattr(exc, "reason", exc)
        raise DeliveryError(f"网络超时或不可达：{reason}") from exc


def send_channel_message(channel: str, target: str, report: ReportIssue) -> str:
    """发一路；失败抛 DeliveryError。返回投递方式说明（模拟 / 真实 webhook）。"""
    if channel in _fail_injected_channels():
        raise DeliveryError("网络超时（演示故障注入 DELIVERY_FAIL_CHANNELS）")
    url = _webhook_urls().get(channel, "")
    if not url:
        return "模拟投递（未配置 webhook）"
    _post_webhook(url, _build_payload(report))
    return "webhook 已受理"


def attempt_delivery(task: ReportDelivery, report: ReportIssue) -> bool:
    """尝试一次并写回任务状态；返回是否送达。"""
    task.attempts += 1
    task.last_attempt_at = utcnow()
    try:
        note = send_channel_message(task.channel, task.target, report)
    except DeliveryError as exc:
        task.status = DeliveryStatus.FAILED.value
        task.last_error = str(exc)
        logger.warning("delivery failed: report=%s channel=%s reason=%s", report.id, task.channel, exc)
        return False
    task.status = DeliveryStatus.SENT.value
    task.delivered_at = utcnow()
    task.last_error = None
    logger.info("delivered: report=%s channel=%s via=%s", report.id, task.channel, note)
    return True


def refresh_report_status(report: ReportIssue) -> None:
    """状态不变式：全部任务送达才 published；否则投递中；无任务回到草稿。"""
    tasks = list(report.deliveries)
    if not tasks:
        report.status = ReportStatus.DRAFT.value
        report.published_at = None
        return
    if all(task.status == DeliveryStatus.SENT.value for task in tasks):
        if report.status != ReportStatus.PUBLISHED.value:
            report.published_at = utcnow()
        report.status = ReportStatus.PUBLISHED.value
    else:
        report.status = ReportStatus.DELIVERING.value
        report.published_at = None


def dispatch_pending(report: ReportIssue) -> dict:
    """续投全部未送达任务（已送达的跳过），并刷新日报发布状态。"""
    summary = {"attempted": 0, "sent": 0, "failed": 0, "skipped_sent": 0}
    for task in report.deliveries:
        if task.status == DeliveryStatus.SENT.value:
            summary["skipped_sent"] += 1
            continue
        summary["attempted"] += 1
        if attempt_delivery(task, report):
            summary["sent"] += 1
        else:
            summary["failed"] += 1
    refresh_report_status(report)
    return summary
