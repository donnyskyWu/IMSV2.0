# app/services/files.py - Upload and scoped download (FP-E01)
"""Store uploads under a tenant path and enforce owner or data-scope reads."""

import os
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.core.context import ctx
from app.core.errors import BizError
from app.db.ids import assign_pk
from app.db.session import get_db_session


class FileService:
    """File upload and download checks."""

    def upload(
        self,
        directory: Path,
        original_name: str,
        data: bytes,
        *,
        scene: str = "TRAIN_DOC",
    ) -> dict[str, str]:
        directory.mkdir(parents=True, exist_ok=True)
        tmp = directory / f".tmp-{uuid4().hex}"
        try:
            if not os.access(directory, os.W_OK):
                raise BizError(5005)
            tmp.write_bytes(data)
            final_name = f"{uuid4().hex}{Path(original_name).suffix}"
            final = directory / final_name
            tmp.replace(final)
        except BizError:
            if tmp.exists():
                tmp.unlink()
            raise
        except OSError as exc:
            if tmp.exists():
                tmp.unlink()
            raise BizError(5005) from exc

        from app.domains.sys.models import StoredFile

        session = get_db_session()
        row = StoredFile(
            tenant_id=ctx.tenant_id or 1,
            scene=scene,
            file_key=final_name,
            original_name=original_name,
            uploader_id=ctx.user_id or 0,
        )
        assign_pk(session, row)
        session.add(row)
        session.flush()
        return {"file_key": row.file_key, "original_name": row.original_name}

    def download(self, file_id: int, user_id: int, dept_ids: Optional[list[int]] = None) -> dict[str, str]:
        """Bound files follow data scope. Unbound files are owner-only."""
        from app.domains.sys.models import StoredFile

        session = get_db_session()
        row = session.query(StoredFile).filter(
            StoredFile.id == file_id,
            StoredFile.deleted == 0,
        ).first()
        if row is None or row.tenant_id != (ctx.tenant_id or row.tenant_id):
            raise BizError(1504)
        if row.biz_type:
            allowed = set(dept_ids or [])
            if row.biz_dept_id not in allowed:
                raise BizError(1504)
        elif row.uploader_id != user_id:
            raise BizError(1504)
        return {
            "file_key": row.file_key,
            "filename": row.original_name,
            "content_disposition": f'attachment; filename="{row.original_name}"',
        }
