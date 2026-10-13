# app/main.py - Application factory and startup (FP-A01-01, FP-A01-02, FP-A01-03)
"""
FastAPI application factory.

Rules per FP-A01-01:
- Environment from IMS_ENV (dev/test/e2e/prod) + config file + env vars
- Config groups: db, football_live, redis, jwt, file, dingtalk, etc.
- Missing required -> startup failure with field names (not values)
- prod disables OpenAPI and debug; secrets never in logs or /health
- dev allows Redis fallback to memory; test/e2e/prod require Redis

Rules per FP-A01-02:
- Auto-register domain routers at /admin-api/ims/<domain>
- Non-/health routes must start with /admin-api/ims/
- Business routes must declare permission or be whitelisted
- Anonymous whitelist: login, refresh, SSO, DingTalk callback, /health
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.context import RequestContext, ctx
from app.core.errors import BizError
from app.core.response import CommonResult

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting IMS Backend ({settings.env})")

    # Initialize database
    from app.db.session import init_db
    init_db()

    # Initialize Redis (or fallback in dev)
    from app.core.cache import init_cache
    init_cache()

    yield

    # Shutdown
    logger.info("Shutting down IMS Backend")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # 延迟导入，避免会话/鉴权依赖在模块加载时拉回 main。
    from app.api.deps import enforce_password_reset, get_current_user_optional
    from app.db.session import get_db

    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        lifespan=lifespan,
        # get_db 必须在鉴权前面：校验令牌时要读库。两者都挂在应用上，
        # 业务路由不用各自声明，匿名接口没有令牌时鉴权依赖直接放过。
        # 改密标记要在令牌解析之后看，所以排在鉴权依赖后面。
        dependencies=[
            Depends(get_db),
            Depends(get_current_user_optional),
            Depends(enforce_password_reset),
        ],
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_prod else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request context middleware
    @app.middleware("http")
    async def context_middleware(request: Request, call_next):
        """Set up request context with trace ID."""
        trace_id = request.headers.get("X-Trace-Id") or None
        context = RequestContext(
            trace_id=trace_id or str(__import__("uuid").uuid4()),
            client_ip=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent") or "",
        )
        ctx.set(context)

        try:
            response = await call_next(request)
            # Add trace ID to response
            response.headers["X-Trace-Id"] = context.trace_id
            return response
        finally:
            ctx.reset()

    # Exception handlers
    @app.exception_handler(BizError)
    async def biz_error_handler(request: Request, exc: BizError) -> JSONResponse:
        """Handle business exceptions."""
        # HTTP 401 for auth-related errors (1002, 1003)
        status_code = 401 if exc.code in (1002, 1003) else 200

        return JSONResponse(
            status_code=status_code,
            content=CommonResult(code=exc.code, msg=exc.msg, data=exc.data).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Handle request validation errors -> 1001."""
        field_errors = []
        for error in exc.errors():
            loc = error.get("loc", [])
            field = loc[-1] if loc else "unknown"
            # Convert snake_case to camelCase
            from app.core.serialization import snake_to_camel
            if isinstance(field, str):
                field = snake_to_camel(field)
            message = error.get("msg", "参数校验失败")
            field_errors.append({"field": str(field), "message": message})

        return JSONResponse(
            status_code=200,
            content=CommonResult(
                code=1001,
                msg="参数校验失败",
                data={"fieldErrors": field_errors},
            ).model_dump(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Handle HTTP exceptions."""
        if exc.status_code == 404:
            return JSONResponse(
                status_code=200,
                content=CommonResult(code=1504, msg="资源不可用").model_dump(),
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=CommonResult(code=5007, msg="系统繁忙，请稍后再试").model_dump(),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions -> 5007."""
        # Log with trace ID
        logger.exception(
            f"Unhandled exception [trace_id={ctx.trace_id}]: {exc}",
            exc_info=exc,
        )

        # Never expose stack trace or internal details
        return JSONResponse(
            status_code=200,
            content=CommonResult(code=5007, msg="系统繁忙，请稍后再试").model_dump(),
        )

    # Register routes
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    """Register all domain routers."""
    from app.api.auth import router as auth_router
    from app.api.health import router as health_router
    from app.api.system import router as system_router

    # Health check (anonymous)
    app.include_router(health_router)

    # Auth routes (/admin-api/ims/auth)
    app.include_router(auth_router, prefix="/admin-api/ims/auth", tags=["认证"])

    # System routes (/admin-api/ims/system)
    app.include_router(system_router, prefix="/admin-api/ims/system", tags=["系统管理"])

    # Demo routes - test environment only (FP-B08-08)
    if settings.env == "test":
        from app.api.demo import router as demo_router
        app.include_router(demo_router, prefix="/admin-api/ims/demo", tags=["演示"])


def validate_routes(app: FastAPI) -> None:
    """
    Validate that all routes follow naming conventions.

    Per FP-A01-02:
    - All routes except /health must start with /admin-api/ims/
    - Business routes must declare permission or be whitelisted
    """
    allowed_prefixes = ["/health", "/admin-api/ims/", "/docs", "/redoc", "/openapi.json"]

    for route in app.routes:
        path = getattr(route, "path", "")
        if not path:
            continue

        if not any(path.startswith(prefix) for prefix in allowed_prefixes):
            raise RuntimeError(
                f"Route {path} does not start with /admin-api/ims/ "
                "(only /health is allowed outside this prefix)"
            )


# Application instance
app = create_app()
