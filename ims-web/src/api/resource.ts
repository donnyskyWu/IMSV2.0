/**
 * 公司资源与证件接口。版本 v1.0 · 2026-10-13
 * 路径与后端 corp / cert 路由一致，不在页面里拼第二套地址。
 */
import { request, type CommonResult } from '@/api/request'

const CORP = '/admin-api/ims/corp/resource'
const CERT = '/admin-api/ims/cert'

export interface CompanyRow {
  id: string
  name: string
  creditCode: string
  industry: string
  legalName: string
  legalIdCard?: string
  address?: string
  status: string
  statusCode: string
  mpCapacity: number
  mpRegistered: number
  capacityTight: boolean
  expansions?: Array<{
    id: string
    fromCapacity: number
    toCapacity: number
    reason: string
    operatorName?: string
  }>
}

export interface RealnameRow {
  id: string
  name: string
  userId: string
  idType: string
  idCard: string
  phone: string
  wechat: string
  status: string
  statusCode: string
  intermediaryCount: number
  intermediaryText: string
  intermediaries?: IntermediaryRow[]
  certs?: Array<{ id: string; name: string }>
  sims?: Array<{ id: string; name: string }>
}

export interface IntermediaryRow {
  id: string
  name: string
  phone: string
  commissionRate?: string
  relationType: string
}

export interface SimRow {
  id: string
  name: string
  phone: string
  realnameId: string
  realnameName?: string
  operator: string
  operatorLabel?: string
  monthlyRent: string
  iccid?: string
  status: string
  statusCode: string
  accounts?: unknown[]
}

export interface CertRow {
  id: string
  name: string
  holderType: string
  holderName: string
  external: boolean
  realnameId: string
  certType: string
  certTypeLabel?: string
  certNo: string
  status: string
  statusLabel?: string
  warnLevel: string
  version: number
  creatorId?: string
  daysLeft?: number | null
  fileKey?: string
  isLocked?: boolean
}

export interface OptionRow {
  id: string
  name: string
  phone?: string
}

function ok<T>(result: CommonResult<T>): T {
  return (result.data ?? null) as T
}

export async function pageCompanies(params: { name?: string; status?: string }) {
  const result = await request.get<CommonResult<{ list: CompanyRow[]; total: number }>>(`${CORP}/company/page`, { params })
  return ok(result)
}

export async function getCompany(id: string) {
  const result = await request.get<CommonResult<CompanyRow>>(`${CORP}/company/${id}`)
  return ok(result)
}

export async function createCompany(payload: Record<string, unknown>) {
  const result = await request.post<CommonResult<CompanyRow>>(`${CORP}/company`, payload)
  return ok(result)
}

export async function updateCompanyStatus(id: string, status: string) {
  const result = await request.put<CommonResult<CompanyRow>>(`${CORP}/company/${id}/status`, { status })
  return ok(result)
}

export async function expandCompany(id: string, toCapacity: number, reason: string) {
  const result = await request.post<CommonResult<CompanyRow>>(`${CORP}/company/${id}/expand`, { toCapacity, reason })
  return ok(result)
}

export async function exportCompanies(params: { name?: string; status?: string }) {
  const result = await request.post<CommonResult<{ taskId: string }>>(`${CORP}/company/export`, params)
  return ok(result)
}

export async function listCompanyOptions(keyword = '') {
  const result = await request.get<CommonResult<OptionRow[]>>(`${CORP}/company/simple-list`, { params: { keyword } })
  return ok(result) || []
}

export async function pageRealnames(params: { name?: string; idCard?: string; status?: string }) {
  const result = await request.get<CommonResult<{ list: RealnameRow[]; total: number }>>(`${CORP}/realname/page`, { params })
  return ok(result)
}

export async function getRealname(id: string) {
  const result = await request.get<CommonResult<RealnameRow>>(`${CORP}/realname/${id}`)
  return ok(result)
}

export async function createRealname(payload: Record<string, unknown>) {
  const result = await request.post<CommonResult<RealnameRow>>(`${CORP}/realname`, payload)
  return ok(result)
}

export async function updateRealnameStatus(id: string, status: string) {
  const result = await request.put<CommonResult<RealnameRow>>(`${CORP}/realname/${id}/status`, { status })
  return ok(result)
}

export async function deleteRealname(id: string) {
  // 页面要带上引用次数，避免和全局提示各弹一次。
  await request.delete(`${CORP}/realname/${id}`, { skipGlobalError: true })
}

export async function createIntermediary(realnameId: string, payload: Record<string, unknown>) {
  const result = await request.post<CommonResult<IntermediaryRow>>(`${CORP}/realname/${realnameId}/intermediary`, payload)
  return ok(result)
}

export async function exportRealnames(params: { status?: string }) {
  const result = await request.post<CommonResult<{ taskId: string }>>(`${CORP}/realname/export`, params)
  return ok(result)
}

