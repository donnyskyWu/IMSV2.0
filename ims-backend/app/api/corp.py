# 公司资源路由。版本 v1.0 · 2026-10-13
"""公司不挂 scope_model。实名人和手机卡挂非空归属。"""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import require_login, require_permission
from app.core.response import CommonResult
from app.core.serialization import BaseSchema
from app.domains.shared.models import MasterRealname, MasterSimCard
from app.services.company import CompanyService
from app.services.realname import RealnameService
from app.services.sim_card import SimCardService

router = APIRouter()


def scoped(model):
    """标到函数上，注册路由时再抄到 route.scope_model。"""

    def wrap(fn):
        fn.__scope_model__ = model
        return fn

    return wrap


class CompanyBody(BaseSchema):
    name: Optional[str] = None
    credit_code: Optional[str] = None
    industry: Optional[str] = None
    address: Optional[str] = None
    legal_name: Optional[str] = None
    legal_id_card: Optional[str] = None
    status: Optional[str] = None


class StatusBody(BaseSchema):
    status: str


class ExpandBody(BaseSchema):
    to_capacity: int
    reason: str


class RealnameBody(BaseSchema):
    name: Optional[str] = None
    user_id: Optional[str] = None
    id_type: Optional[str] = None
    id_card: Optional[str] = None
    change_id_card: Optional[bool] = None
    phone: Optional[str] = None
    wechat: Optional[str] = None
    gender: Optional[str] = None
    status: Optional[str] = None


class IntermediaryBody(BaseSchema):
    name: Optional[str] = None
    phone: Optional[str] = None
    wechat: Optional[str] = None
    relation_type: Optional[str] = None
    commission_rate: Optional[str] = None
    remark: Optional[str] = None


class SimBody(BaseSchema):
    phone: Optional[str] = None
    operator: Optional[str] = None
    realname_id: Optional[str] = None
    assigned_user_id: Optional[str] = None
    iccid: Optional[str] = None
    package_name: Optional[str] = None
    monthly_rent: Optional[str] = None
    status: Optional[str] = None
    is_primary: Optional[bool] = None
    payment_cycle: Optional[str] = None


def _dump(body: BaseSchema) -> dict:
    return body.model_dump(exclude_unset=True)


@router.get("/company/page", dependencies=[Depends(require_permission("ims:corp:company:query"))])
def company_page(
    name: str = "",
    status: str = "",
    page_no: int = Query(1, alias="pageNo"),
    page_size: int = Query(20, alias="pageSize"),
) -> CommonResult:
    return CommonResult.success(CompanyService().page_companies(name, status, page_no, page_size))


@router.get("/company/simple-list", dependencies=[Depends(require_login)])
def company_options(keyword: str = "") -> CommonResult:
    return CommonResult.success(CompanyService().list_company_options(keyword))


@router.post("/company/export", dependencies=[Depends(require_permission("ims:corp:company:export"))])
def company_export(name: str = "", status: str = "") -> CommonResult:
    return CommonResult.success(CompanyService().export_companies(name, status))


@router.get("/company/{company_id}", dependencies=[Depends(require_permission("ims:corp:company:query"))])
def company_get(company_id: str) -> CommonResult:
    return CommonResult.success(CompanyService().get_company(company_id))


@router.post("/company", dependencies=[Depends(require_permission("ims:corp:company:create"))])
def company_create(body: CompanyBody) -> CommonResult:
    return CommonResult.success(CompanyService().create_company(_dump(body)))


@router.put("/company/{company_id}", dependencies=[Depends(require_permission("ims:corp:company:update"))])
def company_update(company_id: str, body: CompanyBody) -> CommonResult:
    return CommonResult.success(CompanyService().update_company(company_id, _dump(body)))


@router.put("/company/{company_id}/status", dependencies=[Depends(require_permission("ims:corp:company:update"))])
def company_status(company_id: str, body: StatusBody) -> CommonResult:
    return CommonResult.success(CompanyService().set_company_status(company_id, body.status))


@router.post("/company/{company_id}/expand", dependencies=[Depends(require_permission("ims:corp:company:expand"))])
def company_expand(company_id: str, body: ExpandBody) -> CommonResult:
    return CommonResult.success(CompanyService().expand_company(company_id, body.to_capacity, body.reason))


@router.get(
    "/realname/page",
    dependencies=[Depends(require_permission("ims:corp:realname:query"))],
)
@scoped(MasterRealname)
def realname_page(
    name: str = "",
    id_card: str = Query("", alias="idCard"),
    page_no: int = Query(1, alias="pageNo"),
    page_size: int = Query(20, alias="pageSize"),
) -> CommonResult:
    return CommonResult.success(RealnameService().page_realnames(name, id_card, page_no, page_size))


@router.get("/realname/simple-list", dependencies=[Depends(require_login)])
def realname_options(keyword: str = "") -> CommonResult:
    return CommonResult.success(RealnameService().list_realname_options(keyword))


