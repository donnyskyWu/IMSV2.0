# app/services/workbench.py - 工作台服务（B3 新建，P0）
"""
工作台服务实现。

功能：
- get_dashboard: 获取工作台仪表盘数据
"""

from sqlalchemy.orm import Session

from app.services import message as message_service
from app.services import todo as todo_service


def get_dashboard(
    session: Session,
    *,
    user_id: int,
) -> dict:
    """
    获取工作台仪表盘数据。

    返回 {todoCount, unreadMessageCount, myAccountCount: null, ...}
    其余字段返回 null（Q4）。
    """
    # 待办计数
    todo_count_data = todo_service.get_my_count(session, user_id=user_id)

    # 未读消息数
    unread_count = message_service.get_unread_count(session, user_id=user_id)

    return {
        "todoCount": todo_count_data["total"],
        "todoByType": todo_count_data["byType"],
        "todoOverdue": todo_count_data["overdue"],
        "unreadMessageCount": unread_count,
        # 以下字段本批返回 null，前端不渲染
        "myAccountCount": None,
        "myAssetCount": None,
        "myApprovalCount": None,
        "myAttendanceCount": None,
    }
