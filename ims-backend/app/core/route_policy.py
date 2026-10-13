# app/core/route_policy.py - Startup route policy (FP-A01, FP-D03, FP-C02)
"""Fail startup when anonymous, permission, or scope declarations are wrong."""

from typing import Any, Iterable, Optional

ANONYMOUS_WHITELIST = {
    "/health",
    "/admin-api/ims/auth/login",
    "/admin-api/ims/auth/login-options",
    "/admin-api/ims/auth/sso/dingtalk/redirect",
    "/admin-api/ims/auth/sso/dingtalk/callback",
    "/admin-api/ims/auth/sso/dingtalk/authorize-params",
    "/admin-api/ims/auth/sso/dingtalk/h5-login",
}

DECLARED_LOGIN_ONLY = {
    "/admin-api/ims/auth/me",
    "/admin-api/ims/auth/password/change",
    "/admin-api/ims/auth/workbench/dashboard",
    "/admin-api/ims/todo/my/page",
    "/admin-api/ims/todo/my/count",
    "/admin-api/ims/todo/my/get",
    "/admin-api/ims/todo/my/close",
    "/admin-api/ims/message/my/page",
    "/admin-api/ims/message/my/unread-count",
    "/admin-api/ims/message/my/get",
    "/admin-api/ims/message/my/read",
    "/admin-api/ims/message/my/read-all",
    "/admin-api/ims/system/dict-type/list",
    "/admin-api/ims/system/user/simple-page",
    "/admin-api/ims/system/role/simple-list",
    "/admin-api/ims/demo/error",
}


def validate_anonymous(routes: Iterable[Any]) -> None:
    """Anonymous routes outside the whitelist fail startup."""
    for route in routes:
        if not getattr(route, "anonymous", False):
            continue
        if getattr(route, "path", "") not in ANONYMOUS_WHITELIST:
            raise RuntimeError(
                f"Anonymous route {route.path} is not in the whitelist"
            )


def validate_business_permissions(
    routes: Iterable[Any],
    menu_codes: Optional[set[str]] = None,
) -> None:
    """Business routes must declare a permission that exists in the menu seed."""
    known = menu_codes if menu_codes is not None else set()
    for route in routes:
        if getattr(route, "anonymous", False) or getattr(route, "login_only", False):
            continue
        perm = getattr(route, "perm_code", None)
        if not perm:
            raise RuntimeError(f"Route {route.path} does not declare a permission")
        if menu_codes is not None and perm not in known:
            raise RuntimeError(f"Route {route.path} uses unknown permission {perm}")


def validate_scope_models(routes: Iterable[Any]) -> None:
    """A route scope model must declare ``__scope_fields__``."""
    for route in routes:
        model = getattr(route, "scope_model", None)
        if model is None:
            continue
        fields = getattr(model, "__scope_fields__", None)
        if not fields:
            raise RuntimeError(
                f"scope_model {getattr(model, '__name__', model)} has no __scope_fields__"
            )


def _dep_names(route: Any) -> list[str]:
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return []
    names = []
    for dep in dependant.dependencies:
        call = getattr(dep, "call", None)
        names.append(getattr(call, "__name__", "") or "")
    return names


def _iter_routes(router: Any, prefix: str = ""):
    """Yield ``(full_path, route)`` including routers mounted via include_router."""
    for route in getattr(router, "routes", []):
        included = getattr(route, "include_context", None)
        child = getattr(included, "included_router", None) if included is not None else None
        if child is not None:
            child_prefix = prefix + (getattr(included, "prefix", "") or "")
            yield from _iter_routes(child, child_prefix)
            continue
        path = getattr(route, "path", None)
        if not path or not hasattr(route, "endpoint"):
            continue
        yield prefix + path, route


def export_login_only(app: Any) -> set[str]:
    """Paths that are login-only and do not declare a permission dependency."""
    found = set()
    router = getattr(app, "router", app)
    for path, route in _iter_routes(router):
        endpoint = getattr(route, "endpoint", None)
        names = _dep_names(route)
        marked = bool(endpoint and getattr(endpoint, "__login_only__", False))
        login = "require_login" in names or marked
        permitted = any(name == "dependency" for name in names)
        if login and not permitted and path:
            found.add(path)
    return found


def assert_login_only_matches(app: Any) -> None:
    """Exported login-only paths must match the code declaration."""
    found = export_login_only(app)
    if found != DECLARED_LOGIN_ONLY:
        raise AssertionError(f"login-only mismatch found={found} declared={DECLARED_LOGIN_ONLY}")
