# 证件路由。版本 v1.0 · 2026-10-13
"""证件不挂 scope_model。这里不写地址或模型名。"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response

from app.api.deps import require_any_permission, require_login, require_permission
from app.core.response import CommonResult
from app.core.serialization import BaseSchema
from app.services.cert import CERT_DIR, CertService
from app.services.cert_expire import CertExpireService
from app.services.cert_file import apply_watermark
from app.services.cert_security import CertSecurityService, build_watermark_text, resolve_preview

router = APIRouter()

ARCHIVE_READ = ["ims:cert:archive:query", "ims:cert:archive:query-self"]


class ReviewBody(BaseSchema):
    passed: bool
    remark: Optional[str] = None


class OcrBody(BaseSchema):
    file_key: str
    cert_type: Optional[str] = None


class LevelBody(BaseSchema):
    rules: list[dict] = []
    whitelist: list[str] = []


@router.post("/archive/upload", dependencies=[Depends(require_permission("ims:cert:archive:upload"))])
async def cert_upload(
    file: UploadFile = File(...),  # noqa: B008
    holder_type: str = Form(...),
    cert_type: str = Form(...),
    cert_no: str = Form(""),
    realname_id: str = Form(""),
    holder_user_id: str = Form(""),
    holder_name: str = Form(""),
    issue_date: str = Form(""),
    expire_date: str = Form(""),
    renew_from_id: str = Form(""),
    ocr_result: str = Form(""),
) -> CommonResult:
    content = await file.read()
    payload = {
        "holder_type": holder_type,
        "cert_type": cert_type,
        "cert_no": cert_no,
        "realname_id": realname_id or None,
        "holder_user_id": holder_user_id or None,
        "holder_name": holder_name,
        "issue_date": issue_date,
        "expire_date": expire_date,
        "renew_from_id": renew_from_id or None,
        "ocr_result": ocr_result or None,
    }
    return CommonResult.success(
        CertService().upload_cert(payload, file.filename or "", file.content_type or "", content)
    )


@router.get("/archive/list", dependencies=[Depends(require_any_permission(ARCHIVE_READ))])
def cert_list(
    page_no: int = Query(1, alias="pageNo"),
    page_size: int = Query(20, alias="pageSize"),
) -> CommonResult:
    return CommonResult.success(CertService().list_certs(page_no, page_size))


@router.get("/archive/digital-metrics", dependencies=[Depends(require_any_permission(ARCHIVE_READ))])
def cert_metrics() -> CommonResult:
    return CommonResult.success(CertService().digital_metrics())


@router.post("/archive/ocr", dependencies=[Depends(require_permission("ims:cert:archive:upload"))])
def cert_ocr(body: OcrBody) -> CommonResult:
    data = CertService().recognize_cert(body.file_key)
    data.pop("ocrStored", None)
    return CommonResult.success(data)


@router.get("/archive/{cert_id}", dependencies=[Depends(require_any_permission(ARCHIVE_READ))])
def cert_get(cert_id: str) -> CommonResult:
    return CommonResult.success(CertService().get_cert(cert_id))


@router.put("/archive/{cert_id}/review", dependencies=[Depends(require_permission("ims:cert:archive:review"))])
def cert_review(cert_id: str, body: ReviewBody) -> CommonResult:
    return CommonResult.success(CertService().review_cert(cert_id, body.passed, body.remark or ""))


@router.delete("/archive/{cert_id}", dependencies=[Depends(require_permission("ims:cert:archive:delete"))])
def cert_delete(cert_id: str) -> CommonResult:
    CertService().delete_cert(cert_id)
    return CommonResult.success()


@router.get("/security/view/{cert_id}", dependencies=[Depends(require_login)])
def cert_view(cert_id: str) -> CommonResult:
    return CommonResult.success(CertService().view_cert(cert_id))


@router.get("/security/preview/{token}")
def cert_preview(token: str) -> Response:
    data = resolve_preview(token)
    path = CERT_DIR / str(data.get("fileKey") or "")
    raw = path.read_bytes() if path.is_file() else b""
    body = apply_watermark(raw, build_watermark_text()) if raw else b""
    media = "application/pdf" if raw.startswith(b"%PDF") else "image/png"
    return Response(content=body, media_type=media)


@router.get("/security/level-config", dependencies=[Depends(require_permission("ims:cert:security:config"))])
def level_get() -> CommonResult:
    return CommonResult.success(CertSecurityService().get_level_config())


@router.put("/security/level-config", dependencies=[Depends(require_permission("ims:cert:security:config"))])
def level_save(body: LevelBody) -> CommonResult:
    return CommonResult.success(CertSecurityService().save_level_config(body.model_dump()))


@router.get("/security/view-logs", dependencies=[Depends(require_permission("ims:cert:security:audit"))])
def view_logs(
    page_no: int = Query(1, alias="pageNo"),
    page_size: int = Query(20, alias="pageSize"),
) -> CommonResult:
    return CommonResult.success(CertSecurityService().list_view_logs(page_no, page_size))


@router.get("/security/risk-report", dependencies=[Depends(require_permission("ims:cert:security:audit"))])
def risk_report() -> CommonResult:
    return CommonResult.success(CertSecurityService().risk_report())


@router.get("/expire/list", dependencies=[Depends(require_permission("ims:cert:expire:query"))])
def expire_list(
    page_no: int = Query(1, alias="pageNo"),
    page_size: int = Query(20, alias="pageSize"),
) -> CommonResult:
    return CommonResult.success(CertExpireService().list_expire_tasks(page_no, page_size))


@router.get("/expire/stats", dependencies=[Depends(require_permission("ims:cert:expire:query"))])
def expire_stats() -> CommonResult:
    return CommonResult.success(CertExpireService().expire_stats())


@router.post("/expire/scan", dependencies=[Depends(require_permission("ims:cert:expire:scan"))])
def expire_scan(test_now: str = Query("", alias="ims.test.now")) -> CommonResult:
    return CommonResult.success(CertExpireService().scan(test_now or None))


@router.put("/expire/{task_id}/remind", dependencies=[Depends(require_permission("ims:cert:expire:remind"))])
def expire_remind(task_id: str) -> CommonResult:
    return CommonResult.success(CertExpireService().remind_expire(task_id))


@router.put("/expire/{task_id}/renew", dependencies=[Depends(require_permission("ims:cert:expire:renew"))])
async def expire_renew(
    task_id: str,
    file: UploadFile = File(...),  # noqa: B008
    cert_no: str = Form(""),
    issue_date: str = Form(""),
    expire_date: str = Form(""),
) -> CommonResult:
    content = await file.read()
    payload = {"cert_no": cert_no, "issue_date": issue_date, "expire_date": expire_date}
    return CommonResult.success(
        CertExpireService().renew_cert(task_id, payload, file.filename or "", file.content_type or "", content)
    )
