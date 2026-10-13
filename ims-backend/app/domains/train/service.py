# app/domains/train/service.py - Training service layer (B21)
"""
Business logic for training module.

P0 Services (90% branch coverage required):
- TrainTaskService.create_task_by_user
- TrainTaskService.create_task_by_position
- TrainTaskService.preview_position_users
- TrainStudyService.report_video_progress
- TrainStudyService.report_document_progress
- TrainStudyService.report_link_progress
- TrainStudyService.confirm_duration
- TrainStudyService.submit_quiz
- TrainStatService.get_finish_rate
"""

import json
from datetime import datetime
from typing import Optional

from app.core.clock import get_now
from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session
from app.domains.train.models import (
    TrainMaterial,
    TrainMaterialCate,
    TrainMaterialVersion,
    TrainTask,
    TrainTaskRecord,
)
from app.domains.train.repo import (
    TrainCateRepo,
    TrainMaterialRepo,
    TrainMaterialVersionRepo,
    TrainRecordRepo,
    TrainStudyLogRepo,
    TrainTaskRepo,
)
from app.domains.train.schemas import (
    CateCreateRequest,
    CateTreeNode,
    CateUpdateRequest,
    MaterialCreateRequest,
    MaterialDetail,
    MaterialListItem,
    MaterialUpdateRequest,
    QuizQuestion,
    TaskCreateRequest,
    TaskDetail,
    TaskListItem,
    TaskUpdateRequest,
)
from app.domains.train.scope import check_task_in_scope
from app.domains.train.upload import validate_link_url
from app.domains.train.video import (
    calculate_coverage,
    intervals_to_json,
    is_video_complete,
    parse_intervals_json,
    update_watched_intervals,
    validate_video_progress,
)


