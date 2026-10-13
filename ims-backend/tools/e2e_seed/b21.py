# tools/e2e_seed/b21.py - E2E test fixtures for B21 Training (B21)
"""
E2E test data seeding for training module.

Per 培训管理-实现理解.md §12.4:
- Fixed ID range 90001~90099 for isolation from other modules
- stat_daily: 2 weeks low completion rate data for E2E-B21-35
- All IDs use upsert for idempotency
"""

import json
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session


FIXTURE = {
    "depts": [
        {"id": 90001, "name": "B21测试部门A", "leader_user_id": 90001},
        {"id": 90002, "name": "B21测试部门B", "leader_user_id": 90002},
    ],
    "positions": [
        {"position_code": "B21_ANCHOR", "dict_label": "B21主播组"},
        {"position_code": "B21_OPERATOR", "dict_label": "B21直播运营"},
    ],
    "users": [
        {
            "id": 90001,
            "username": "b21_admin",
            "nickname": "B21管理员",
            "role": "R1",
            "dept_id": 90001,
            "data_scope": "ALL",
        },
        {
            "id": 90002,
            "username": "b21_dept_mgr",
            "nickname": "B21部门经理",
            "role": "R1",
            "dept_id": 90002,
            "data_scope": "DEPT",
        },
        {
            "id": 90003,
            "username": "b21_student",
            "nickname": "B21学员",
            "position": "B21_ANCHOR",
            "dept_id": 90001,
            "data_scope": "SELF",
        },
        {
            "id": 90004,
            "username": "b21_other",
            "nickname": "B21其他用户",
            "position": "B21_OPERATOR",
            "dept_id": 90002,
            "data_scope": "SELF",
        },
    ],
    "categories": [
        {"id": 90001, "parent_id": 0, "cate_name": "B21主播培训", "position_code": "B21_ANCHOR"},
        {"id": 90002, "parent_id": 90001, "cate_name": "入职培训"},
        {"id": 90003, "parent_id": 90001, "cate_name": "技能培训"},
    ],
    "materials": [
        {
            "id": 90001,
            "material_no": "MT202610010001",
            "title": "B21测试文档",
            "cate_id": 90002,
            "material_type": "DOC",
            "status": "PUBLISHED",
            "page_count": 10,
            "position_codes": ["B21_ANCHOR"],
        },
        {
            "id": 90002,
            "material_no": "MT202610010002",
            "title": "B21测试视频",
            "cate_id": 90002,
            "material_type": "VIDEO",
            "status": "PUBLISHED",
            "duration_seconds": 300,
            "position_codes": ["B21_ANCHOR"],
        },
        {
            "id": 90003,
            "material_no": "MT202610010003",
            "title": "B21草稿资料",
            "cate_id": 90002,
            "material_type": "DOC",
            "status": "DRAFT",
        },
        {
            "id": 90004,
            "material_no": "MT202610010004",
            "title": "B21已下架资料",
            "cate_id": 90002,
            "material_type": "LINK",
            "status": "OFFLINE",
            "link_url": "https://example.com",
        },
    ],
    "tasks": [
        {
            "id": 90001,
            "task_no": "TT202610010001",
            "task_name": "B21学时任务",
            "material_ids": [90001, 90002],
            "assign_scope": "BY_USER",
            "confirm_type": "DURATION",
            "required_minutes": 30,
            "status": "IN_PROGRESS",
            "deadline_days": 7,
            "assigned_user_ids": [90003],
        },
        {
            "id": 90002,
            "task_no": "TT202610010002",
            "task_name": "B21问卷任务",
            "material_ids": [90001],
            "assign_scope": "BY_USER",
            "confirm_type": "QUIZ",
            "pass_score": 60,
            "quiz": [
                {
                    "type": "SINGLE",
                    "question": "测试题目1",
                    "options": ["A", "B", "C", "D"],
                    "answer_index": 0,
                },
                {
                    "type": "TRUE_FALSE",
                    "question": "测试题目2",
                    "answer_boolean": True,
                },
            ],
            "status": "IN_PROGRESS",
            "deadline_days": 14,
            "assigned_user_ids": [90003, 90004],
            "is_overdue": False,
        },
    ],
    # E2E-B21-35 验证：连续两周低完成率部门数据
    "stat_daily": [
        # 上上周数据（部门 90002 完成率 70%）
        {"stat_date": "2026-09-28", "dept_id": 90002, "assigned": 10, "finished": 7, "finish_rate": 70.0},
        {"stat_date": "2026-09-29", "dept_id": 90002, "assigned": 10, "finished": 7, "finish_rate": 70.0},
        {"stat_date": "2026-09-30", "dept_id": 90002, "assigned": 10, "finished": 7, "finish_rate": 70.0},
        {"stat_date": "2026-10-01", "dept_id": 90002, "assigned": 10, "finished": 7, "finish_rate": 70.0},
        {"stat_date": "2026-10-02", "dept_id": 90002, "assigned": 10, "finished": 7, "finish_rate": 70.0},
        {"stat_date": "2026-10-03", "dept_id": 90002, "assigned": 10, "finished": 7, "finish_rate": 70.0},
        {"stat_date": "2026-10-04", "dept_id": 90002, "assigned": 10, "finished": 7, "finish_rate": 70.0},
        # 上周数据（部门 90002 完成率 75%）
        {"stat_date": "2026-10-05", "dept_id": 90002, "assigned": 20, "finished": 15, "finish_rate": 75.0},
        {"stat_date": "2026-10-06", "dept_id": 90002, "assigned": 20, "finished": 15, "finish_rate": 75.0},
        {"stat_date": "2026-10-07", "dept_id": 90002, "assigned": 20, "finished": 15, "finish_rate": 75.0},
        {"stat_date": "2026-10-08", "dept_id": 90002, "assigned": 20, "finished": 15, "finish_rate": 75.0},
        {"stat_date": "2026-10-09", "dept_id": 90002, "assigned": 20, "finished": 15, "finish_rate": 75.0},
        {"stat_date": "2026-10-10", "dept_id": 90002, "assigned": 20, "finished": 15, "finish_rate": 75.0},
        {"stat_date": "2026-10-11", "dept_id": 90002, "assigned": 20, "finished": 15, "finish_rate": 75.0},
    ],
    "train_ai_mock": True,
}


