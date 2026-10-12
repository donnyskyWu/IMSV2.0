# app/api/health.py - Health check endpoint (FP-A01-03)
"""
Health check endpoint.

Input: GET /health (anonymous)
Output: {code:0, data:{status:"UP"|"DEGRADED", db:"UP"|"DOWN", redis:"UP"|"DOWN"|"MEMORY",
         footballLive:"UP"|"DOWN"|"DISABLED", version}}

Rules per FP-A01-03:
- IMS main DB DOWN -> status=DOWN, HTTP 503
- Redis or Football DOWN -> DEGRADED (HTTP 200)
- Never output connection strings
"""

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.response import CommonResult

router = APIRouter()


class HealthData(BaseModel):
    """Health check response data."""
    status: str
    db: str
    redis: str
    football_live: str
    version: str

    class Config:
        populate_by_name = True


@router.get(
    "/health",
    response_model=CommonResult[HealthData],
    tags=["健康检查"],
    summary="健康检查",
)
async def health_check() -> CommonResult[HealthData]:
    """
    Health check endpoint.

    Returns system health status. Does not expose any connection strings.
    """
    from app.core.cache import CacheHealth
    from app.db.session import DatabaseHealth

    # Check IMS database
    db_up = DatabaseHealth.check_ims()
    db_status = "UP" if db_up else "DOWN"

    # Check Redis
    redis_up, redis_status = CacheHealth.check()

    # Check Football database
    football_up, football_status = DatabaseHealth.check_football()

    # Determine overall status
    if not db_up:
        overall_status = "DOWN"
        http_status = 503
    elif not redis_up or not football_up:
        overall_status = "DEGRADED"
        http_status = 200
    else:
        overall_status = "UP"
        http_status = 200

    data = HealthData(
        status=overall_status,
        db=db_status,
        redis=redis_status,
        football_live=football_status,
        version=__version__,
    )

    # Note: FastAPI doesn't directly support dynamic status codes in the same response model
    # For 503, we handle this specially
    result = CommonResult.success(data=data)

    if http_status == 503:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content=result.model_dump(by_alias=True),
        )

    return result
