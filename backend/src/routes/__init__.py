"""路由聚合：统一 /api 前缀（Nginx 反代时剥掉 /api）。"""
from fastapi import APIRouter

from src.routes.attributions import router as attributions_router
from src.routes.audit import router as audit_router
from src.routes.auth import router as auth_router
from src.routes.baselines import router as baselines_router
from src.routes.exports import router as exports_router
from src.routes.health import router as health_router
from src.routes.metrics import router as metrics_router
from src.routes.reports import router as reports_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(metrics_router)
api_router.include_router(baselines_router)
api_router.include_router(attributions_router)
api_router.include_router(reports_router)
api_router.include_router(exports_router)
api_router.include_router(audit_router)
