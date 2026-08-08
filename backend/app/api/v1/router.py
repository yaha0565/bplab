"""API v1 路由聚合"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.commissions import router as commissions_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.records import router as records_router
from app.api.v1.reports import router as reports_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.organizations import router as organizations_router
from app.api.v1.methods import router as methods_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.equipment import router as equipment_router
from app.api.v1.templates import router as templates_router
from app.api.v1.export import router as export_router
from app.api.v1.experiment_config import router as experiment_config_router
from app.api.v1.returns import router as returns_router
from app.api.v1.traceability import router as traceability_router
from app.api.v1.incidents import router as incidents_router
from app.api.v1.objections import router as objections_router
from app.api.v1.hazardous_waste import router as hazardous_waste_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.signatures import router as signatures_router
from app.api.v1.system import router as system_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(commissions_router)
api_router.include_router(tasks_router)
api_router.include_router(records_router)
api_router.include_router(reports_router)
api_router.include_router(dashboard_router)
api_router.include_router(organizations_router)
api_router.include_router(methods_router)
api_router.include_router(catalog_router)
api_router.include_router(equipment_router)
api_router.include_router(templates_router)
api_router.include_router(export_router)
api_router.include_router(experiment_config_router)
api_router.include_router(returns_router)
api_router.include_router(traceability_router)
api_router.include_router(incidents_router)
api_router.include_router(objections_router)
api_router.include_router(hazardous_waste_router)
api_router.include_router(notifications_router)
api_router.include_router(signatures_router)
api_router.include_router(system_router)