class TrainMaterialService:
    """Service for material and category management."""

    def __init__(self):
        self.session = get_db_session()
        self.cate_repo = TrainCateRepo(self.session)
        self.material_repo = TrainMaterialRepo(self.session)
        self.version_repo = TrainMaterialVersionRepo(self.session)

    async def get_cate_tree(
        self,
        position_code: Optional[str] = None,
        for_student: bool = False,
    ) -> list[CateTreeNode]:
        """Get category tree (FP-B21-MT-01)."""
        tenant_id = ctx.tenant_id
        if for_student:
            user_position = await self._get_user_position()
            position_code = user_position

        categories = self.cate_repo.get_tree(tenant_id, position_code)

        nodes: dict[int, CateTreeNode] = {}
        for cate in categories:
            nodes[cate.id] = CateTreeNode(
                id=str(cate.id),
                parent_id=str(cate.parent_id) if cate.parent_id else None,
                position_code=cate.position_code,
                cate_name=cate.cate_name,
                sort=cate.sort or 0,
                children=[],
            )

        roots: list[CateTreeNode] = []
        for cate in categories:
            node = nodes[cate.id]
            parent = nodes.get(cate.parent_id)
            if parent is None or cate.parent_id == 0:
                roots.append(node)
            else:
                parent.children.append(node)

        def sort_children(node_list: list[CateTreeNode]) -> None:
            node_list.sort(key=lambda n: (n.sort, int(n.id)))
            for n in node_list:
                sort_children(n.children)

        sort_children(roots)
        return roots

    async def create_cate(self, req: CateCreateRequest) -> CateTreeNode:
        """Create category (FP-B21-MT-02)."""
        tenant_id = ctx.tenant_id

        if req.parent_id != "0":
            parent = self.cate_repo.get_by_id(int(req.parent_id), tenant_id)
            if not parent:
                raise BizError(1500, msg="父分类不存在")

        cate = TrainMaterialCate(
            tenant_id=tenant_id,
            parent_id=int(req.parent_id),
            cate_name=req.cate_name,
            sort=req.sort,
            creator=ctx.user_id,
        )
        cate = self.cate_repo.create(cate)

        return CateTreeNode(
            id=str(cate.id),
            parent_id=str(cate.parent_id) if cate.parent_id else None,
            position_code=cate.position_code,
            cate_name=cate.cate_name,
            sort=cate.sort or 0,
            children=[],
        )

    async def update_cate(self, cate_id: str, req: CateUpdateRequest) -> CateTreeNode:
        """Update category (FP-B21-MT-02)."""
        tenant_id = ctx.tenant_id
        cate = self.cate_repo.get_by_id(int(cate_id), tenant_id)
        if not cate:
            raise BizError(1504, msg="分类不存在")

        if req.cate_name is not None:
            cate.cate_name = req.cate_name
        if req.sort is not None:
            cate.sort = req.sort

        cate.updater = ctx.user_id
        self.session.flush()

        return CateTreeNode(
            id=str(cate.id),
            parent_id=str(cate.parent_id) if cate.parent_id else None,
            position_code=cate.position_code,
            cate_name=cate.cate_name,
            sort=cate.sort or 0,
            children=[],
        )

    async def delete_cate(self, cate_id: str) -> None:
        """Delete category (FP-B21-MT-02)."""
        tenant_id = ctx.tenant_id
        cate = self.cate_repo.get_by_id(int(cate_id), tenant_id)
        if not cate:
            raise BizError(1504, msg="分类不存在")

        if self.cate_repo.has_children(cate.id, tenant_id):
            raise BizError(1001, msg="存在子分类，不可删除")

        if self.cate_repo.has_materials(cate.id, tenant_id):
            raise BizError(1001, msg="分类下有资料，不可删除")

        self.cate_repo.soft_delete(cate)

    async def list_materials(
        self,
        cate_id: Optional[str] = None,
        status: Optional[str] = None,
        material_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        for_student: bool = False,
    ) -> tuple[list[MaterialListItem], int]:
        """List materials (FP-B21-MT-03)."""
        tenant_id = ctx.tenant_id
        position_codes = None

        if for_student:
            user_position = await self._get_user_position()
            if user_position:
                position_codes = [user_position]
            status = "PUBLISHED"

        offset = (page - 1) * page_size
        materials, total = self.material_repo.list_materials(
            tenant_id=tenant_id,
            cate_id=int(cate_id) if cate_id else None,
            status=status,
            material_type=material_type,
            keyword=keyword,
            position_codes=position_codes,
            offset=offset,
            limit=page_size,
        )

        items = []
        for m in materials:
            items.append(
                MaterialListItem(
                    id=str(m.id),
                    material_no=m.material_no,
                    title=m.title,
                    cate_id=str(m.cate_id),
                    material_type=m.material_type,
                    status=m.status,
                    convert_status=m.convert_status,
                    version=m.version,
                    page_count=m.page_count,
                    duration_seconds=m.duration_seconds,
                    position_labels=[],
                    published_at=m.published_at.isoformat() if m.published_at else None,
                    create_time=m.create_time.isoformat() if m.create_time else None,
                )
            )

        return items, total

    async def create_material(self, req: MaterialCreateRequest) -> MaterialDetail:
        """Create material (FP-B21-MT-04)."""
        tenant_id = ctx.tenant_id

        cate = self.cate_repo.get_by_id(int(req.cate_id), tenant_id)
        if not cate:
            raise BizError(1500, msg="分类不存在")

        if req.material_type == "LINK":
            validate_link_url(req.link_url)
        elif not req.file_key:
            raise BizError(1001, msg="文档/视频类型必须上传文件")

        material_no = self.material_repo.generate_material_no(tenant_id)
        now = get_now()

        material = TrainMaterial(
            tenant_id=tenant_id,
            material_no=material_no,
            title=req.title,
            cate_id=int(req.cate_id),
            material_type=req.material_type,
            file_key=req.file_key,
            link_url=req.link_url,
            position_codes=json.dumps(req.position_codes) if req.position_codes else None,
            version=1,
            status=req.status,
            uploader_user_id=ctx.user_id,
            creator=ctx.user_id,
        )

        if req.status == "PUBLISHED":
            material.published_at = now

        if req.material_type == "DOC" and req.file_key:
            material.convert_status = "PENDING"

        material = self.material_repo.create(material)

        version = TrainMaterialVersion(
            tenant_id=tenant_id,
            material_id=material.id,
            version=1,
            title=req.title,
            file_key=req.file_key,
            link_url=req.link_url,
            editor_user_id=ctx.user_id,
            created_at=now,
        )
        self.version_repo.create(version)

        return await self.get_material_detail(str(material.id))

    async def get_material_detail(self, material_id: str) -> MaterialDetail:
        """Get material detail with versions (FP-B21-MT-07)."""
        tenant_id = ctx.tenant_id
        material = self.material_repo.get_by_id(int(material_id), tenant_id)
        if not material:
            raise BizError(1504, msg="资料不存在")

        versions = self.version_repo.get_versions(material.id, tenant_id)
        version_items = []
        for v in versions:
            version_items.append(
                {
                    "version": v.version,
                    "title": v.title,
                    "file_key": v.file_key,
                    "pdf_key": v.pdf_key,
                    "link_url": v.link_url,
                    "page_count": v.page_count,
                    "duration_seconds": v.duration_seconds,
                    "editor_name": None,
                    "created_at": v.created_at.isoformat(),
                }
            )

        position_codes = json.loads(material.position_codes) if material.position_codes else []

        return MaterialDetail(
            id=str(material.id),
            material_no=material.material_no,
            title=material.title,
            cate_id=str(material.cate_id),
            material_type=material.material_type,
            file_key=material.file_key,
            link_url=material.link_url,
            position_codes=position_codes,
            position_labels=[],
            version=material.version,
            status=material.status,
            convert_status=material.convert_status,
            page_count=material.page_count,
            duration_seconds=material.duration_seconds,
            published_at=material.published_at.isoformat() if material.published_at else None,
            create_time=material.create_time.isoformat() if material.create_time else None,
            versions=version_items,
        )

    async def update_material(
        self, material_id: str, req: MaterialUpdateRequest
    ) -> MaterialDetail:
        """Update material (creates new version) (FP-B21-MT-05/06)."""
        tenant_id = ctx.tenant_id
        material = self.material_repo.get_by_id(int(material_id), tenant_id)
        if not material:
            raise BizError(1504, msg="资料不存在")

        if material.status == "OFFLINE":
            raise BizError(1501, msg="已下架资料不可编辑")

        now = get_now()
        create_new_version = False

        if req.title is not None and req.title != material.title:
            material.title = req.title
            create_new_version = True

        if req.cate_id is not None:
            cate = self.cate_repo.get_by_id(int(req.cate_id), tenant_id)
            if not cate:
                raise BizError(1500, msg="分类不存在")
            material.cate_id = int(req.cate_id)

        if req.file_key is not None and req.file_key != material.file_key:
            material.file_key = req.file_key
            create_new_version = True
            if material.material_type == "DOC":
                material.convert_status = "PENDING"

        if req.link_url is not None:
            validate_link_url(req.link_url)
            if req.link_url != material.link_url:
                material.link_url = req.link_url
                create_new_version = True

        if req.position_codes is not None:
            material.position_codes = json.dumps(req.position_codes)

        if req.status is not None:
            if req.status == "PUBLISHED" and material.status != "PUBLISHED":
                if material.convert_status == "PENDING":
                    raise BizError(1001, msg="文档转换中，不可发布")
                material.published_at = now
            material.status = req.status

        if create_new_version:
            material.version += 1
            version = TrainMaterialVersion(
                tenant_id=tenant_id,
                material_id=material.id,
                version=material.version,
                title=material.title,
                file_key=material.file_key,
                link_url=material.link_url,
                editor_user_id=ctx.user_id,
                created_at=now,
            )
            self.version_repo.create(version)

        material.updater = ctx.user_id
        self.session.flush()

        return await self.get_material_detail(material_id)

    async def offline_material(self, material_id: str) -> None:
        """Offline (soft delete) material (FP-B21-MT-08)."""
        tenant_id = ctx.tenant_id
        material = self.material_repo.get_by_id(int(material_id), tenant_id)
        if not material:
            raise BizError(1504, msg="资料不存在")

        self.material_repo.soft_delete(material)

    async def _get_user_position(self) -> Optional[str]:
        """Get current user's position code."""
        from app.domains.sys.models import User
        user = self.session.query(User).filter(
            User.id == ctx.user_id,
            User.tenant_id == ctx.tenant_id,
            User.deleted == 0,
        ).first()
        return user.position_code if user else None


