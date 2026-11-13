"""算法阈值与约束（口径集中定义，不散落在 service）。"""
from __future__ import annotations

RATE_WINDOW_SECONDS = 60

# 稳健异常：|Δ| / MAD 超过该阈值判为异常
ANOMALY_MAD_THRESHOLD = 3.0
# 达到该 z 值升级为「重大」
ANOMALY_CRITICAL_THRESHOLD = 5.0
# 基线候选最少需要的同星期历史点数
MIN_BASELINE_POINTS = 3
# 节假日位移：允许 ±N 天窗口内找同类节点
HOLIDAY_SHIFT_WINDOW_DAYS = 3

# 组合扫描：参与扫描的维度个数上限（防组合爆炸，5 维全组合 576 个，只扫前 3 维）
MAX_COMBO_DIMENSIONS = 3
# 单次归因最多保留的因子数
MAX_FACTORS = 40
# 默认 Top-N
DEFAULT_TOP_N = 8
# 解释度低于该比例时批次标记为 partial（残差过大要显式暴露）
EXPLAINED_PARTIAL_THRESHOLD = 0.70
# 日报最多分发渠道数
MAX_DELIVERY_TARGETS = 4