def seed_b21_data(session: Session, tenant_id: int = 1) -> dict:
    """
    Seed B21 test data.
    
    Args:
        session: Database session
        tenant_id: Target tenant ID
    
    Returns:
        Summary of seeded data
    """
    from app.domains.sys.models import Dept, DictData, User, UserDept, UserRole
    from app.domains.train.models import (
        TrainMaterial,
        TrainMaterialCate,
        TrainStatDaily,
        TrainTask,
        TrainTaskRecord,
    )
    
    summary = {"depts": 0, "users": 0, "categories": 0, "materials": 0, "tasks": 0, "stats": 0}
    now = datetime.now()
    
    # Seed departments
    for dept_data in FIXTURE["depts"]:
        existing = session.query(Dept).filter(Dept.id == dept_data["id"]).first()
        if not existing:
            dept = Dept(
                id=dept_data["id"],
                tenant_id=tenant_id,
                parent_id=1,
                path=f"/1/{dept_data['id']}/",
                name=dept_data["name"],
                status="ENABLED",
                source="LOCAL",
                leader_user_id=dept_data.get("leader_user_id"),
            )
            session.add(dept)
            summary["depts"] += 1
    
    # Seed positions (dict data)
    for pos_data in FIXTURE["positions"]:
        existing = session.query(DictData).filter(
            DictData.dict_type == "dict_position",
            DictData.dict_value == pos_data["position_code"],
        ).first()
        if not existing:
            dict_data = DictData(
                tenant_id=1,
                dict_type="dict_position",
                dict_value=pos_data["position_code"],
                dict_label=pos_data["dict_label"],
                status="ENABLED",
            )
            session.add(dict_data)
    
    # Seed users
    for user_data in FIXTURE["users"]:
        existing = session.query(User).filter(User.id == user_data["id"]).first()
        if not existing:
            user = User(
                id=user_data["id"],
                tenant_id=tenant_id,
                username=user_data["username"],
                nickname=user_data["nickname"],
                status="ACTIVE",
                source="LOCAL",
                main_dept_id=user_data.get("dept_id"),
                position_code=user_data.get("position"),
            )
            session.add(user)
            summary["users"] += 1
            
            # User-Dept association
            if user_data.get("dept_id"):
                user_dept = UserDept(
                    user_id=user_data["id"],
                    dept_id=user_data["dept_id"],
                    is_main=True,
                )
                session.add(user_dept)
    
    session.flush()
    
    # Seed categories
    for cate_data in FIXTURE["categories"]:
        existing = session.query(TrainMaterialCate).filter(
            TrainMaterialCate.id == cate_data["id"]
        ).first()
        if not existing:
            cate = TrainMaterialCate(
                id=cate_data["id"],
                tenant_id=tenant_id,
                parent_id=cate_data["parent_id"],
                cate_name=cate_data["cate_name"],
                position_code=cate_data.get("position_code"),
            )
            session.add(cate)
            summary["categories"] += 1
    
    session.flush()
    
    # Seed materials
    for mat_data in FIXTURE["materials"]:
        existing = session.query(TrainMaterial).filter(
            TrainMaterial.id == mat_data["id"]
        ).first()
        if not existing:
            material = TrainMaterial(
                id=mat_data["id"],
                tenant_id=tenant_id,
                material_no=mat_data["material_no"],
                title=mat_data["title"],
                cate_id=mat_data["cate_id"],
                material_type=mat_data["material_type"],
                status=mat_data["status"],
                page_count=mat_data.get("page_count"),
                duration_seconds=mat_data.get("duration_seconds"),
                link_url=mat_data.get("link_url"),
                position_codes=json.dumps(mat_data.get("position_codes", [])),
                version=1,
                published_at=now if mat_data["status"] == "PUBLISHED" else None,
            )
            session.add(material)
            summary["materials"] += 1
    
    session.flush()
    
    # Seed tasks and records
    for task_data in FIXTURE["tasks"]:
        existing = session.query(TrainTask).filter(
            TrainTask.id == task_data["id"]
        ).first()
        if not existing:
            deadline = now + timedelta(days=task_data.get("deadline_days", 7))
            
            task = TrainTask(
                id=task_data["id"],
                tenant_id=tenant_id,
                task_no=task_data["task_no"],
                task_name=task_data["task_name"],
                material_ids=json.dumps(task_data["material_ids"]),
                assign_scope=task_data["assign_scope"],
                deadline=deadline,
                confirm_type=task_data["confirm_type"],
                required_minutes=task_data.get("required_minutes", 0),
                quiz=json.dumps(task_data.get("quiz")) if task_data.get("quiz") else None,
                pass_score=task_data.get("pass_score"),
                status=task_data["status"],
                source="MANUAL",
                creator_dept_id=90001,
            )
            session.add(task)
            summary["tasks"] += 1
            
            # Create records for assigned users
            for user_id in task_data.get("assigned_user_ids", []):
                record = TrainTaskRecord(
                    tenant_id=tenant_id,
                    task_id=task_data["id"],
                    user_id=user_id,
                    user_dept_id=90001 if user_id == 90003 else 90002,
                    is_overdue=task_data.get("is_overdue", False),
                )
                session.add(record)
    
    session.flush()
    
    # Seed statistics
    for stat_data in FIXTURE["stat_daily"]:
        existing = session.query(TrainStatDaily).filter(
            TrainStatDaily.stat_date == stat_data["stat_date"],
            TrainStatDaily.dept_id == stat_data["dept_id"],
        ).first()
        if not existing:
            stat = TrainStatDaily(
                tenant_id=tenant_id,
                stat_date=stat_data["stat_date"],
                dept_id=stat_data["dept_id"],
                assigned_count=stat_data["assigned"],
                finished_count=stat_data["finished"],
                overdue_count=0,
                total_duration_minutes=stat_data["assigned"] * 30,
                finish_rate=stat_data["finish_rate"],
            )
            session.add(stat)
            summary["stats"] += 1
    
    session.commit()
    
    return summary