class TrainTaskService:
    """Service for task management. P0 functions."""

    def __init__(self):
        self.session = get_db_session()
        self.task_repo = TrainTaskRepo(self.session)
        self.record_repo = TrainRecordRepo(self.session)
        self.material_repo = TrainMaterialRepo(self.session)

    async def list_tasks(
        self,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TaskListItem], int]:
        """List tasks with scope filtering (FP-B21-TK-01)."""
        tenant_id = ctx.tenant_id
        offset = (page - 1) * page_size

        ctx_data = {
            "trace_id": ctx.trace_id,
            "user_id": ctx.user_id,
            "tenant_id": ctx.tenant_id,
            "dept_ids": ctx.dept_ids,
            "data_scopes": ctx.data_scopes,
        }

        tasks, total = self.task_repo.list_tasks(
            tenant_id=tenant_id,
            ctx_data=ctx_data,
            status=status,
            keyword=keyword,
            offset=offset,
            limit=page_size,
        )

        items = []
        for task in tasks:
            counts = self.record_repo.count_by_task(task.id, tenant_id)
            progress_rate = (
                counts["finished"] / counts["total"] * 100
                if counts["total"] > 0
                else 0
            )

            items.append(
                TaskListItem(
                    id=str(task.id),
                    task_no=task.task_no,
                    task_name=task.task_name,
                    assign_scope=task.assign_scope,
                    confirm_type=task.confirm_type,
                    deadline=task.deadline.isoformat(),
                    status=task.status,
                    source=task.source,
                    assigned_count=counts["total"],
                    finished_count=counts["finished"],
                    progress_rate=round(progress_rate, 1),
                    create_time=task.create_time.isoformat() if task.create_time else None,
                )
            )

        return items, total

    async def create_task_by_user(self, req: TaskCreateRequest) -> TaskDetail:
        """
        Create task with BY_USER assignment (FP-B21-TK-02).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id

        deadline = datetime.fromisoformat(req.deadline.replace("Z", "+00:00"))
        if deadline <= get_now():
            raise BizError(1102, msg="截止时间不能早于当前时间")

        material_ids = [int(mid) for mid in req.material_ids]
        materials = self.material_repo.get_by_ids(material_ids, tenant_id)
        if len(materials) != len(material_ids):
            raise BizError(1101, msg="部分资料不存在")
        for m in materials:
            if m.status != "PUBLISHED":
                raise BizError(1101, msg=f"资料「{m.title}」未发布")

        if req.confirm_type == "QUIZ":
            if not req.quiz:
                raise BizError(1001, msg="问卷类型必须配置题目")
            if not req.pass_score:
                raise BizError(1001, msg="问卷类型必须配置及格分")
            self._validate_quiz(req.quiz)
        elif req.confirm_type == "DURATION":
            if not req.required_minutes or req.required_minutes < 1:
                raise BizError(1001, msg="学时类型必须配置要求时长")

        if not req.assigned_user_ids:
            raise BizError(1001, msg="按人指派必须选择学员")

        task_no = self.task_repo.generate_task_no(tenant_id)

        from app.domains.sys.models import User
        users = self.session.query(User).filter(
            User.id.in_([int(uid) for uid in req.assigned_user_ids]),
            User.tenant_id == tenant_id,
            User.deleted == 0,
            User.status.in_(["ACTIVE", "FROZEN"]),
        ).all()

        if len(users) != len(req.assigned_user_ids):
            raise BizError(1500, msg="部分用户不存在或已停用")

        creator_user = self.session.query(User).filter(
            User.id == ctx.user_id,
            User.tenant_id == tenant_id,
        ).first()
        creator_dept_id = creator_user.main_dept_id if creator_user else None

        task = TrainTask(
            tenant_id=tenant_id,
            task_no=task_no,
            task_name=req.task_name,
            material_ids=json.dumps(material_ids),
            assign_scope="BY_USER",
            deadline=deadline.replace(tzinfo=None),
            confirm_type=req.confirm_type,
            required_minutes=req.required_minutes or 0,
            quiz=json.dumps([q.model_dump() for q in req.quiz]) if req.quiz else None,
            pass_score=req.pass_score,
            status="IN_PROGRESS",
            source="MANUAL",
            client_token=req.client_token,
            creator_dept_id=creator_dept_id,
            creator=ctx.user_id,
        )
        task = self.task_repo.create(task)

        records = []
        for user in users:
            record = TrainTaskRecord(
                tenant_id=tenant_id,
                task_id=task.id,
                user_id=user.id,
                user_dept_id=user.main_dept_id,
                creator=ctx.user_id,
            )
            records.append(record)

        self.record_repo.create_batch(records)

        return await self.get_task_detail(str(task.id))

    async def create_task_by_position(self, req: TaskCreateRequest) -> TaskDetail:
        """
        Create task with BY_POSITION assignment (FP-B21-TK-04).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id

        deadline = datetime.fromisoformat(req.deadline.replace("Z", "+00:00"))
        if deadline <= get_now():
            raise BizError(1102, msg="截止时间不能早于当前时间")

        material_ids = [int(mid) for mid in req.material_ids]
        materials = self.material_repo.get_by_ids(material_ids, tenant_id)
        if len(materials) != len(material_ids):
            raise BizError(1101, msg="部分资料不存在")
        for m in materials:
            if m.status != "PUBLISHED":
                raise BizError(1101, msg=f"资料「{m.title}」未发布")

        if req.confirm_type == "QUIZ":
            if not req.quiz:
                raise BizError(1001, msg="问卷类型必须配置题目")
            if not req.pass_score:
                raise BizError(1001, msg="问卷类型必须配置及格分")
            self._validate_quiz(req.quiz)
        elif req.confirm_type == "DURATION":
            if not req.required_minutes or req.required_minutes < 1:
                raise BizError(1001, msg="学时类型必须配置要求时长")

        if not req.assigned_position_codes:
            raise BizError(1001, msg="按岗位指派必须选择岗位")

        from app.domains.sys.models import User
        users = self.session.query(User).filter(
            User.position_code.in_(req.assigned_position_codes),
            User.tenant_id == tenant_id,
            User.deleted == 0,
            User.status.in_(["ACTIVE", "FROZEN"]),
        ).all()

        if not users:
            raise BizError(1001, msg="所选岗位下没有可指派的用户")

        task_no = self.task_repo.generate_task_no(tenant_id)

        creator_user = self.session.query(User).filter(
            User.id == ctx.user_id,
            User.tenant_id == tenant_id,
        ).first()
        creator_dept_id = creator_user.main_dept_id if creator_user else None

        task = TrainTask(
            tenant_id=tenant_id,
            task_no=task_no,
            task_name=req.task_name,
            material_ids=json.dumps(material_ids),
            assign_scope="BY_POSITION",
            deadline=deadline.replace(tzinfo=None),
            confirm_type=req.confirm_type,
            required_minutes=req.required_minutes or 0,
            quiz=json.dumps([q.model_dump() for q in req.quiz]) if req.quiz else None,
            pass_score=req.pass_score,
            status="IN_PROGRESS",
            source="MANUAL",
            client_token=req.client_token,
            creator_dept_id=creator_dept_id,
            creator=ctx.user_id,
        )
        task = self.task_repo.create(task)

        records = []
        for user in users:
            record = TrainTaskRecord(
                tenant_id=tenant_id,
                task_id=task.id,
                user_id=user.id,
                user_dept_id=user.main_dept_id,
                creator=ctx.user_id,
            )
            records.append(record)

        self.record_repo.create_batch(records)

        return await self.get_task_detail(str(task.id))

    async def get_task_detail(self, task_id: str) -> TaskDetail:
        """Get task detail (FP-B21-TK-06, ST-02)."""
        tenant_id = ctx.tenant_id
        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        has_task_query = "ims:train:task:query" in (ctx.perm_codes or set())
        is_assigned = self.record_repo.is_user_assigned(task.id, ctx.user_id, tenant_id)

        if has_task_query:
            assigned_dept_ids = self.record_repo.get_assigned_dept_ids(task.id, tenant_id)
            if not check_task_in_scope(ctx, task, assigned_dept_ids):
                raise BizError(1504, msg="无权访问该任务")
        elif not is_assigned:
            raise BizError(1105, msg="非被指派人")

        material_ids = json.loads(task.material_ids) if task.material_ids else []
        materials = self.material_repo.get_by_ids(material_ids, tenant_id)

        material_items = []
        for m in materials:
            material_items.append({
                "id": str(m.id),
                "title": m.title,
                "material_type": m.material_type,
                "duration_seconds": m.duration_seconds,
                "page_count": m.page_count,
            })

        records = self.record_repo.get_by_task(task.id, tenant_id)
        assigned_users = []
        for r in records:
            assigned_users.append({
                "user_id": str(r.user_id),
                "nickname": "",
                "dept_name": None,
                "progress": r.progress,
                "confirm_status": r.confirm_status,
            })

        quiz = json.loads(task.quiz) if task.quiz else None

        return TaskDetail(
            id=str(task.id),
            task_no=task.task_no,
            task_name=task.task_name,
            material_ids=[str(mid) for mid in material_ids],
            materials=material_items,
            assign_scope=task.assign_scope,
            deadline=task.deadline.isoformat(),
            confirm_type=task.confirm_type,
            required_minutes=task.required_minutes,
            quiz=quiz,
            pass_score=task.pass_score,
            status=task.status,
            source=task.source,
            assigned_users=assigned_users,
            create_time=task.create_time.isoformat() if task.create_time else None,
        )

    async def update_task(self, task_id: str, req: TaskUpdateRequest) -> TaskDetail:
        """Update task (FP-B21-TK-06)."""
        tenant_id = ctx.tenant_id
        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        if task.status != "IN_PROGRESS":
            raise BizError(1104, msg="已结束任务不可编辑")

        if task.deadline <= get_now():
            raise BizError(1104, msg="已过截止时间不可编辑")

        if req.task_name is not None:
            task.task_name = req.task_name

        if req.deadline is not None:
            deadline = datetime.fromisoformat(req.deadline.replace("Z", "+00:00"))
            if deadline <= get_now():
                raise BizError(1102, msg="截止时间不能早于当前时间")
            task.deadline = deadline.replace(tzinfo=None)

        if req.required_minutes is not None:
            task.required_minutes = req.required_minutes

        if req.quiz is not None:
            self._validate_quiz(req.quiz)
            task.quiz = json.dumps([q.model_dump() for q in req.quiz])

        if req.pass_score is not None:
            task.pass_score = req.pass_score

        task.updater = ctx.user_id
        self.session.flush()

        return await self.get_task_detail(task_id)

    async def delete_task(self, task_id: str) -> None:
        """Delete task (FP-B21-TK-07)."""
        tenant_id = ctx.tenant_id
        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        self.task_repo.soft_delete(task)

    async def preview_position_users(
        self, position_codes: list[str]
    ) -> list[dict]:
        """
        Preview users for position assignment (FP-B21-TK-03).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id

        from app.domains.sys.models import DictData, User

        result = []
        for code in position_codes:
            dict_data = self.session.query(DictData).filter(
                DictData.dict_type == "dict_position",
                DictData.dict_value == code,
                DictData.deleted == 0,
                DictData.status == "ENABLED",
            ).first()

            label = dict_data.dict_label if dict_data else code

            users = self.session.query(User).filter(
                User.position_code == code,
                User.tenant_id == tenant_id,
                User.deleted == 0,
                User.status.in_(["ACTIVE", "FROZEN"]),
            ).all()

            user_items = []
            for u in users:
                user_items.append({
                    "user_id": str(u.id),
                    "nickname": u.nickname,
                    "dept_name": None,
                })

            result.append({
                "position_code": code,
                "position_label": label,
                "user_count": len(users),
                "users": user_items,
            })

        return result

    def _validate_quiz(self, quiz: list[QuizQuestion]) -> None:
        """Validate quiz structure."""
        if not quiz:
            raise BizError(1001, msg="题目列表不能为空")

        for i, q in enumerate(quiz):
            if q.type == "SINGLE":
                if not q.options or len(q.options) < 2:
                    raise BizError(1001, msg=f"题目{i+1}的选项不能少于2个")
                if q.answer_index is None or q.answer_index < 0 or q.answer_index >= len(q.options):
                    raise BizError(1001, msg=f"题目{i+1}的答案索引无效")
            elif q.type == "TRUE_FALSE":
                if q.answer_boolean is None:
                    raise BizError(1001, msg=f"题目{i+1}的答案不能为空")


class TrainStudyService:
    """Service for study execution. P0 functions."""

    def __init__(self):
        self.session = get_db_session()
        self.task_repo = TrainTaskRepo(self.session)
        self.record_repo = TrainRecordRepo(self.session)
        self.log_repo = TrainStudyLogRepo(self.session)
        self.material_repo = TrainMaterialRepo(self.session)

    async def get_my_tasks(
        self,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Get current user's learning tasks (FP-B21-ST-01)."""
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        from sqlalchemy import select

        query = (
            select(TrainTaskRecord, TrainTask)
            .join(TrainTask, TrainTaskRecord.task_id == TrainTask.id)
            .where(
                TrainTaskRecord.user_id == user_id,
                TrainTaskRecord.tenant_id == tenant_id,
                TrainTaskRecord.deleted == 0,
                TrainTask.deleted == 0,
            )
        )

        if status == "IN_PROGRESS":
            query = query.where(TrainTask.status == "IN_PROGRESS")
        elif status == "FINISHED":
            query = query.where(TrainTaskRecord.confirm_status == "CONFIRMED")

        query = query.order_by(TrainTask.deadline)

        from sqlalchemy import func
        count_query = select(func.count()).select_from(query.subquery())
        total = self.session.scalar(count_query) or 0

        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        results = self.session.execute(query).all()

        items = []
        for record, task in results:
            material_ids = json.loads(task.material_ids) if task.material_ids else []
            items.append({
                "id": str(task.id),
                "task_no": task.task_no,
                "task_name": task.task_name,
                "confirm_type": task.confirm_type,
                "deadline": task.deadline.isoformat(),
                "status": task.status,
                "progress": record.progress,
                "confirm_status": record.confirm_status,
                "is_overdue": record.is_overdue,
                "material_count": len(material_ids),
            })

        return items, total

    async def get_task_for_study(self, task_id: str) -> dict:
        """Get task detail for study execution (FP-B21-ST-02)."""
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        record = self.record_repo.get_by_user_task(task.id, user_id, tenant_id)
        if not record:
            raise BizError(1105, msg="非被指派人")

        material_ids = json.loads(task.material_ids) if task.material_ids else []
        materials = self.material_repo.get_by_ids(material_ids, tenant_id)

        material_progress = json.loads(record.material_progress) if record.material_progress else {}

        material_items = []
        for m in materials:
            progress = material_progress.get(str(m.id), 0)
            material_items.append({
                "id": str(m.id),
                "title": m.title,
                "material_type": m.material_type,
                "file_key": m.file_key,
                "link_url": m.link_url,
                "duration_seconds": m.duration_seconds,
                "page_count": m.page_count,
                "progress": progress,
                "last_position": None,
            })

        quiz_draft = json.loads(record.quiz_draft) if record.quiz_draft else None

        return {
            "id": str(task.id),
            "task_no": task.task_no,
            "task_name": task.task_name,
            "materials": material_items,
            "confirm_type": task.confirm_type,
            "required_minutes": task.required_minutes,
            "pass_score": task.pass_score,
            "deadline": task.deadline.isoformat(),
            "progress": record.progress,
            "effective_minutes": record.effective_seconds // 60,
            "confirm_status": record.confirm_status,
            "quiz_draft": quiz_draft,
            "attempt_count": record.attempt_count,
        }

    async def report_video_progress(
        self,
        task_id: str,
        material_id: str,
        position: int,
        heartbeat_interval: float = 15.0,
    ) -> dict:
        """
        Report video progress (heartbeat) (FP-B21-ST-03).

        P0 function - 90% branch coverage required.

        Per Q-D11, Q-D12:
        - Single increment <= actual interval AND <= 20s
        - Interval deduplication
        - Coverage >= 95% for completion
        """
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        record = self.record_repo.get_by_user_task(task.id, user_id, tenant_id)
        if not record:
            raise BizError(1105, msg="非被指派人")

        material = self.material_repo.get_by_id(int(material_id), tenant_id)
        if not material:
            raise BizError(1101, msg="资料不存在")
        if material.material_type != "VIDEO":
            raise BizError(1001, msg="非视频类型资料")

        now = get_now()
        stat_date = now.strftime("%Y-%m-%d")

        log = self.log_repo.get_or_create_today(
            record_id=record.id,
            material_id=material.id,
            tenant_id=tenant_id,
            stat_date=stat_date,
        )

        last_pos = log.last_position or 0
        is_valid, effective_secs = validate_video_progress(
            current_pos=position,
            last_pos=last_pos,
            interval_seconds=heartbeat_interval,
        )

        if effective_secs > 0:
            existing_intervals = parse_intervals_json(log.watched_intervals)
            new_intervals = update_watched_intervals(
                existing_intervals,
                last_pos,
                position,
            )
            log.watched_intervals = intervals_to_json(new_intervals)
            log.effective_seconds += effective_secs

        log.last_position = position
        log.last_heartbeat_at = now

        if not record.started_at:
            record.started_at = now

        record.effective_seconds += effective_secs

        total_duration = material.duration_seconds or 0
        intervals = parse_intervals_json(log.watched_intervals)
        is_complete = is_video_complete(intervals, total_duration)

        material_progress = json.loads(record.material_progress) if record.material_progress else {}
        if is_complete:
            material_progress[str(material.id)] = 100
        else:
            coverage = calculate_coverage(intervals, total_duration)
            material_progress[str(material.id)] = int(coverage * 100)

        record.material_progress = json.dumps(material_progress)
        record.progress = self._calculate_overall_progress(task, material_progress)

        self.session.flush()

        return {
            "effective_seconds": effective_secs,
            "total_effective_seconds": record.effective_seconds,
            "material_progress": material_progress.get(str(material.id), 0),
            "overall_progress": record.progress,
            "is_complete": is_complete,
        }

    async def report_document_progress(
        self,
        task_id: str,
        material_id: str,
        page: int,
        heartbeat_interval: float = 15.0,
    ) -> dict:
        """
        Report document progress (FP-B21-ST-04).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        record = self.record_repo.get_by_user_task(task.id, user_id, tenant_id)
        if not record:
            raise BizError(1105, msg="非被指派人")

        material = self.material_repo.get_by_id(int(material_id), tenant_id)
        if not material:
            raise BizError(1101, msg="资料不存在")
        if material.material_type != "DOC":
            raise BizError(1001, msg="非文档类型资料")

        now = get_now()
        stat_date = now.strftime("%Y-%m-%d")

        log = self.log_repo.get_or_create_today(
            record_id=record.id,
            material_id=material.id,
            tenant_id=tenant_id,
            stat_date=stat_date,
        )

        effective_secs = min(int(heartbeat_interval), 20)
        log.effective_seconds += effective_secs
        log.last_position = page
        log.last_heartbeat_at = now

        if not record.started_at:
            record.started_at = now

        record.effective_seconds += effective_secs

        total_pages = material.page_count or 1
        progress = min(100, int(page / total_pages * 100))

        material_progress = json.loads(record.material_progress) if record.material_progress else {}
        material_progress[str(material.id)] = max(
            material_progress.get(str(material.id), 0),
            progress,
        )

        record.material_progress = json.dumps(material_progress)
        record.progress = self._calculate_overall_progress(task, material_progress)

        self.session.flush()

        return {
            "effective_seconds": effective_secs,
            "total_effective_seconds": record.effective_seconds,
            "material_progress": material_progress.get(str(material.id), 0),
            "overall_progress": record.progress,
        }

    async def report_link_progress(
        self,
        task_id: str,
        material_id: str,
        heartbeat_interval: float = 15.0,
    ) -> dict:
        """
        Report link progress (FP-B21-ST-05).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        record = self.record_repo.get_by_user_task(task.id, user_id, tenant_id)
        if not record:
            raise BizError(1105, msg="非被指派人")

        material = self.material_repo.get_by_id(int(material_id), tenant_id)
        if not material:
            raise BizError(1101, msg="资料不存在")
        if material.material_type != "LINK":
            raise BizError(1001, msg="非外链类型资料")

        now = get_now()
        stat_date = now.strftime("%Y-%m-%d")

        log = self.log_repo.get_or_create_today(
            record_id=record.id,
            material_id=material.id,
            tenant_id=tenant_id,
            stat_date=stat_date,
        )

        effective_secs = min(int(heartbeat_interval), 20)
        log.effective_seconds += effective_secs
        log.last_heartbeat_at = now

        if not record.started_at:
            record.started_at = now

        record.effective_seconds += effective_secs

        material_progress = json.loads(record.material_progress) if record.material_progress else {}
        material_progress[str(material.id)] = 100

        record.material_progress = json.dumps(material_progress)
        record.progress = self._calculate_overall_progress(task, material_progress)

        self.session.flush()

        return {
            "effective_seconds": effective_secs,
            "total_effective_seconds": record.effective_seconds,
            "material_progress": 100,
            "overall_progress": record.progress,
        }

    async def confirm_duration(self, task_id: str) -> dict:
        """
        Confirm completion for DURATION type (FP-B21-ST-06).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        if task.confirm_type != "DURATION":
            raise BizError(1001, msg="非学时确认类型")

        record = self.record_repo.get_by_user_task(task.id, user_id, tenant_id)
        if not record:
            raise BizError(1105, msg="非被指派人")

        if record.confirm_status == "CONFIRMED":
            return {"success": True, "message": "已完成确认"}

        effective_minutes = record.effective_seconds // 60
        required_minutes = task.required_minutes or 0

        if effective_minutes < required_minutes:
            raise BizError(1104, msg=f"学时未达标，需要{required_minutes}分钟，当前{effective_minutes}分钟")

        now = get_now()
        record.confirm_status = "CONFIRMED"
        record.finished_at = now
        record.is_overdue = now > task.deadline

        self.session.flush()

        return {
            "success": True,
            "message": "确认完成",
        }

    async def save_quiz_draft(self, task_id: str, answers: list) -> dict:
        """Save quiz draft (FP-B21-ST-07)."""
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        record = self.record_repo.get_by_user_task(task.id, user_id, tenant_id)
        if not record:
            raise BizError(1105, msg="非被指派人")

        record.quiz_draft = json.dumps(answers)
        self.session.flush()

        return {"success": True}

    async def submit_quiz(self, task_id: str, answers: list) -> dict:
        """
        Submit quiz (FP-B21-ST-08).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id
        user_id = ctx.user_id

        task = self.task_repo.get_by_id(int(task_id), tenant_id)
        if not task:
            raise BizError(1504, msg="任务不存在")

        if task.confirm_type != "QUIZ":
            raise BizError(1001, msg="非问卷确认类型")

        record = self.record_repo.get_by_user_task(task.id, user_id, tenant_id)
        if not record:
            raise BizError(1105, msg="非被指派人")

        quiz = json.loads(task.quiz) if task.quiz else []
        if not quiz:
            raise BizError(1001, msg="任务未配置问卷")

        score = self._grade_quiz(quiz, answers)
        passed = score >= (task.pass_score or 60)

        now = get_now()
        record.attempt_count += 1
        record.confirm_score = score
        record.quiz_draft = None

        if passed:
            record.confirm_status = "CONFIRMED"
            record.finished_at = now
            record.is_overdue = now > task.deadline

        self.session.flush()

        return {
            "success": passed,
            "message": "提交成功" if passed else "未通过，请重试",
            "score": score,
            "passed": passed,
        }

    def _calculate_overall_progress(
        self, task: TrainTask, material_progress: dict
    ) -> int:
        """Calculate overall task progress."""
        material_ids = json.loads(task.material_ids) if task.material_ids else []
        if not material_ids:
            return 0

        total = sum(material_progress.get(str(mid), 0) for mid in material_ids)
        return total // len(material_ids)

    def _grade_quiz(self, quiz: list[dict], answers: list) -> int:
        """Grade quiz and return score 0-100."""
        if not quiz:
            return 0

        correct = 0
        for i, q in enumerate(quiz):
            if i >= len(answers):
                continue

            answer = answers[i]
            if q.get("type") == "SINGLE":
                if answer == q.get("answer_index"):
                    correct += 1
            elif q.get("type") == "TRUE_FALSE" and answer == q.get("answer_boolean"):
                correct += 1

        return int(correct / len(quiz) * 100)


