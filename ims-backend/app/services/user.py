# app/services/user.py - User service (FW-B03, FW-B08)
"""
User service.

Implements:
- FP-B03-01: User management
- FP-B03-02: User-Department management
- FP-B08-03: Query users by department
- FP-B08-08: User endpoints for B0b
"""

from typing import Any, Optional

import bcrypt
from sqlalchemy import or_

from app.core.context import ctx
from app.core.errors import BizError
from app.core.pagination import PageParam, PageResult
from app.db.session import get_db_session
from app.db.transaction import transactional


class UserService:
    """User management service."""

    async def get_user_page(
        self,
        page_param: PageParam,
        dept_id: Optional[str] = None,
        include_children: bool = True,
        keyword: Optional[str] = None,
        status: Optional[str] = None,
    ) -> PageResult:
        """
        Get paginated user list.

        Rules per FP-B08-03:
        - includeChildren=true: filter by path LIKE '/…/deptId/%'
        - includeChildren=false: only direct members
        - Data scope filtering applied

        Args:
            page_param: Pagination parameters
            dept_id: Filter by department
            include_children: Include users in child departments
            keyword: Username/nickname keyword
            status: Filter by status

        Returns:
            PageResult with user list
        """
        from app.domains.sys.models import Dept, User, UserDept
        session = get_db_session()

        tenant_id = ctx.tenant_id

        # Base query
        query = session.query(User).filter(
            User.tenant_id == tenant_id,
            User.deleted == 0,
        )

        # Filter by department
        if dept_id:
            dept_id_int = int(dept_id)

            if include_children:
                # Get department path for LIKE query
                dept = session.query(Dept).filter(
                    Dept.id == dept_id_int,
                    Dept.tenant_id == tenant_id,
                    Dept.deleted == 0,
                ).first()

                if dept:
                    # Find all departments in subtree
                    child_dept_ids = session.query(Dept.id).filter(
                        Dept.path.like(f"{dept.path}%"),
                        Dept.tenant_id == tenant_id,
                        Dept.deleted == 0,
                    ).all()
                    child_dept_ids = [d.id for d in child_dept_ids]

                    # Users in any of these departments
                    user_ids = session.query(UserDept.user_id).filter(
                        UserDept.dept_id.in_(child_dept_ids),
                        UserDept.tenant_id == tenant_id,
                    ).distinct().all()
                    user_ids = [u.user_id for u in user_ids]

                    query = query.filter(User.id.in_(user_ids))
            else:
                # Only direct members
                user_ids = session.query(UserDept.user_id).filter(
                    UserDept.dept_id == dept_id_int,
                    UserDept.tenant_id == tenant_id,
                ).all()
                user_ids = [u.user_id for u in user_ids]

                query = query.filter(User.id.in_(user_ids))

        # Filter by keyword
        if keyword:
            query = query.filter(
                or_(
                    User.username.like(f"%{keyword}%"),
                    User.nickname.like(f"%{keyword}%"),
                )
            )

        # Filter by status
        if status:
            query = query.filter(User.status == status)

        # Apply data scope filtering
        # TODO: Implement data scope from ctx.dataScopes

        # Count total
        total = query.count()

        # Get page data
        offset = (page_param.page_no - 1) * page_param.page_size
        users = query.order_by(User.create_time.desc(), User.id.desc()).offset(
            offset
        ).limit(page_param.page_size).all()

        # Get main department names
        main_dept_ids = [u.main_dept_id for u in users if u.main_dept_id]
        dept_names = {}
        if main_dept_ids:
            depts = session.query(Dept.id, Dept.name).filter(
                Dept.id.in_(main_dept_ids),
                Dept.deleted == 0,
            ).all()
            dept_names = {d.id: d.name for d in depts}

        # Build result
        items = []
        for user in users:
            items.append({
                "id": str(user.id),
                "username": user.username,
                "nickname": user.nickname,
                "mobile": self._mask_mobile(user.mobile_enc) if user.mobile_enc else None,
                "email": user.email,
                "status": user.status,
                "main_dept_id": str(user.main_dept_id) if user.main_dept_id else None,
                "main_dept_name": dept_names.get(user.main_dept_id),
                "position_label": None,  # TODO: Get from dict
                "last_login_time": (
                    user.last_login_time.isoformat() + "+08:00"
                    if user.last_login_time else None
                ),
            })

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    async def get_user_simple_page(
        self,
        page_param: PageParam,
        keyword: Optional[str] = None,
    ) -> PageResult:
        """
        Get simple user list for selectors.

        LOGIN_ONLY - returns id, nickname, mainDeptName, status only.

        Args:
            page_param: Pagination parameters
            keyword: Nickname keyword

        Returns:
            PageResult with simple user list
        """
        from app.domains.sys.models import Dept, User
        session = get_db_session()

        tenant_id = ctx.tenant_id

        query = session.query(User).filter(
            User.tenant_id == tenant_id,
            User.deleted == 0,
            User.status.in_(["ACTIVE", "FROZEN"]),  # Exclude resigned
        )

        if keyword:
            query = query.filter(User.nickname.like(f"%{keyword}%"))

        total = query.count()

        offset = (page_param.page_no - 1) * page_param.page_size
        users = query.order_by(User.nickname).offset(offset).limit(
            page_param.page_size
        ).all()

        # Get main department names
        main_dept_ids = [u.main_dept_id for u in users if u.main_dept_id]
        dept_names = {}
        if main_dept_ids:
            depts = session.query(Dept.id, Dept.name).filter(
                Dept.id.in_(main_dept_ids),
                Dept.deleted == 0,
            ).all()
            dept_names = {d.id: d.name for d in depts}

        items = [
            {
                "id": str(user.id),
                "nickname": user.nickname,
                "main_dept_name": dept_names.get(user.main_dept_id),
                "status": user.status,
            }
            for user in users
        ]

        return PageResult(
            list=items,
            total=total,
            page_no=page_param.page_no,
            page_size=page_param.page_size,
        )

    @transactional
    async def create_user(self, request: Any) -> dict[str, Any]:
        """
        Create a new user.

        Minimal fields: username, nickname, mobile, depts, mainDeptId, password.

        Args:
            request: UserCreateRequest

        Returns:
            Created user data
        """
        from app.domains.sys.models import Dept, User, UserDept
        session = get_db_session()

        tenant_id = ctx.tenant_id

        # Validate username format (4-30 alphanumeric underscore)
        import re
        if not re.match(r"^[a-zA-Z0-9_]{4,30}$", request.username):
            raise BizError(1001, msg="用户名必须为4-30位字母数字下划线")

        # Check username uniqueness
        existing = session.query(User).filter(
            User.username == request.username,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if existing:
            raise BizError(1001, msg="用户名已存在")

        # Validate departments exist and are enabled
        dept_ids = [int(d) for d in request.dept_ids]
        main_dept_id = int(request.main_dept_id)

        if main_dept_id not in dept_ids:
            raise BizError(1001, msg="主部门必须在所属部门列表中")

        depts = session.query(Dept).filter(
            Dept.id.in_(dept_ids),
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).all()

        if len(depts) != len(dept_ids):
            raise BizError(1500)

        for dept in depts:
            if dept.status != "ENABLED":
                raise BizError(1501)

        # Hash password
        password_hash = bcrypt.hashpw(
            request.password.encode(), bcrypt.gensalt(rounds=10)
        ).decode()

        # Create user
        user = User(
            tenant_id=tenant_id,
            username=request.username,
            nickname=request.nickname,
            mobile_enc=self._encrypt_mobile(request.mobile) if request.mobile else None,
            mobile_hash=self._hash_mobile(request.mobile) if request.mobile else None,
            password_hash=password_hash,
            main_dept_id=main_dept_id,
            source="LOCAL",
            status="ACTIVE",
            pwd_reset_required=True,
        )

        session.add(user)
        session.flush()

        # Create user-dept associations
        for dept_id in dept_ids:
            user_dept = UserDept(
                tenant_id=tenant_id,
                user_id=user.id,
                dept_id=dept_id,
                is_main=(dept_id == main_dept_id),
                source="LOCAL",
            )
            session.add(user_dept)

        session.flush()

        return {
            "id": str(user.id),
            "username": user.username,
            "nickname": user.nickname,
            "status": user.status,
            "main_dept_id": str(main_dept_id),
        }

    def _mask_mobile(self, encrypted: str) -> str:
        """Mask mobile number (show only last 4)."""
        # TODO: Decrypt and mask properly
        # For now return masked placeholder
        return "***********"

    def _encrypt_mobile(self, mobile: str) -> str:
        """Encrypt mobile number with AES."""
        # TODO: Implement AES encryption
        return mobile

    def _hash_mobile(self, mobile: str) -> str:
        """Create HMAC hash of mobile for matching."""
        import hashlib
        import hmac

        # TODO: Use configured secret key
        key = b"ims_mobile_hash_key"
        return hmac.new(key, mobile.encode(), hashlib.sha256).hexdigest()

    @transactional
    async def update_user_depts(
        self,
        user_id: str,
        dept_ids: list[str],
        main_dept_id: str,
    ) -> None:
        """
        Update user's department assignments.

        Rules per FP-B03-02:
        - User can belong to multiple departments
        - Must have exactly one main department
        - Removing main dept requires specifying another main first
        - Removing all depts auto-assigns to "待分配" dept

        Args:
            user_id: User ID
            dept_ids: List of department IDs
            main_dept_id: Main department ID
        """
        from app.domains.sys.models import Dept, User, UserDept
        session = get_db_session()

        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        # Get user
        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        dept_id_ints = [int(d) for d in dept_ids]
        main_dept_id_int = int(main_dept_id)

        # If no depts provided, assign to "待分配"
        if not dept_id_ints:
            system_dept = session.query(Dept).filter(
                Dept.source == "SYSTEM",
                Dept.tenant_id == tenant_id,
                Dept.deleted == 0,
            ).first()

            if system_dept:
                dept_id_ints = [system_dept.id]
                main_dept_id_int = system_dept.id
            else:
                raise BizError(1001, msg="未找到系统部门")

        # Main dept must be in dept list
        if main_dept_id_int not in dept_id_ints:
            raise BizError(1001, msg="主部门必须在所属部门列表中")

        # Validate all depts exist and are enabled
        depts = session.query(Dept).filter(
            Dept.id.in_(dept_id_ints),
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).all()

        if len(depts) != len(dept_id_ints):
            raise BizError(1500)

        for dept in depts:
            if dept.status != "ENABLED":
                raise BizError(1501)

        # Delete existing associations
        session.query(UserDept).filter(
            UserDept.user_id == user_id_int,
            UserDept.tenant_id == tenant_id,
        ).delete()

        # Create new associations
        for dept_id in dept_id_ints:
            user_dept = UserDept(
                tenant_id=tenant_id,
                user_id=user_id_int,
                dept_id=dept_id,
                is_main=(dept_id == main_dept_id_int),
                source="LOCAL",
            )
            session.add(user_dept)

        # Update user's main dept
        user.main_dept_id = main_dept_id_int

        session.flush()

    @transactional
    async def delete_user(self, user_id: str) -> None:
        """
        Delete user.

        Rules per FP-B03-01 item 3:
        - Only users who never logged in AND have no business references can be deleted
        - RESIGNED users cannot be deleted -> 1502

        Args:
            user_id: User ID
        """
        from app.domains.sys.models import User, UserDept
        session = get_db_session()

        tenant_id = ctx.tenant_id
        user_id_int = int(user_id)

        user = session.query(User).filter(
            User.id == user_id_int,
            User.tenant_id == tenant_id,
            User.deleted == 0,
        ).first()

        if not user:
            raise BizError(1504)

        # RESIGNED users cannot be deleted
        if user.status == "RESIGNED":
            raise BizError(1502, refs=[{"entity": "已离职用户", "count": 1}])

        # Users who have logged in cannot be deleted
        if user.last_login_time is not None:
            raise BizError(1502, refs=[{"entity": "有登录记录的用户", "count": 1}])

        # TODO: Check for business references (in future modules)

        # Delete user-dept associations
        session.query(UserDept).filter(
            UserDept.user_id == user_id_int,
            UserDept.tenant_id == tenant_id,
        ).delete()

        # Soft delete user
        user.deleted = user.id

        session.flush()