def clear_b21_data(session: Session) -> dict:
    """
    Clear B21 test data.
    
    Args:
        session: Database session
    
    Returns:
        Summary of cleared data
    """
    from app.domains.train.models import (
        TrainDeptAlert,
        TrainMaterial,
        TrainMaterialCate,
        TrainMaterialVersion,
        TrainStatDaily,
        TrainStudyLog,
        TrainTask,
        TrainTaskRecord,
    )
    
    summary = {}
    
    # Clear in reverse dependency order
    summary["study_logs"] = session.query(TrainStudyLog).filter(
        TrainStudyLog.id >= 90000, TrainStudyLog.id < 100000
    ).delete(synchronize_session=False)
    
    summary["records"] = session.query(TrainTaskRecord).filter(
        TrainTaskRecord.id >= 90000, TrainTaskRecord.id < 100000
    ).delete(synchronize_session=False)
    
    summary["tasks"] = session.query(TrainTask).filter(
        TrainTask.id >= 90000, TrainTask.id < 100000
    ).delete(synchronize_session=False)
    
    summary["versions"] = session.query(TrainMaterialVersion).filter(
        TrainMaterialVersion.id >= 90000, TrainMaterialVersion.id < 100000
    ).delete(synchronize_session=False)
    
    summary["materials"] = session.query(TrainMaterial).filter(
        TrainMaterial.id >= 90000, TrainMaterial.id < 100000
    ).delete(synchronize_session=False)
    
    summary["categories"] = session.query(TrainMaterialCate).filter(
        TrainMaterialCate.id >= 90000, TrainMaterialCate.id < 100000
    ).delete(synchronize_session=False)
    
    summary["stats"] = session.query(TrainStatDaily).filter(
        TrainStatDaily.dept_id >= 90000, TrainStatDaily.dept_id < 100000
    ).delete(synchronize_session=False)
    
    summary["alerts"] = session.query(TrainDeptAlert).filter(
        TrainDeptAlert.dept_id >= 90000, TrainDeptAlert.dept_id < 100000
    ).delete(synchronize_session=False)
    
    session.commit()
    
    return summary


if __name__ == "__main__":
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    db_url = os.environ.get("IMS_DB_URL", "sqlite:///:memory:")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("Seeding B21 test data...")
    result = seed_b21_data(session)
    print(f"Seeded: {result}")
