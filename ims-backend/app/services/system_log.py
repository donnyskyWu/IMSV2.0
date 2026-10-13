# app/services/system_log.py - Log query service (B2-M02)
"""
Log query service.

Implements L-01 to L-04 from the B2 system management module:
- Operation log list and detail
- Login log list
- Log export
"""

from typing import Any, Optional

from app.core.context import ctx
from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult
from app.db.session import get_db_session


class SystemLogService:
    """Log query service for B2 system management."""

    async def get_operate_log_page(
        self,
        page_param: PageParam,
        module: Optional[str] = None,
        operation: Optional[str] = None,
        operator_name: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> PageResult:
        """Get paginated operation log list (L-01)."""
        from app.domains.sys.models import OperateLog
        
        session = get_db_session()
        tenant_id = ctx.tenant_id

        query = session.query(OperateLog).filter(
            OperateLog.tenant_id == tenant_id,
            OperateLog.deleted == 0,
        )

        if module:
            query = query.filter(OperateLog.module == module)

        if operation:
            query = query.filter(OperateLog.operation.like(f"%{operation}%"))

        if operator_name:
            query = query.filter(OperateLog.operator_name.like(f"%{operator_name}%"))

        if start_time:
            query = query.filter(OperateLog.create_time >= start_time)

        if end_time:
            query = query.filter(OperateLog.create_time <= end_time)

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        logs = query.order_by(OperateLog.create_time.desc()).offset(offset).limit(
            page_param.page_size
        ).all()

        items = []
        for log in logs:
            items.append({
                "id": str(log.id),
                "module": log.module,
                "operation": log.operation,
                "operator_name": log.operator_name,
                "result": log.result,
                "ip": log.ip,
                "duration_ms": log.duration_ms,
                "create_time": log.create_time.isoformat() if log.create_time else None,
            })

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    async def get_operate_log_detail(self, log_id: str) -> dict[str, Any]:
        """Get operation log detail (L-02)."""
        from app.domains.sys.models import OperateLog
        
        session = get_db_session()
        tenant_id = ctx.tenant_id
        log_id_int = int(log_id)

        log = session.query(OperateLog).filter(
            OperateLog.id == log_id_int,
            OperateLog.tenant_id == tenant_id,
            OperateLog.deleted == 0,
        ).first()

        if not log:
            raise BizError(1504)

        return {
            "id": str(log.id),
            "module": log.module,
            "operation": log.operation,
            "object_type": log.object_type,
            "object_id": log.object_id,
            "operator_name": log.operator_name,
            "result": log.result,
            "error_code": log.error_code,
            "ip": log.ip,
            "duration_ms": log.duration_ms,
            "request_path": log.request_path,
            "request_method": log.request_method,
            "request_params": log.request_params,
            "create_time": log.create_time.isoformat() if log.create_time else None,
        }

    async def get_login_log_page(
        self,
        page_param: PageParam,
        username: Optional[str] = None,
        result: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> PageResult:
        """Get paginated login log list (L-03)."""
        from app.domains.sys.models import LoginLog
        
        session = get_db_session()
        tenant_id = ctx.tenant_id

        query = session.query(LoginLog).filter(
            LoginLog.tenant_id == tenant_id,
            LoginLog.deleted == 0,
        )

        if username:
            query = query.filter(LoginLog.username.like(f"%{username}%"))

        if result:
            query = query.filter(LoginLog.result == result)

        if start_time:
            query = query.filter(LoginLog.create_time >= start_time)

        if end_time:
            query = query.filter(LoginLog.create_time <= end_time)

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        logs = query.order_by(LoginLog.create_time.desc()).offset(offset).limit(
            page_param.page_size
        ).all()

        items = []
        for log in logs:
            items.append({
                "id": str(log.id),
                "username": log.username,
                "user_id": str(log.user_id) if log.user_id else None,
                "login_method": log.login_method,
                "result": log.result,
                "ip": log.ip,
                "device": log.device,
                "create_time": log.create_time.isoformat() if log.create_time else None,
            })

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    async def export_operate_logs(self) -> dict[str, Any]:
        """Create operation log export task (L-04)."""
        # TODO: Implement async export via B0a export service
        return {"task_id": "pending"}

    async def export_login_logs(self) -> dict[str, Any]:
        """Create login log export task (L-04)."""
        # TODO: Implement async export via B0a export service
        return {"task_id": "pending"}
