# app/services/org_sync.py - Organization sync service (FW-D07)
"""
Organization synchronization service.

Implements:
- FP-D07-04: DingTalk organization reconciliation
"""

from typing import Any, Optional

from app.core.clock import get_now
from app.core.context import ctx
from app.db.session import get_db_session
from app.db.transaction import transactional


class OrgSyncService:
    """Organization synchronization service."""
    
    @transactional
    async def trigger_reconcile(self) -> dict[str, Any]:
        """
        Trigger organization structure reconciliation with DingTalk.
        
        Rules per FP-D07-04:
        - Compares IMS org structure with DingTalk
        - Creates sync batch record
        - Returns immediately with batch info (async execution)
        
        Returns:
            Sync batch info
        """
        from app.domains.sys.models import OrgSyncBatch
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        now = get_now()
        
        # Create sync batch record
        batch = OrgSyncBatch(
            tenant_id=tenant_id,
            status="PENDING",
            started_at=now,
        )
        
        session.add(batch)
        session.flush()
        
        # TODO: Trigger async DingTalk sync job
        # For now, just return the batch info
        
        return self._batch_to_response(batch)
    
    async def get_latest_batch(self) -> Optional[dict[str, Any]]:
        """
        Get the latest org sync batch status.
        
        Rules per FP-D07-04:
        - Returns the most recent sync batch
        - Includes counts for dept/user changes
        
        Returns:
            Latest batch info or None
        """
        from app.domains.sys.models import OrgSyncBatch
        session = get_db_session()
        
        tenant_id = ctx.tenant_id
        
        batch = session.query(OrgSyncBatch).filter(
            OrgSyncBatch.tenant_id == tenant_id,
        ).order_by(OrgSyncBatch.id.desc()).first()
        
        if not batch:
            return None
        
        return self._batch_to_response(batch)
    
    def _batch_to_response(self, batch) -> dict[str, Any]:
        """Convert batch to response dict."""
        return {
            "batch_id": str(batch.id),
            "status": batch.status,
            "started_at": (
                batch.started_at.isoformat() + "+08:00"
                if batch.started_at else None
            ),
            "completed_at": (
                batch.completed_at.isoformat() + "+08:00"
                if batch.completed_at else None
            ),
            "added_depts": batch.added_depts or 0,
            "updated_depts": batch.updated_depts or 0,
            "removed_depts": batch.removed_depts or 0,
            "added_users": batch.added_users or 0,
            "updated_users": batch.updated_users or 0,
            "removed_users": batch.removed_users or 0,
            "error_msg": batch.error_msg,
        }