export async function listRealnameOptions(keyword = '') {
  const result = await request.get<CommonResult<OptionRow[]>>(`${CORP}/realname/simple-list`, { params: { keyword } })
  return ok(result) || []
}

export async function pageSimCards(params: { operator?: string; phone?: string }) {
  const result = await request.get<CommonResult<{ list: SimRow[]; total: number }>>(`${CORP}/sim-card/page`, { params })
  return ok(result)
}

export async function getSimCard(id: string) {
  const result = await request.get<CommonResult<SimRow>>(`${CORP}/sim-card/${id}`)
  return ok(result)
}

export async function createSimCard(payload: Record<string, unknown>) {
  const result = await request.post<CommonResult<SimRow>>(`${CORP}/sim-card`, payload)
  return ok(result)
}

export async function updateSimCard(id: string, payload: Record<string, unknown>) {
  const result = await request.put<CommonResult<SimRow>>(`${CORP}/sim-card/${id}`, payload)
  return ok(result)
}

export async function deleteSimCard(id: string) {
  await request.delete(`${CORP}/sim-card/${id}`)
}

export async function exportSimCards() {
  const result = await request.post<CommonResult<{ taskId: string }>>(`${CORP}/sim-card/export`, {})
  return ok(result)
}

export async function listSimOptions(keyword = '') {
  const result = await request.get<CommonResult<OptionRow[]>>(`${CORP}/sim-card/simple-list`, { params: { keyword } })
  return ok(result) || []
}

export async function listCerts() {
  const result = await request.get<CommonResult<{ list: CertRow[]; total: number }>>(`${CERT}/archive/list`)
  return ok(result)
}

export async function digitalMetrics() {
  const result = await request.get<CommonResult<{ total: number; covered: number; rate: string }>>(`${CERT}/archive/digital-metrics`)
  return ok(result)
}

export async function uploadCert(payload: Record<string, unknown>) {
  // 1032 由上传抽屉自己出确认框，不走全局 toast。
  const result = await request.post<CommonResult<CertRow>>(`${CERT}/archive/upload`, payload, { skipGlobalError: true })
  return ok(result)
}

export async function reviewCert(id: string, passed: boolean, remark: string) {
  const result = await request.put<CommonResult<CertRow>>(`${CERT}/archive/${id}/review`, { passed, remark })
  return ok(result)
}

export async function deleteCert(id: string) {
  await request.delete(`${CERT}/archive/${id}`)
}

export async function recognizeCert(fileKey: string) {
  const result = await request.post<CommonResult<{
    recognized: boolean
    name?: string
    certNo?: string
    issueDate?: string
    expireDate?: string
  }>>(`${CERT}/archive/ocr`, { fileKey })
  return ok(result)
}

export async function viewCert(id: string) {
  const result = await request.get<CommonResult<{
    previewUrl: string
    watermarkText: string
    viewLevel: number
    certNo: string
  }>>(`${CERT}/security/view/${id}`)
  return ok(result)
}

export async function expireStats() {
  const result = await request.get<CommonResult<{ YELLOW: number; RED: number; LOCKED: number }>>(`${CERT}/expire/stats`)
  return ok(result)
}

export async function listExpireTasks() {
  const result = await request.get<CommonResult<{ list: Array<Record<string, unknown>>; total: number }>>(`${CERT}/expire/list`)
  return ok(result)
}

export async function scanExpire(testNow?: string) {
  const result = await request.post<CommonResult<{ notified: number }>>(`${CERT}/expire/scan`, { testNow })
  return ok(result)
}

export async function remindExpire(taskId: string) {
  const result = await request.put<CommonResult<{ reminded: boolean; remindCount: number }>>(`${CERT}/expire/${taskId}/remind`, {})
  return ok(result)
}

export async function renewCert(taskId: string, payload: Record<string, unknown>) {
  const result = await request.put<CommonResult<CertRow>>(`${CERT}/expire/${taskId}/renew`, payload)
  return ok(result)
}

export async function getLevelConfig() {
  const result = await request.get<CommonResult<{ rules: Array<{ roleId: string; viewLevel: number; roleName?: string }>; whitelist: string[] }>>(`${CERT}/security/level-config`)
  return ok(result)
}

export async function saveLevelConfig(payload: Record<string, unknown>) {
  const result = await request.put<CommonResult<unknown>>(`${CERT}/security/level-config`, payload)
  return ok(result)
}

export async function listViewLogs(viewer = '') {
  const result = await request.get<CommonResult<{ list: Array<Record<string, string>>; total: number }>>(`${CERT}/security/view-logs`, { params: { viewer } })
  return ok(result)
}

export async function riskReport() {
  const result = await request.get<CommonResult<{ users: Array<{ userId: string; name?: string; count: number }> }>>(`${CERT}/security/risk-report`)
  return ok(result)
}
