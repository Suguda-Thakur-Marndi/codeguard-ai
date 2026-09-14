"""API v1 master router aggregating all sub-resources."""

from fastapi import APIRouter

from app.api.v1.endpoints.approvals import router as approvals_router
from app.api.v1.endpoints.audit import router as audit_router
from app.api.v1.endpoints.benchmarks import router as benchmarks_router
from app.api.v1.endpoints.code_intelligence import router as code_intelligence_router
from app.api.v1.endpoints.findings import router as findings_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.organizations import router as organizations_router
from app.api.v1.endpoints.policies import router as policies_router
from app.api.v1.endpoints.publications import router as publications_router
from app.api.v1.endpoints.pull_requests import router as pull_requests_router
from app.api.v1.endpoints.repositories import router as repositories_router
from app.api.v1.endpoints.review_jobs import router as review_jobs_router
from app.api.v1.endpoints.webhooks import router as webhooks_router

api_v1_router = APIRouter(prefix="/api/v1")

# Mount sub-routers
api_v1_router.include_router(health_router)
api_v1_router.include_router(webhooks_router)
api_v1_router.include_router(organizations_router)
api_v1_router.include_router(repositories_router)
api_v1_router.include_router(code_intelligence_router)
api_v1_router.include_router(pull_requests_router)
api_v1_router.include_router(review_jobs_router)
api_v1_router.include_router(findings_router)
api_v1_router.include_router(approvals_router)
api_v1_router.include_router(publications_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(policies_router)
api_v1_router.include_router(benchmarks_router)