class TrainStatService:
    """Service for statistics. P0 functions."""

    def __init__(self):
        self.session = get_db_session()

    async def get_finish_rate(
        self,
        dept_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """
        Get finish rate overview (FP-B21-SS-01).

        P0 function - 90% branch coverage required.
        """
        tenant_id = ctx.tenant_id

        from app.domains.train.scope import get_stat_visible_depts

        visible_depts, is_self_only = get_stat_visible_depts(
            ctx,
            int(dept_id) if dept_id else None,
        )

        if visible_depts is not None and len(visible_depts) == 0:
            return {
                "total_assigned": 0,
                "total_finished": 0,
                "total_overdue": 0,
                "finish_rate": 0.0,
                "overdue_rate": 0.0,
            }

        from sqlalchemy import func, select

        query = select(
            func.count().label("total"),
            func.sum(
                func.case((TrainTaskRecord.confirm_status == "CONFIRMED", 1), else_=0)
            ).label("finished"),
            func.sum(
                func.case((TrainTaskRecord.is_overdue, 1), else_=0)
            ).label("overdue"),
        ).where(
            TrainTaskRecord.tenant_id == tenant_id,
            TrainTaskRecord.deleted == 0,
        )

        if is_self_only:
            query = query.where(TrainTaskRecord.user_id == ctx.user_id)
        elif visible_depts:
            query = query.where(TrainTaskRecord.user_dept_id.in_(visible_depts))

        result = self.session.execute(query).first()

        total = result.total or 0
        finished = result.finished or 0
        overdue = result.overdue or 0

        finish_rate = round(finished / total * 100, 2) if total > 0 else 0.0
        overdue_rate = round(overdue / total * 100, 2) if total > 0 else 0.0

        return {
            "total_assigned": total,
            "total_finished": finished,
            "total_overdue": overdue,
            "finish_rate": finish_rate,
            "overdue_rate": overdue_rate,
        }
