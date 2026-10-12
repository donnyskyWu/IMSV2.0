# app/services/dept.py - Department service (FW-B08)
"""
Department service.

Implements:
- FP-B08-02: Department tree query
- FP-B08-03: Query users by department
- FP-B08-04: Create local department
- FP-B08-05: Update department
- FP-B08-06: Move department
- FP-B08-07: Enable/disable/delete department
"""

from typing import Any, Optional

from sqlalchemy import and_, func, or_

from app.core.context import ctx
from app.core.errors import BizError
from app.db.session import get_db_session
from app.db.transaction import transactional


class DeptService:
    """Department management service."""
    
    async def get_dept_tree(
        self,
        status: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Get department tree.
        
        Rules per FP-B08-02:
        - memberCount: dedup count of active+frozen users in dept and descendants
        - directMemberCount: users directly in this dept
        - keyword match: return matched node and ancestor path
        - Default excludes disabled depts, status=ALL includes them
        - Tree itself not filtered by data scope
        - Performance: 2000 depts, 20k users -> <= 500ms
        
        Args:
            status: Filter by status, "ALL" to include disabled
            keyword: Department name keyword
            
        Returns:
            List of tree nodes
        """
        from app.domains.sys.models import Dept, User, UserDept
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        
        # Base query for departments
        dept_query = session.query(Dept).filter(
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        )
        
        if status != "ALL":
            dept_query = dept_query.filter(Dept.status == "ENABLED")
        
        depts = dept_query.order_by(Dept.sort, Dept.id).all()
        
        if not depts:
            return []
        
        # Get all department IDs
        dept_ids = [d.id for d in depts]
        dept_map = {d.id: d for d in depts}
        
        # Calculate member counts in batch (single query)
        user_dept_subq = session.query(
            UserDept.dept_id,
            UserDept.user_id,
        ).join(User, User.id == UserDept.user_id).filter(
            UserDept.dept_id.in_(dept_ids),
            User.status.in_(["ACTIVE", "FROZEN"]),
            User.deleted == 0,
        ).subquery()
        
        direct_counts = dict(
            session.query(
                user_dept_subq.c.dept_id,
                func.count(func.distinct(user_dept_subq.c.user_id)),
            ).group_by(user_dept_subq.c.dept_id).all()
        )
        
        # Get leader names
        leader_ids = [d.leader_user_id for d in depts if d.leader_user_id]
        leader_names = {}
        if leader_ids:
            from app.domains.sys.models import User
            leaders = session.query(User.id, User.nickname).filter(
                User.id.in_(leader_ids),
                User.deleted == 0,
            ).all()
            leader_names = {u.id: u.nickname for u in leaders}
        
        # Build tree structure
        def build_node(dept: Dept) -> dict[str, Any]:
            children = [
                build_node(child) 
                for child in depts 
                if child.parent_id == dept.id
            ]
            
            # Calculate member count including children
            member_count = self._calculate_member_count_recursive(
                dept.id, depts, direct_counts
            )
            
            node = {
                "id": str(dept.id),
                "parent_id": str(dept.parent_id) if dept.parent_id else None,
                "name": dept.name,
                "source": dept.source,
                "status": dept.status,
                "local_orphan": dept.local_orphan,
                "member_count": member_count,
                "direct_member_count": direct_counts.get(dept.id, 0),
                "leader_name": leader_names.get(dept.leader_user_id),
                "children": children,
            }
            return node
        
        # Find root departments (parent_id = 0 or None)
        root_depts = [d for d in depts if d.parent_id == 0 or d.parent_id is None]
        tree = [build_node(d) for d in root_depts]
        
        # Apply keyword filter if specified
        if keyword:
            tree = self._filter_tree_by_keyword(tree, keyword)
        
        return tree
    
    def _calculate_member_count_recursive(
        self,
        dept_id: int,
        all_depts: list,
        direct_counts: dict[int, int],
    ) -> int:
        """Calculate member count including all descendants (deduped)."""
        count = direct_counts.get(dept_id, 0)
        
        for dept in all_depts:
            if dept.parent_id == dept_id:
                count += self._calculate_member_count_recursive(
                    dept.id, all_depts, direct_counts
                )
        
        return count
    
    def _filter_tree_by_keyword(
        self, tree: list[dict], keyword: str
    ) -> list[dict]:
        """Filter tree to only show matching nodes and their ancestors."""
        def node_matches(node: dict, kw: str) -> bool:
            return kw.lower() in node["name"].lower()
        
        def filter_node(node: dict, kw: str) -> Optional[dict]:
            children_result = []
            has_matching_child = False
            
            for child in node.get("children", []):
                filtered_child = filter_node(child, kw)
                if filtered_child:
                    children_result.append(filtered_child)
                    has_matching_child = True
            
            if node_matches(node, kw) or has_matching_child:
                result = node.copy()
                result["children"] = children_result
                return result
            
            return None
        
        return [
            n for n in (filter_node(node, keyword) for node in tree) 
            if n is not None
        ]
    
    @transactional
    async def create_dept(self, request: Any) -> dict[str, Any]:
        """
        Create a local department.
        
        Rules per FP-B08-04:
        - source=LOCAL
        - Parent not exist -> 1500, disabled -> 1501
        - Same-parent duplicate name -> 1219
        - Under "待分配" -> 1220
        
        Args:
            request: DeptCreateRequest with parentId, name, sort, leaderUserId
            
        Returns:
            Created department data
        """
        from app.domains.sys.models import Dept, User
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        parent_id = int(request.parent_id)
        
        # Check parent exists
        parent = session.query(Dept).filter(
            Dept.id == parent_id,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if not parent:
            raise BizError(1500)
        
        if parent.status != "ENABLED":
            raise BizError(1501)
        
        # Cannot create under SYSTEM department (待分配)
        if parent.source == "SYSTEM":
            raise BizError(1220)
        
        # Check duplicate name under same parent
        existing = session.query(Dept).filter(
            Dept.parent_id == parent_id,
            Dept.name == request.name,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if existing:
            raise BizError(1219)
        
        # Check leader exists and is active
        leader_user_id = None
        if request.leader_user_id:
            leader_user_id = int(request.leader_user_id)
            leader = session.query(User).filter(
                User.id == leader_user_id,
                User.tenant_id == tenant_id,
                User.deleted == 0,
            ).first()
            
            if not leader:
                raise BizError(1500)
            if leader.status != "ACTIVE":
                raise BizError(1501)
        
        # Build path
        new_id = None
        dept = Dept(
            tenant_id=tenant_id,
            parent_id=parent_id,
            name=request.name,
            sort=request.sort or 0,
            leader_user_id=leader_user_id,
            source="LOCAL",
            status="ENABLED",
        )
        
        session.add(dept)
        session.flush()
        
        # Update path after we have the ID
        dept.path = f"{parent.path}{dept.id}/"
        session.flush()
        
        return self._dept_to_response(dept)
    
    @transactional
    async def update_dept(self, dept_id: str, request: Any) -> dict[str, Any]:
        """
        Update department (name, leader, sort).
        
        Rules per FP-B08-05:
        - SYSTEM dept -> 1220
        - Same-parent duplicate name -> 1219
        - DINGTALK dept: success with syncOverrideHint=true
        
        Args:
            dept_id: Department ID
            request: DeptUpdateRequest
            
        Returns:
            Updated department data with syncOverrideHint
        """
        from app.domains.sys.models import Dept, User
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        dept_id_int = int(dept_id)
        
        dept = session.query(Dept).filter(
            Dept.id == dept_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if not dept:
            raise BizError(1504)
        
        # SYSTEM department cannot be modified
        if dept.source == "SYSTEM":
            raise BizError(1220)
        
        sync_override_hint = dept.source == "DINGTALK"
        
        # Update name
        if request.name is not None and request.name != dept.name:
            # Check duplicate name under same parent
            existing = session.query(Dept).filter(
                Dept.parent_id == dept.parent_id,
                Dept.name == request.name,
                Dept.tenant_id == tenant_id,
                Dept.deleted == 0,
                Dept.id != dept_id_int,
            ).first()
            
            if existing:
                raise BizError(1219)
            
            dept.name = request.name
        
        # Update leader
        if request.leader_user_id is not None:
            if request.leader_user_id:
                leader_id = int(request.leader_user_id)
                leader = session.query(User).filter(
                    User.id == leader_id,
                    User.tenant_id == tenant_id,
                    User.deleted == 0,
                    User.status == "ACTIVE",
                ).first()
                
                if not leader:
                    raise BizError(1500)
                
                dept.leader_user_id = leader_id
            else:
                dept.leader_user_id = None
        
        # Update sort
        if request.sort is not None:
            dept.sort = request.sort
        
        session.flush()
        
        result = self._dept_to_response(dept)
        result["sync_override_hint"] = sync_override_hint
        return result
    
    @transactional
    async def move_dept(self, dept_id: str, new_parent_id: str) -> dict[str, Any]:
        """
        Move department to new parent.
        
        Rules per FP-B08-06:
        - Move to self or descendant -> 1218
        - DINGTALK to LOCAL parent -> 1220
        - SYSTEM dept cannot move or be target -> 1220
        - Same-parent duplicate name -> 1219
        - Same transaction update all descendant paths
        
        Args:
            dept_id: Department ID to move
            new_parent_id: New parent department ID
            
        Returns:
            Updated department data
        """
        from app.domains.sys.models import Dept
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        dept_id_int = int(dept_id)
        new_parent_id_int = int(new_parent_id)
        
        # Get department to move
        dept = session.query(Dept).filter(
            Dept.id == dept_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if not dept:
            raise BizError(1504)
        
        # SYSTEM department cannot be moved
        if dept.source == "SYSTEM":
            raise BizError(1220)
        
        # Get new parent
        new_parent = session.query(Dept).filter(
            Dept.id == new_parent_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if not new_parent:
            raise BizError(1500)
        
        if new_parent.status != "ENABLED":
            raise BizError(1501)
        
        # Cannot move to SYSTEM department
        if new_parent.source == "SYSTEM":
            raise BizError(1220)
        
        # Cannot move to self or descendant
        if new_parent_id_int == dept_id_int:
            raise BizError(1218)
        
        if f"/{dept_id_int}/" in new_parent.path:
            raise BizError(1218)
        
        # DINGTALK department cannot move to LOCAL parent
        if dept.source == "DINGTALK" and new_parent.source == "LOCAL":
            raise BizError(1220)
        
        # Check duplicate name under new parent
        existing = session.query(Dept).filter(
            Dept.parent_id == new_parent_id_int,
            Dept.name == dept.name,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
            Dept.id != dept_id_int,
        ).first()
        
        if existing:
            raise BizError(1219)
        
        # Update paths for department and all descendants
        old_path_prefix = dept.path
        new_path = f"{new_parent.path}{dept_id_int}/"
        
        # Update self
        dept.parent_id = new_parent_id_int
        dept.path = new_path
        
        # Update all descendants
        descendants = session.query(Dept).filter(
            Dept.path.like(f"{old_path_prefix}%"),
            Dept.id != dept_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).all()
        
        for descendant in descendants:
            descendant.path = descendant.path.replace(
                old_path_prefix, new_path, 1
            )
        
        session.flush()
        
        return self._dept_to_response(dept)
    
    @transactional
    async def update_dept_status(self, dept_id: str, status: str) -> None:
        """
        Enable or disable department.
        
        Rules per FP-B08-07:
        - Has enabled children -> 1502
        - SYSTEM dept -> 1220
        - DINGTALK dept: local disable allowed, next sync may re-enable
        
        Args:
            dept_id: Department ID
            status: ENABLED or DISABLED
        """
        from app.domains.sys.models import Dept
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        dept_id_int = int(dept_id)
        
        dept = session.query(Dept).filter(
            Dept.id == dept_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if not dept:
            raise BizError(1504)
        
        # SYSTEM department cannot be modified
        if dept.source == "SYSTEM":
            raise BizError(1220)
        
        # Validate status
        if status not in ("ENABLED", "DISABLED"):
            raise BizError(1001, msg="状态值不正确")
        
        # If disabling, check for enabled children
        if status == "DISABLED":
            has_enabled_children = session.query(Dept).filter(
                Dept.parent_id == dept_id_int,
                Dept.status == "ENABLED",
                Dept.tenant_id == tenant_id,
                Dept.deleted == 0,
            ).first() is not None
            
            if has_enabled_children:
                raise BizError(1502, refs=[{"entity": "下级部门", "count": 1}])
        
        dept.status = status
        session.flush()
    
    @transactional
    async def delete_dept(self, dept_id: str) -> None:
        """
        Delete department.
        
        Rules per FP-B08-07:
        - Has children or users (any status including resigned) -> 1502
        - SYSTEM dept -> 1220
        
        Args:
            dept_id: Department ID
        """
        from app.domains.sys.models import Dept, UserDept
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        dept_id_int = int(dept_id)
        
        dept = session.query(Dept).filter(
            Dept.id == dept_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if not dept:
            raise BizError(1504)
        
        # SYSTEM department cannot be deleted
        if dept.source == "SYSTEM":
            raise BizError(1220)
        
        # Check for children
        child_count = session.query(Dept).filter(
            Dept.parent_id == dept_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).count()
        
        if child_count > 0:
            raise BizError(1502, refs=[{"entity": "下级部门", "count": child_count}])
        
        # Check for users (any status)
        user_count = session.query(UserDept).filter(
            UserDept.dept_id == dept_id_int,
            UserDept.tenant_id == tenant_id,
        ).count()
        
        if user_count > 0:
            raise BizError(1502, refs=[{"entity": "人员", "count": user_count}])
        
        # Soft delete
        dept.deleted = dept.id
        session.flush()
    
    @transactional
    async def confirm_orphan_dept(self, dept_id: str) -> None:
        """
        Confirm keeping a local orphan department.
        
        Rules per FP-D07-02 item 7:
        - Sets local_orphan=0, marking dept as confirmed to keep
        - Only applicable to departments with local_orphan=1
        
        Args:
            dept_id: Department ID
        """
        from app.domains.sys.models import Dept
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        dept_id_int = int(dept_id)
        
        dept = session.query(Dept).filter(
            Dept.id == dept_id_int,
            Dept.tenant_id == tenant_id,
            Dept.deleted == 0,
        ).first()
        
        if not dept:
            raise BizError(1504)
        
        if not dept.local_orphan:
            raise BizError(1001, msg="该部门不是待确认状态")
        
        dept.local_orphan = False
        session.flush()
    
    def _dept_to_response(self, dept) -> dict[str, Any]:
        """Convert department to response dict."""
        return {
            "id": str(dept.id),
            "parent_id": str(dept.parent_id) if dept.parent_id else None,
            "name": dept.name,
            "source": dept.source,
            "status": dept.status,
            "sort": dept.sort or 0,
            "leader_user_id": str(dept.leader_user_id) if dept.leader_user_id else None,
            "sync_override_hint": False,
        }