@router.post("/realname/export", dependencies=[Depends(require_permission("ims:corp:realname:export"))])
@scoped(MasterRealname)
def realname_export(name: str = "") -> CommonResult:
    return CommonResult.success(RealnameService().export_realnames(name))


@router.post("/realname", dependencies=[Depends(require_permission("ims:corp:realname:create"))])
@scoped(MasterRealname)
def realname_create(body: RealnameBody) -> CommonResult:
    return CommonResult.success(RealnameService().create_realname(_dump(body)))


@router.get("/realname/{realname_id}", dependencies=[Depends(require_permission("ims:corp:realname:query"))])
@scoped(MasterRealname)
def realname_get(realname_id: str) -> CommonResult:
    return CommonResult.success(RealnameService().get_realname(realname_id))


@router.put("/realname/{realname_id}", dependencies=[Depends(require_permission("ims:corp:realname:update"))])
@scoped(MasterRealname)
def realname_update(realname_id: str, body: RealnameBody) -> CommonResult:
    return CommonResult.success(RealnameService().update_realname(realname_id, _dump(body)))


@router.put("/realname/{realname_id}/status", dependencies=[Depends(require_permission("ims:corp:realname:update"))])
@scoped(MasterRealname)
def realname_status(realname_id: str, body: StatusBody) -> CommonResult:
    return CommonResult.success(RealnameService().set_realname_status(realname_id, body.status))


@router.delete("/realname/{realname_id}", dependencies=[Depends(require_permission("ims:corp:realname:delete"))])
@scoped(MasterRealname)
def realname_delete(realname_id: str) -> CommonResult:
    RealnameService().delete_realname(realname_id)
    return CommonResult.success()


@router.post(
    "/realname/{realname_id}/intermediary",
    dependencies=[Depends(require_permission("ims:corp:realname:update"))],
)
@scoped(MasterRealname)
def intermediary_create(realname_id: str, body: IntermediaryBody) -> CommonResult:
    return CommonResult.success(RealnameService().create_intermediary(realname_id, _dump(body)))


@router.put(
    "/realname/intermediary/{intermediary_id}",
    dependencies=[Depends(require_permission("ims:corp:realname:update"))],
)
@scoped(MasterRealname)
def intermediary_update(intermediary_id: str, body: IntermediaryBody) -> CommonResult:
    return CommonResult.success(RealnameService().update_intermediary(intermediary_id, _dump(body)))


@router.delete(
    "/realname/intermediary/{intermediary_id}",
    dependencies=[Depends(require_permission("ims:corp:realname:update"))],
)
@scoped(MasterRealname)
def intermediary_delete(intermediary_id: str) -> CommonResult:
    RealnameService().delete_intermediary(intermediary_id)
    return CommonResult.success()


@router.get("/sim-card/page", dependencies=[Depends(require_permission("ims:corp:sim:query"))])
@scoped(MasterSimCard)
def sim_page(
    phone: str = "",
    page_no: int = Query(1, alias="pageNo"),
    page_size: int = Query(20, alias="pageSize"),
) -> CommonResult:
    return CommonResult.success(SimCardService().page_sim_cards(phone, page_no, page_size))


@router.get("/sim-card/simple-list", dependencies=[Depends(require_login)])
def sim_options(keyword: str = "") -> CommonResult:
    return CommonResult.success(SimCardService().list_sim_card_options(keyword))


@router.post("/sim-card/export", dependencies=[Depends(require_permission("ims:corp:sim:export"))])
@scoped(MasterSimCard)
def sim_export(phone: str = "") -> CommonResult:
    return CommonResult.success(SimCardService().export_sim_cards(phone))


@router.post("/sim-card", dependencies=[Depends(require_permission("ims:corp:sim:create"))])
@scoped(MasterSimCard)
def sim_create(body: SimBody) -> CommonResult:
    return CommonResult.success(SimCardService().create_sim_card(_dump(body)))


@router.get("/sim-card/{sim_id}", dependencies=[Depends(require_permission("ims:corp:sim:query"))])
@scoped(MasterSimCard)
def sim_get(sim_id: str) -> CommonResult:
    return CommonResult.success(SimCardService().get_sim_card(sim_id))


@router.put("/sim-card/{sim_id}", dependencies=[Depends(require_permission("ims:corp:sim:update"))])
@scoped(MasterSimCard)
def sim_update(sim_id: str, body: SimBody) -> CommonResult:
    return CommonResult.success(SimCardService().update_sim_card(sim_id, _dump(body)))


@router.delete("/sim-card/{sim_id}", dependencies=[Depends(require_permission("ims:corp:sim:delete"))])
@scoped(MasterSimCard)
def sim_delete(sim_id: str) -> CommonResult:
    SimCardService().delete_sim_card(sim_id)
    return CommonResult.success()
