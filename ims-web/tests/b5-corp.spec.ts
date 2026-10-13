/**
 * B5 公司资源 Playwright。接口在浏览器里桩掉，页面按 02 的按钮和文案走。
 * 版本 v1.0 · 2026-10-13
 */
import { expect, test, type Page, type Route } from '@playwright/test'

const ID_A = '110101199003078515'
const ID_B = '110101199001011237'

interface Company {
  id: string
  name: string
  creditCode: string
  mpCapacity: number
  mpRegistered: number
  statusCode: string
  legalIdCard: string
  expansions: Array<{ id: string; fromCapacity: number; toCapacity: number; reason: string; operatorName: string }>
}

interface Person {
  id: string
  name: string
  idCard: string
  phone: string
  statusCode: string
  people: Array<{ id: string; name: string; commissionRate: string }>
}

interface Sim {
  id: string
  phone: string
  operator: string
  realnameId: string
  monthlyRent: string
  iccid: string
  statusCode: string
}

interface Cert {
  id: string
  holderName: string
  holderType: string
  realnameId: string
  certType: string
  certNo: string
  status: string
  warnLevel: string
  creatorId: string
  daysLeft: number | null
  isLocked: boolean
  external: boolean
}

interface World {
  seq: number
  companies: Company[]
  people: Person[]
  sims: Sim[]
  certs: Cert[]
  tasks: Array<{ id: string; certName: string; level: string; status: string; remindCount: number }>
  logs: Array<{ viewerName: string; result: string }>
  views: number
  levels: Record<string, number>
  ocr: boolean
  risks: Array<{ userId: string; name: string; count: number }>
}

const LABELS: Record<string, string> = {
  ENABLED: '启用',
  DISABLED: '停用',
  ON_JOB: '在职',
  LEFT: '离职',
  CMCC: '移动',
  CUCC: '联通',
  ID_CARD: '居民身份证',
  PASSPORT: '护照',
  HEALTH: '健康证',
}

function maskId(value: string) {
  if (value.length < 8) return value
  return `${value.slice(0, 3)}${'*'.repeat(Math.max(value.length - 7, 1))}${value.slice(-4)}`
}

function maskPhone(value: string) {
  if (value.length < 7) return value
  return `${value.slice(0, 3)}****${value.slice(-4)}`
}

/** 18 位身份证校验位。桩接口与后端同一规则，错位要回 1001。 */
function idOk(value: string) {
  if (!/^\d{17}[\dX]$/.test(value)) return false
  const weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
  const codes = '10X98765432'
  const sum = weights.reduce((total, weight, index) => total + Number(value[index]) * weight, 0)
  return codes[sum % 11] === value[17]
}

function fresh(): World {
  return {
    seq: 10,
    companies: [],
    people: [],
    sims: [],
    certs: [],
    tasks: [],
    logs: [],
    views: 0,
    levels: { admin: 3, xz: 2, xz2: 2, ro: 1, self: 1 },
    ocr: true,
    risks: [],
  }
}

function nextId(world: World) {
  world.seq += 1
  return String(world.seq)
}

function companyView(row: Company) {
  const left = row.mpCapacity - row.mpRegistered
  return {
    id: row.id,
    name: row.name,
    creditCode: row.creditCode,
    legalIdCard: maskId(row.legalIdCard),
    status: LABELS[row.statusCode],
    statusCode: row.statusCode,
    mpCapacity: row.mpCapacity,
    mpRegistered: row.mpRegistered,
    capacityTight: left < 5,
    expansions: row.expansions,
  }
}

function personView(row: Person, seeCommission: boolean) {
  return {
    id: row.id,
    name: row.name,
    idCard: maskId(row.idCard),
    phone: maskPhone(row.phone),
    status: LABELS[row.statusCode],
    statusCode: row.statusCode,
    intermediaryText: row.people.length ? `${row.people[0].name} 等 ${row.people.length} 人` : '',
    intermediaries: row.people.map((item) => ({
      id: item.id,
      name: item.name,
      commissionRate: seeCommission ? item.commissionRate : undefined,
    })),
    certs: [],
    sims: [],
  }
}

const PERMS: Record<string, string[]> = {
  admin: [
    'ims:corp:company:query', 'ims:corp:company:create', 'ims:corp:company:update',
    'ims:corp:company:expand', 'ims:corp:company:export',
    'ims:corp:realname:query', 'ims:corp:realname:create', 'ims:corp:realname:update',
    'ims:corp:realname:delete', 'ims:corp:realname:export', 'ims:corp:realname:commission',
    'ims:corp:sim:query', 'ims:corp:sim:create', 'ims:corp:sim:update', 'ims:corp:sim:delete', 'ims:corp:sim:export',
    'ims:cert:archive:query', 'ims:cert:archive:upload', 'ims:cert:archive:review', 'ims:cert:archive:delete',
    'ims:cert:expire:query', 'ims:cert:expire:scan', 'ims:cert:expire:renew', 'ims:cert:expire:remind',
    'ims:cert:security:config', 'ims:cert:security:audit',
  ],
  xz: [],
  ro: [
    'ims:corp:company:query', 'ims:corp:realname:query', 'ims:corp:sim:query', 'ims:cert:archive:query',
  ],
  self: ['ims:cert:archive:query-self'],
  yg: [],
  reset: ['ims:corp:company:query', 'ims:cert:archive:query'],
}
PERMS.xz = PERMS.admin.filter((code) => code !== 'ims:cert:archive:delete' && code !== 'ims:cert:security:config')
PERMS.xz2 = PERMS.xz

const USERS: Record<string, { id: string; nickname: string }> = {
  admin: { id: '1', nickname: '测试管理员' },
  xz: { id: '2', nickname: 'test_xz' },
  xz2: { id: '3', nickname: 'test_xz2' },
  ro: { id: '4', nickname: 'test_ro' },
  self: { id: '5', nickname: 'test_self' },
  yg: { id: '6', nickname: 'test_yg' },
  reset: { id: '7', nickname: 'test_reset' },
}

function menusFor(role: string) {
  const asset = {
    id: 'asset',
    name: '公司资产',
    children: [{
      id: 'res',
      name: '资源管理',
      children: [
        { id: 'co', name: '公司管理', path: '/ims/corp/resource/company', children: [] },
        { id: 'rn', name: '实名人管理', path: '/ims/corp/resource/realname', children: [] },
        { id: 'sm', name: '手机卡管理', path: '/ims/corp/resource/sim-card', children: [] },
        { id: 'ct', name: '证件管理', path: '/ims/corp/resource/certificate', children: [] },
      ],
    }],
  }
  const auth = {
    id: 'auth',
    name: '权限管理',
    children: [{ id: 'org', name: '组织架构同步', path: '/ims/auth/org', children: [] }],
  }
  if (role === 'yg') return [auth]
  if (role === 'self') {
    return [{
      id: 'asset',
      name: '公司资产',
      children: [{
        id: 'res',
        name: '资源管理',
        children: [{ id: 'ct', name: '证件管理', path: '/ims/corp/resource/certificate', children: [] }],
      }],
    }]
  }
  return [auth, asset]
}

function reply(route: Route, code: number, data: unknown, msg = 'ok') {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code, msg, data }),
  })
}

async function handle(route: Route, world: World, role: () => string) {
  const request = route.request()
  const url = new URL(request.url())
  const path = url.pathname
  const method = request.method()
  const current = role()
  const user = USERS[current]
  const perms = PERMS[current] || []
  let body: Record<string, unknown> = {}
  if (method !== 'GET' && method !== 'DELETE') {
    try {
      body = request.postDataJSON() as Record<string, unknown>
    } catch {
      body = {}
    }
  }

  if (path.endsWith('/auth/me')) {
    return reply(route, 0, {
      dataScopeText: '全部',
      menus: menusFor(current),
      permCodes: perms,
      permDetails: {},
      user: {
        id: user.id,
        username: current,
        nickname: user.nickname,
        avatar: null,
        deptNames: [],
        mainDeptName: '',
        pwdResetRequired: current === 'reset',
      },
    })
  }

  if (current === 'reset' && !path.endsWith('/auth/me')) return reply(route, 1008, null, '暂无权限')
  if (current === 'yg' && path.includes('/corp/resource/company/page')) return reply(route, 1008, null, '暂无权限')

  if (path.endsWith('/company/page') && method === 'GET') {
    let list = world.companies.map(companyView)
    const status = url.searchParams.get('status')
    const name = url.searchParams.get('name')
    if (status) list = list.filter((item) => item.statusCode === status)
    if (name) list = list.filter((item) => item.name.includes(name))
    return reply(route, 0, { list, total: list.length })
  }
  if (path.endsWith('/company/simple-list')) {
    const list = world.companies.filter((item) => item.statusCode === 'ENABLED').map((item) => ({ id: item.id, name: item.name }))
    return reply(route, 0, list)
  }
  if (path.endsWith('/company/export')) {
    return reply(route, 0, { taskId: 'exp-co' })
  }
  if (method === 'POST' && path.endsWith('/company')) {
    if (!perms.includes('ims:corp:company:create')) return reply(route, 1008, null, '暂无权限')
    const name = String(body.name || '')
    if (world.companies.some((item) => item.name === name)) return reply(route, 1001, null, '公司名称已存在')
    if (body.creditCode && String(body.creditCode).length < 18) return reply(route, 1001, null, '信用代码格式不正确')
    const row: Company = {
      id: nextId(world),
      name,
      creditCode: String(body.creditCode || ''),
      mpCapacity: Number(body.mpCapacity || 0),
      mpRegistered: 0,
      statusCode: 'ENABLED',
      legalIdCard: '110101199003078515',
      expansions: [],
    }
    world.companies.push(row)
    return reply(route, 0, companyView(row))
  }
  const companyId = path.match(/\/company\/([^/]+)$/)
  if (companyId && method === 'GET') {
    const row = world.companies.find((item) => item.id === companyId[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    return reply(route, 0, companyView(row))
  }
  const statusMatch = path.match(/\/company\/([^/]+)\/status$/)
  if (statusMatch && method === 'PUT') {
    const row = world.companies.find((item) => item.id === statusMatch[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    row.statusCode = String(body.status)
    return reply(route, 0, companyView(row))
  }
  const expandMatch = path.match(/\/company\/([^/]+)\/expand$/)
  if (expandMatch) {
    const row = world.companies.find((item) => item.id === expandMatch[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    const target = Number(body.toCapacity)
    if (row.mpRegistered > target) return reply(route, 1222, null, '容量不能小于已注册数')
    row.expansions.push({
      id: nextId(world),
      fromCapacity: row.mpCapacity,
      toCapacity: target,
      reason: String(body.reason || ''),
      operatorName: user.nickname,
    })
    row.mpCapacity = target
    return reply(route, 0, companyView(row))
  }

  if (path.endsWith('/realname/page')) {
    let list = world.people.map((item) => personView(item, perms.includes('ims:corp:realname:commission')))
    const card = url.searchParams.get('idCard')
    if (card) list = list.filter((item) => world.people.find((person) => person.id === item.id)?.idCard === card)
    return reply(route, 0, { list, total: list.length })
  }
  if (path.endsWith('/realname/simple-list')) {
    return reply(route, 0, world.people.filter((item) => item.statusCode === 'ON_JOB').map((item) => ({ id: item.id, name: item.name })))
  }
  if (path.endsWith('/realname/export')) return reply(route, 0, { taskId: 'exp-rn' })
  if (method === 'POST' && path.endsWith('/realname')) {
    const card = String(body.idCard || '')
    if (body.idType === 'ID_CARD' && !idOk(card)) return reply(route, 1001, null, '身份证号不合法')
    if (world.people.some((item) => item.idCard === card)) return reply(route, 1001, null, '证件号已存在')
    const row: Person = {
      id: nextId(world), name: String(body.name), idCard: card, phone: String(body.phone || '13812345678'),
      statusCode: 'ON_JOB', people: [],
    }
    world.people.push(row)
    return reply(route, 0, personView(row, true))
  }
  const personGet = path.match(/\/realname\/([^/]+)$/)
  if (personGet && method === 'GET') {
    const row = world.people.find((item) => item.id === personGet[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    const view = personView(row, perms.includes('ims:corp:realname:commission'))
    view.certs = world.certs.filter((item) => item.realnameId === row.id).map((item) => ({ id: item.id, name: item.holderName }))
    view.sims = world.sims.filter((item) => item.realnameId === row.id).map((item) => ({ id: item.id, name: maskPhone(item.phone) }))
    return reply(route, 0, view)
  }
  const personStatus = path.match(/\/realname\/([^/]+)\/status$/)
  if (personStatus) {
    const row = world.people.find((item) => item.id === personStatus[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    row.statusCode = String(body.status)
    return reply(route, 0, personView(row, true))
  }
  const personDelete = path.match(/\/realname\/([^/]+)$/)
  if (personDelete && method === 'DELETE') {
    const row = world.people.find((item) => item.id === personDelete[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    const refs = []
    const simCount = world.sims.filter((item) => item.realnameId === row.id).length
    const certCount = world.certs.filter((item) => item.realnameId === row.id).length
    if (simCount) refs.push({ type: 'sim', count: simCount })
    if (certCount) refs.push({ type: 'cert', count: certCount })
    if (refs.length) return reply(route, 1502, { refs }, '关联的实体已被其他记录引用')
    world.people = world.people.filter((item) => item.id !== row.id)
    return reply(route, 0, null)
  }
  const addPerson = path.match(/\/realname\/([^/]+)\/intermediary$/)
  if (addPerson && method === 'POST') {
    const row = world.people.find((item) => item.id === addPerson[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    row.people.push({ id: nextId(world), name: String(body.name), commissionRate: String(body.commissionRate || '') })
    return reply(route, 0, { id: row.people.at(-1)?.id, name: body.name })
  }

  if (path.endsWith('/sim-card/page')) {
    let list = world.sims
    const operator = url.searchParams.get('operator')
    const phone = url.searchParams.get('phone')
    if (operator) list = list.filter((item) => item.operator === operator)
    if (phone) list = list.filter((item) => item.phone.includes(phone))
    return reply(route, 0, {
      list: list.map((item) => ({
        id: item.id,
        phone: maskPhone(item.phone),
        operator: item.operator,
        operatorLabel: LABELS[item.operator],
        realnameId: item.realnameId,
        realnameName: world.people.find((person) => person.id === item.realnameId)?.name || '',
        monthlyRent: Number(item.monthlyRent).toFixed(2),
        statusCode: item.statusCode,
        accounts: [],
      })),
      total: list.length,
    })
  }
  if (path.endsWith('/sim-card/simple-list')) {
    return reply(route, 0, world.sims.filter((item) => item.statusCode === 'ENABLED').map((item) => ({ id: item.id, name: maskPhone(item.phone) })))
  }
  if (path.endsWith('/sim-card/export')) return reply(route, 0, { taskId: 'exp-sm' })
  if (method === 'POST' && path.endsWith('/sim-card')) {
    const person = world.people.find((item) => item.id === String(body.realnameId))
    if (person && person.statusCode !== 'ON_JOB') return reply(route, 1501, null, '实名人已离职')
    if (world.sims.some((item) => item.phone === body.phone)) return reply(route, 1001, null, '手机号已存在')
    if (body.iccid && world.sims.some((item) => item.iccid === body.iccid)) return reply(route, 1001, null, 'ICCID已存在')
    const row: Sim = {
      id: nextId(world),
      phone: String(body.phone),
      operator: String(body.operator),
      realnameId: String(body.realnameId),
      monthlyRent: String(body.monthlyRent || '0'),
      iccid: String(body.iccid || ''),
      statusCode: 'ENABLED',
    }
    world.sims.push(row)
    return reply(route, 0, { id: row.id })
  }
  const simGet = path.match(/\/sim-card\/([^/]+)$/)
  if (simGet && method === 'GET') {
    const row = world.sims.find((item) => item.id === simGet[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    const owner = world.people.find((item) => item.id === row.realnameId)
    return reply(route, 0, {
      id: row.id,
      phone: maskPhone(row.phone),
      realnameId: row.realnameId,
      realnameName: owner?.name || '',
      monthlyRent: Number(row.monthlyRent).toFixed(2),
      accounts: [],
    })
  }
  const simPut = path.match(/\/sim-card\/([^/]+)$/)
  if (simPut && method === 'PUT') {
    const row = world.sims.find((item) => item.id === simPut[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    if (body.iccid && world.sims.some((item) => item.iccid === body.iccid && item.id !== row.id)) {
      return reply(route, 1001, null, 'ICCID已存在')
    }
    if (body.iccid) row.iccid = String(body.iccid)
    return reply(route, 0, { id: row.id, phone: maskPhone(row.phone) })
  }
  const simDel = path.match(/\/sim-card\/([^/]+)$/)
  if (simDel && method === 'DELETE') {
    world.sims = world.sims.filter((item) => item.id !== simDel[1])
    return reply(route, 0, null)
  }

  if (path.endsWith('/archive/list')) {
    let list = world.certs
    if (perms.includes('ims:cert:archive:query-self') && !perms.includes('ims:cert:archive:query')) {
      list = list.filter((item) => item.holderName.includes('自'))
    }
    return reply(route, 0, {
      list: list.map((item) => ({
        ...item,
        certTypeLabel: LABELS[item.certType] || item.certType,
        certNo: maskId(item.certNo),
      })),
      total: list.length,
    })
  }
  if (path.endsWith('/digital-metrics')) {
    const active = world.people.filter((item) => item.statusCode === 'ON_JOB')
    const covered = active.filter((item) => world.certs.some((cert) => cert.realnameId === item.id && cert.certType === 'ID_CARD' && cert.status === 'EFFECTIVE')).length
    const rate = active.length ? ((covered / active.length) * 100).toFixed(2) : '0.00'
    return reply(route, 0, { total: active.length, covered, rate })
  }
  if (path.endsWith('/archive/upload') || path.match(/\/expire\/[^/]+\/renew$/)) {
    const holderName = String(body.holderName || world.people.find((item) => item.id === body.realnameId)?.name || '持有人')
    const duplicated = world.certs.some((item) => item.realnameId === body.realnameId && item.certType === body.certType && ['EFFECTIVE', 'PENDING_REVIEW'].includes(item.status))
    if (duplicated && !path.includes('/renew')) return reply(route, 1032, null, '已存在有效档案，如为新证请走换证流程')
    const row: Cert = {
      id: nextId(world),
      holderName,
      holderType: String(body.holderType || 'REALNAME'),
      realnameId: String(body.realnameId || ''),
      certType: String(body.certType),
      certNo: String(body.certNo),
      status: 'PENDING_REVIEW',
      warnLevel: '',
      creatorId: user.id,
      daysLeft: 365,
      isLocked: false,
      external: body.holderType === 'EXTERNAL',
    }
    world.certs.push(row)
    return reply(route, 0, row)
  }
  if (path.endsWith('/archive/ocr')) {
    if (!world.ocr) return reply(route, 0, { recognized: false })
    return reply(route, 0, {
      recognized: true,
      name: '张三',
      certNo: ID_A,
      issueDate: '2020-01-01',
      expireDate: '2030-01-01',
    })
  }
  const review = path.match(/\/archive\/([^/]+)\/review$/)
  if (review) {
    const row = world.certs.find((item) => item.id === review[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    if (row.creatorId === user.id) return reply(route, 1008, null, '不能审核自己上传的证件')
    if (row.status !== 'PENDING_REVIEW') return reply(route, 1033, null, '不是待审证件')
    if (!body.passed && !String(body.remark || '').trim()) return reply(route, 1001, null, '原因必填')
    row.status = body.passed ? 'EFFECTIVE' : 'REJECTED'
    if (row.daysLeft != null && row.daysLeft <= 7) row.warnLevel = 'RED'
    if (row.daysLeft != null && row.daysLeft > 7 && row.daysLeft <= 30) row.warnLevel = 'YELLOW'
    if (row.daysLeft != null && row.daysLeft <= 0) row.warnLevel = 'LOCKED'
    return reply(route, 0, row)
  }
  const certDelete = path.match(/\/archive\/([^/]+)$/)
  if (certDelete && method === 'DELETE') {
    if (!perms.includes('ims:cert:archive:delete')) return reply(route, 1008, null, '暂无权限')
    const row = world.certs.find((item) => item.id === certDelete[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    if (row.isLocked) return reply(route, 1502, null, '证件已锁定，不可删除')
    world.certs = world.certs.filter((item) => item.id !== row.id)
    return reply(route, 0, null)
  }
  const view = path.match(/\/security\/view\/([^/]+)$/)
  if (view) {
    const row = world.certs.find((item) => item.id === view[1])
    if (!row) return reply(route, 1504, null, '资源不存在')
    const level = world.levels[current] || 1
    world.views += 1
    if (world.views >= 11) {
      world.risks = [{ userId: user.id, name: user.nickname, count: world.views }]
      world.logs.push({ viewerName: user.nickname, result: '拒绝' })
      return reply(route, 1035, null, '查看次数过多')
    }
    if (level <= 1) {
      world.logs.push({ viewerName: user.nickname, result: '拒绝' })
      return reply(route, 1034, null, '访问级别不足')
    }
    world.logs.push({ viewerName: user.nickname, result: '成功' })
    return reply(route, 0, {
      previewUrl: '/preview/demo.png',
      watermarkText: `E${user.id} ${user.nickname} 2026-10-13 09:00`,
      viewLevel: level,
      certNo: level >= 3 ? row.certNo : maskId(row.certNo),
    })
  }
  if (path.endsWith('/expire/stats')) {
    if (!perms.includes('ims:cert:expire:query')) return reply(route, 1008, null, '暂无权限')
    return reply(route, 0, {
      YELLOW: world.tasks.filter((item) => item.level === 'YELLOW').length,
      RED: world.tasks.filter((item) => item.level === 'RED').length,
      LOCKED: world.tasks.filter((item) => item.level === 'LOCKED').length,
    })
  }
  if (path.endsWith('/expire/list')) {
    if (!perms.includes('ims:cert:expire:query')) return reply(route, 1008, null, '暂无权限')
    return reply(route, 0, { list: world.tasks, total: world.tasks.length })
  }
  if (path.endsWith('/expire/scan')) {
    return reply(route, 0, { notified: 0 })
  }
  const remind = path.match(/\/expire\/([^/]+)\/remind$/)
  if (remind) {
    const task = world.tasks.find((item) => item.id === remind[1])
    if (!task) return reply(route, 1504, null, '资源不存在')
    if (task.remindCount >= 1) return reply(route, 0, { reminded: false, remindCount: task.remindCount })
    task.remindCount += 1
    return reply(route, 0, { reminded: true, remindCount: task.remindCount })
  }
  if (path.endsWith('/security/level-config') && method === 'PUT') {
    if (!perms.includes('ims:cert:security:config')) return reply(route, 1008, null, '暂无权限')
    world.levels.ro = Number(body.rules?.[0]?.viewLevel || 1)
    return reply(route, 0, { rules: body.rules || [] })
  }
  if (path.endsWith('/security/level-config')) return reply(route, 0, { rules: [], whitelist: [] })
  if (path.endsWith('/security/view-logs')) {
    const viewer = url.searchParams.get('viewer') || ''
    const list = world.logs.filter((item) => !viewer || item.viewerName.includes(viewer))
    return reply(route, 0, { list, total: list.length })
  }
  if (path.endsWith('/security/risk-report')) return reply(route, 0, { users: world.risks })
  if (path.includes('/cert/archive/') && method === 'GET') return reply(route, 1504, null, '资源不存在')
  return reply(route, 0, { list: [], total: 0 })
}

async function boot(page: Page, roleName: string, world = fresh()) {
  let role = roleName
  await page.addInitScript((reset) => {
    localStorage.setItem('ims_access_token', 'b5-token')
    localStorage.setItem('ims_refresh_token', 'b5-refresh')
    if (reset) sessionStorage.setItem('ims_pwd_reset', '1')
    else sessionStorage.removeItem('ims_pwd_reset')
  }, roleName === 'reset')
  await page.route('**/admin-api/**', (route) => handle(route, world, () => role))
  return {
    world,
    async switchRole(next: string) {
      role = next
      await page.reload()
    },
  }
}

/** 下拉的占位在 span 上，点整块选择器才能打开选项。 */
async function openSelect(page: Page, label: string) {
  await page.locator('.el-select').filter({ hasText: label }).last().click()
}

/** 选中后等到选项层收起，避免它挡住抽屉里的保存。 */
async function choose(page: Page, label: string, option: string) {
  await openSelect(page, label)
  await page.getByRole('option', { name: option }).click()
  await expect(page.getByRole('listbox')).toBeHidden()
}

/** 抽屉里的输入。列表筛选用同名占位时不要点到外面那一个。 */
function inDrawer(page: Page, placeholder: string) {
  return page.locator('.el-drawer:visible').getByPlaceholder(placeholder)
}

async function openMenu(page: Page, leaf: string) {
  if ((page.viewportSize()?.width || 1440) < 768) {
    const drawer = page.locator('.sidebar').first()
    const hidden = await drawer.evaluate((el) => el.classList.contains('mobile-hidden'))
    if (hidden) await page.locator('.menu-btn').tap()
  }
  const sidebar = page.locator('.sidebar')
  const leafItem = sidebar.getByText(leaf, { exact: true })
  if (await leafItem.isVisible().catch(() => false)) {
    await leafItem.click()
    return
  }
  const asset = sidebar.getByText('公司资产', { exact: true })
  if (await asset.count()) await asset.click()
  if (!(await leafItem.isVisible().catch(() => false))) {
    const group = sidebar.getByRole('menuitem', { name: '资源管理', exact: true })
    if (await group.count()) await group.click()
  }
  await leafItem.click()
}

test('E2E-B5-CO-01 进入页面与列表元素', async ({ page }) => {
  await boot(page, 'xz')
  await page.goto('/ims/corp/resource/company')
  await openMenu(page, '公司管理')
  const sidebar = page.locator('.sidebar')
  const text = await sidebar.innerText()
  expect(text.indexOf('权限管理')).toBeLessThan(text.indexOf('公司资产'))
  await expect(sidebar.getByText('资源管理')).toBeVisible()
  await expect(page.getByRole('button', { name: '导出' })).toBeVisible()
  await expect(page.getByRole('button', { name: '新建公司' })).toBeVisible()
  await expect(page.getByPlaceholder('名称')).toBeVisible()
  await expect(page.getByPlaceholder('信用代码')).toBeVisible()
  await expect(page.getByText('公司 ID')).toBeVisible()
  await expect(page.getByText('公众号容量')).toBeVisible()
})

test('E2E-B5-CO-02 新建公司与必填、重复', async ({ page }) => {
  await boot(page, 'xz')
  await page.goto('/ims/corp/resource/company')
  await page.getByRole('button', { name: '新建公司' }).click()
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('必填项，请填写')).toBeVisible()
  await page.getByPlaceholder('公司名称').fill('TC公司A')
  await page.getByPlaceholder('容量').fill('1')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('0 / 1')).toBeVisible()
  await page.getByRole('button', { name: '新建公司' }).click()
  await page.getByPlaceholder('公司名称').fill('TC公司B')
  await page.getByPlaceholder('容量').fill('10')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('0 / 10')).toBeVisible()
  await page.getByRole('button', { name: '新建公司' }).click()
  await page.getByPlaceholder('公司名称').fill('TC公司A')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('公司名称已存在')).toBeVisible()
  await page.getByPlaceholder('公司名称').fill('TC公司C')
  await page.getByPlaceholder('信用代码').last().fill('123')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('信用代码格式不正确')).toBeVisible()
})

test('E2E-B5-CO-03 详情与扩容', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.companies.push({
    id: '21', name: 'TC公司A', creditCode: '', mpCapacity: 1, mpRegistered: 1,
    statusCode: 'ENABLED', legalIdCard: ID_A, expansions: [],
  })
  await page.goto('/ims/corp/resource/company')
  await page.getByRole('button', { name: '详情' }).click()
  await expect(page.getByText('总量 1 / 已注册 1 / 剩余 0')).toBeVisible()
  await page.getByRole('button', { name: '扩容', exact: true }).click()
  await page.getByPlaceholder('新容量').fill('2')
  await page.getByPlaceholder('扩容原因').fill('测试扩容')
  await page.getByRole('button', { name: '确认扩容' }).click()
  await expect(page.getByText('原 1 → 新 2')).toBeVisible()
  await page.getByRole('button', { name: '扩容', exact: true }).click()
  await page.getByPlaceholder('新容量').fill('0')
  await page.getByRole('button', { name: '确认扩容' }).click()
  await expect(page.getByText('容量不能小于已注册数')).toBeVisible()
})

test('E2E-B5-CO-04 停用后不可被选', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.companies.push({
    id: '22', name: 'TC公司B', creditCode: '', mpCapacity: 10, mpRegistered: 0,
    statusCode: 'ENABLED', legalIdCard: ID_A, expansions: [],
  })
  await page.goto('/ims/corp/resource/company')
  await page.getByRole('button', { name: '停用' }).click()
  await expect(page.getByText('已关联账号不受影响')).toBeVisible()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.getByText('停用').first()).toBeVisible()
  const listed = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/corp/resource/company/simple-list')
    return response.json()
  })
  expect(listed.data.map((item: { name: string }) => item.name)).not.toContain('TC公司B')
  await page.getByRole('button', { name: '启用' }).click()
  const restored = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/corp/resource/company/simple-list')
    return response.json()
  })
  expect(restored.data.map((item: { name: string }) => item.name)).toContain('TC公司B')
})

test('E2E-B5-CO-05 容量紧张标签', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.companies.push(
    { id: '31', name: 'TC公司A', creditCode: '', mpCapacity: 2, mpRegistered: 0, statusCode: 'ENABLED', legalIdCard: ID_A, expansions: [] },
    { id: '32', name: 'TC公司B', creditCode: '', mpCapacity: 10, mpRegistered: 0, statusCode: 'ENABLED', legalIdCard: ID_A, expansions: [] },
  )
  await page.goto('/ims/corp/resource/company')
  const tight = page.locator('tr', { hasText: 'TC公司A' })
  await expect(tight.getByText('容量紧张')).toBeVisible()
  await expect(page.locator('tr', { hasText: 'TC公司B' }).getByText('容量紧张')).toHaveCount(0)
})

test('E2E-B5-CO-06 筛选与导出', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.companies.push({
    id: '41', name: 'TC公司A', creditCode: '91350100M000100Y43', mpCapacity: 1, mpRegistered: 0,
    statusCode: 'ENABLED', legalIdCard: ID_A, expansions: [],
  })
  await page.goto('/ims/corp/resource/company')
  await choose(page, '状态', '启用')
  await page.getByRole('button', { name: '查询' }).click()
  await page.getByRole('button', { name: '导出' }).click()
  await expect(page.getByTestId('export-preview')).toContainText('共 1 行')
  await expect(page.getByTestId('export-preview')).toContainText('脱敏')
  await page.getByRole('button', { name: '重置' }).click()
  await expect(page.getByPlaceholder('名称')).toHaveValue('')
})

test('E2E-B5-RN-01 新增实名人与脱敏', async ({ page }) => {
  await boot(page, 'xz')
  await page.goto('/ims/corp/resource/realname')
  await page.getByRole('button', { name: '新增实名人' }).click()
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('姓名必填')).toBeVisible()
  await expect(page.getByText('证件号必填')).toBeVisible()
  await inDrawer(page, '姓名').fill('坏证件')
  await choose(page, '证件类型', '居民身份证')
  await inDrawer(page, '证件号').fill('123456789012345678')
  await page.getByRole('dialog', { name: '新增实名人' }).getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('身份证号不合法')).toBeVisible()
  await page.getByRole('dialog', { name: '新增实名人' }).getByRole('button', { name: '关闭此对话框' }).click()
  for (const [name, card] of [['TC实名人甲', ID_A], ['TC实名人乙', ID_B]] as const) {
    await page.getByRole('button', { name: '新增实名人' }).click()
    await inDrawer(page, '姓名').fill(name)
    await choose(page, '证件类型', '居民身份证')
    await inDrawer(page, '证件号').fill(card)
    await page.getByPlaceholder('手机号').fill('13812345678')
    await page.getByRole('button', { name: '保存' }).click()
  }
  await expect(page.getByText(maskId(ID_A))).toBeVisible()
  await expect(page.getByText('138****5678').first()).toBeVisible()
})

test('E2E-B5-RN-02 证件号重复与精确查询', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '51', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  await page.goto('/ims/corp/resource/realname')
  await page.getByRole('button', { name: '新增实名人' }).click()
  await inDrawer(page, '姓名').fill('重复人')
  await choose(page, '证件类型', '护照')
  await inDrawer(page, '证件号').fill(ID_A)
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('证件号已存在')).toBeVisible()
  await page.keyboard.press('Escape')
  await page.locator('.filters').getByPlaceholder('证件号').fill(ID_A)
  await page.getByRole('button', { name: '查询' }).click()
  await expect(page.getByRole('cell', { name: 'TC实名人甲' })).toBeVisible()
})

test('E2E-B5-RN-03 中介人与佣金脱敏', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '61', name: 'TC实名人乙', idCard: ID_B, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  await page.goto('/ims/corp/resource/realname')
  await page.getByRole('button', { name: '详情' }).click()
  await page.getByPlaceholder('中介人姓名').fill('TC中介1')
  await page.getByPlaceholder('佣金').fill('5.50')
  await page.getByRole('button', { name: '添加中介人' }).click()
  await page.getByPlaceholder('中介人姓名').fill('TC中介2')
  await page.getByRole('button', { name: '添加中介人' }).click()
  await expect(page.getByText('TC中介1 等 2 人')).toBeVisible()
  await session.switchRole('ro')
  await page.goto('/ims/corp/resource/realname')
  await page.getByRole('button', { name: '详情' }).click()
  await expect(page.getByText('佣金比例 ****')).toBeVisible()
  await expect(page.getByText('5.50')).toHaveCount(0)
})

test('E2E-B5-RN-04 详情聚合', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '71', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  session.world.certs.push({
    id: 'c1', holderName: 'CERT-A', holderType: 'REALNAME', realnameId: '71', certType: 'ID_CARD',
    certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '2', daysLeft: 365, isLocked: false, external: false,
  })
  session.world.sims.push({ id: 's1', phone: '13812345678', operator: 'CMCC', realnameId: '71', monthlyRent: '128', iccid: '', statusCode: 'ENABLED' })
  await page.goto('/ims/corp/resource/realname')
  await page.getByRole('button', { name: '详情' }).click()
  await expect(page.getByText('证件索引')).toBeVisible()
  await page.getByRole('button', { name: 'CERT-A' }).click()
  await expect(page).toHaveURL(/certificate\?holder=71/)
})

test('E2E-B5-RN-05 离职后不可被选', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '81', name: 'TC实名人丙', idCard: ID_B, phone: '13900001111', statusCode: 'ON_JOB', people: [] })
  await page.goto('/ims/corp/resource/realname')
  await page.getByRole('button', { name: '离职' }).click()
  await page.goto('/ims/corp/resource/sim-card')
  await page.getByRole('button', { name: '新增手机卡' }).click()
  await openSelect(page, '请选择实名人')
  await expect(page.getByRole('option', { name: 'TC实名人丙' })).toHaveCount(0)
  const denied = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/corp/resource/sim-card', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: '13700001111', operator: 'CMCC', realnameId: '81' }),
    })
    return response.json()
  })
  expect(denied.code).toBe(1501)
})

test('E2E-B5-RN-06 被引用不可删、未引用可删', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '91', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  session.world.sims.push({ id: 's9', phone: '13812345678', operator: 'CMCC', realnameId: '91', monthlyRent: '1', iccid: '', statusCode: 'ENABLED' })
  await page.goto('/ims/corp/resource/realname')
  await page.getByRole('button', { name: '删除' }).click()
  await expect(page.getByText('关联的实体已被其他记录引用')).toBeVisible()
  await expect(page.getByText('sim:1')).toBeVisible()
  await page.getByRole('button', { name: '新增实名人' }).click()
  await inDrawer(page, '姓名').fill('TC临时实名人')
  await choose(page, '证件类型', '护照')
  await inDrawer(page, '证件号').fill('P-TEMP')
  await page.getByRole('button', { name: '保存' }).click()
  await page.locator('tr', { hasText: 'TC临时实名人' }).getByRole('button', { name: '删除' }).click()
  await expect(page.getByText('TC临时实名人')).toHaveCount(0)
})

test('E2E-B5-RN-07 导出脱敏', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '92', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  await page.goto('/ims/corp/resource/realname')
  await choose(page, '状态', '在职')
  await page.getByRole('button', { name: '查询' }).click()
  await page.getByRole('button', { name: '导出' }).click()
  await expect(page.getByTestId('rn-export')).toContainText('无佣金列')
  await expect(page.getByText(maskId(ID_A))).toBeVisible()
  await expect(page.getByText(ID_A)).toHaveCount(0)
})

test('E2E-B5-SM-01 新增手机卡', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '101', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  await page.goto('/ims/corp/resource/sim-card')
  await page.getByRole('button', { name: '新增手机卡' }).click()
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('号码必填')).toBeVisible()
  await expect(page.getByText('实名人必填')).toBeVisible()
  await expect(page.locator('.realname-select input')).toHaveJSProperty('readOnly', true)
  await inDrawer(page, '号码').fill('13800001111')
  await choose(page, '运营商', '移动')
  await choose(page, '请选择实名人', 'TC实名人甲')
  await page.getByPlaceholder('月租').fill('128')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('138****1111')).toBeVisible()
  await expect(page.getByText('¥128.00')).toBeVisible()
})

test('E2E-B5-SM-02 号码 / ICCID 重复', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '111', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  session.world.sims.push({ id: '1111', phone: '13800001111', operator: 'CMCC', realnameId: '111', monthlyRent: '1', iccid: 'ICCID-A', statusCode: 'ENABLED' })
  await page.goto('/ims/corp/resource/sim-card')
  await page.getByRole('button', { name: '新增手机卡' }).click()
  await inDrawer(page, '号码').fill('13800001111')
  await choose(page, '运营商', '移动')
  await choose(page, '请选择实名人', 'TC实名人甲')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('手机号已存在')).toBeVisible()
  await page.keyboard.press('Escape')
  await page.keyboard.press('Escape')
  session.world.sims.push({ id: '1112', phone: '13900002222', operator: 'CUCC', realnameId: '111', monthlyRent: '2', iccid: '', statusCode: 'ENABLED' })
  await page.reload()
  await page.locator('tr', { hasText: '139****2222' }).getByRole('button', { name: '编辑' }).click()
  await page.getByPlaceholder('ICCID').fill('ICCID-A')
  await page.getByRole('button', { name: '保存' }).click()
  await expect(page.getByText('ICCID已存在')).toBeVisible()
})

test('E2E-B5-SM-03 详情与编辑只读号码', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '121', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  session.world.sims.push({ id: '1211', phone: '13800001111', operator: 'CMCC', realnameId: '121', monthlyRent: '128', iccid: 'X', statusCode: 'ENABLED' })
  await page.goto('/ims/corp/resource/sim-card')
  await page.getByRole('button', { name: '详情' }).click()
  await expect(page.getByText('实名人 TC实名人甲')).toBeVisible()
  await expect(page.getByText('关联平台账号空状态')).toBeVisible()
  await page.keyboard.press('Escape')
  await page.getByRole('button', { name: '编辑' }).click()
  await expect(inDrawer(page, '号码')).toBeDisabled()
  await expect(inDrawer(page, '号码')).toHaveValue('138****1111')
})

test('E2E-B5-SM-04 删除与筛选', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '131', name: '甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  session.world.sims.push(
    { id: '1', phone: '13800001111', operator: 'CMCC', realnameId: '131', monthlyRent: '1', iccid: '', statusCode: 'ENABLED' },
    { id: '2', phone: '13900002222', operator: 'CUCC', realnameId: '131', monthlyRent: '59', iccid: '', statusCode: 'ENABLED' },
  )
  await page.goto('/ims/corp/resource/sim-card')
  await page.locator('tr', { hasText: '138****1111' }).getByRole('button', { name: '删除' }).click()
  await expect(page.getByText('138****1111')).toHaveCount(0)
  await choose(page, '运营商', '联通')
  await page.getByRole('button', { name: '查询' }).click()
  await expect(page.getByText('139****2222')).toBeVisible()
  await expect(page.locator('.el-table').getByText('移动')).toHaveCount(0)
})

test('E2E-B5-SM-05 导出', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.sims.push({ id: '1', phone: '13800001111', operator: 'CMCC', realnameId: '1', monthlyRent: '1', iccid: 'SECRET', statusCode: 'ENABLED' })
  await page.goto('/ims/corp/resource/sim-card')
  await page.getByRole('button', { name: '导出' }).click()
  await expect(page.getByTestId('sm-export')).toContainText('共 1 行')
  await expect(page.getByText('SECRET')).toHaveCount(0)
  await expect(page.getByText('138****1111')).toBeVisible()
})

test('E2E-B5-CT-01 上传必填与格式', async ({ page }) => {
  await boot(page, 'xz')
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '上传证件' }).click()
  await page.getByRole('button', { name: '提交' }).click()
  await expect(page.getByText('扫描件必填')).toBeVisible()
  await page.getByText('外协', { exact: true }).click()
  await page.getByPlaceholder('外协姓名').fill('外协')
  await choose(page, '证件类型', '居民身份证')
  await inDrawer(page, '证件号').fill('123')
  await page.getByPlaceholder('签发日期').fill('2020-01-01')
  await page.getByPlaceholder('有效期至').fill('2030-01-01')
  await page.getByLabel('扫描件').setInputFiles({ name: 'a.png', mimeType: 'image/png', buffer: Buffer.from('png') })
  await page.getByRole('button', { name: '提交' }).click()
  await expect(page.getByText('身份证号不合法')).toBeVisible()
  await inDrawer(page, '证件号').fill(ID_A)
  await page.getByPlaceholder('有效期至').fill('2019-01-01')
  await page.getByRole('button', { name: '提交' }).click()
  await expect(page.getByText('有效期须晚于签发日期')).toBeVisible()
})

test('E2E-B5-CT-02 上传有效证件（持有人选实名人）', async ({ page }) => {
  await boot(page, 'xz')
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '上传证件' }).click()
  await expect(page.getByText('实名人', { exact: true })).toBeVisible()
  await expect(page.getByText('员工')).toBeVisible()
  await expect(page.getByText('外协')).toBeVisible()
  await page.getByText('外协', { exact: true }).click()
  await page.getByPlaceholder('外协姓名').fill('TC外协')
  await choose(page, '证件类型', '护照')
  await inDrawer(page, '证件号').fill('P100')
  await page.getByPlaceholder('签发日期').fill('2020-01-01')
  await page.getByPlaceholder('有效期至').fill('2030-01-01')
  await page.getByLabel('扫描件').setInputFiles({ name: 'a.png', mimeType: 'image/png', buffer: Buffer.from('png') })
  await page.getByRole('button', { name: '提交' }).click()
  await expect(page.getByText('待审')).toBeVisible()
  await expect(page.getByText('外协').last()).toBeVisible()
})

test('E2E-B5-CT-03 一人一类型一份', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '71', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  session.world.certs.push({
    id: 'c71', holderName: 'TC实名人甲', holderType: 'REALNAME', realnameId: '71', certType: 'ID_CARD',
    certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '3', daysLeft: 10, isLocked: false, external: false,
  })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '上传证件' }).click()
  await choose(page, '请选择实名人', 'TC实名人甲')
  await choose(page, '证件类型', '居民身份证')
  await inDrawer(page, '证件号').fill(ID_A)
  await page.getByPlaceholder('签发日期').fill('2020-01-01')
  await page.getByPlaceholder('有效期至').fill('2031-01-01')
  await page.getByLabel('扫描件').setInputFiles({ name: 'a.png', mimeType: 'image/png', buffer: Buffer.from('png') })
  await page.getByRole('button', { name: '提交' }).click()
  await expect(page.getByText('已存在有效档案，如为新证请走换证流程')).toBeVisible()
  await page.getByRole('button', { name: '去换证' }).click()
  await expect(page.getByText('到期预警')).toBeVisible()
})

test('E2E-B5-CT-04 审核与回避', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.certs.push({
    id: 'own', holderName: '自己的证', holderType: 'EXTERNAL', realnameId: '', certType: 'PASSPORT',
    certNo: 'P1', status: 'PENDING_REVIEW', warnLevel: '', creatorId: '2', daysLeft: 5, isLocked: false, external: true,
  })
  await page.goto('/ims/corp/resource/certificate')
  await expect(page.locator('tr', { hasText: '自己的证' }).getByRole('button', { name: '审核' })).toHaveCount(0)
  const denied = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/cert/archive/own/review', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ passed: true, remark: '' }),
    })
    return response.json()
  })
  expect(denied.code).toBe(1008)
  await session.switchRole('xz2')
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '审核' }).click()
  await expect(page.getByText('生效')).toBeVisible()
  await expect(page.getByText('剩余 5 天')).toBeVisible()
})

test('E2E-B5-CT-05 L1 默认只见索引', async ({ page }) => {
  const session = await boot(page, 'ro')
  session.world.certs.push({
    id: 'a', holderName: 'CERT-A', holderType: 'REALNAME', realnameId: '1', certType: 'ID_CARD',
    certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '2', daysLeft: 30, isLocked: false, external: false,
  })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '查看原图' }).click()
  await expect(page.getByText('访问级别不足')).toBeVisible()
  await expect(page.getByTestId('cert-preview')).toHaveCount(0)
  await expect(page.getByRole('tab', { name: '分级与审计' })).toHaveCount(0)
})

test('E2E-B5-CT-06 L2 水印查看、禁下载', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.certs.push({
    id: 'a', holderName: 'CERT-A', holderType: 'REALNAME', realnameId: '1', certType: 'ID_CARD',
    certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '3', daysLeft: 30, isLocked: false, external: false,
  })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '查看原图' }).click()
  const layer = page.getByTestId('cert-preview')
  await expect(layer).toContainText('test_xz')
  await expect(layer).toContainText(maskId(ID_A))
  await expect(layer.getByRole('button', { name: '下载' })).toHaveCount(0)
  const image = layer.locator('img')
  await expect(image).toHaveAttribute('draggable', 'false')
})

test('E2E-B5-CT-07 L3 明文', async ({ page }) => {
  const session = await boot(page, 'admin')
  session.world.certs.push({
    id: 'a', holderName: 'CERT-A', holderType: 'REALNAME', realnameId: '1', certType: 'ID_CARD',
    certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '2', daysLeft: 30, isLocked: false, external: false,
  })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '查看原图' }).click()
  await expect(page.getByTestId('cert-preview')).toContainText(ID_A)
  await expect(page.getByTestId('cert-preview').getByRole('button', { name: '下载' })).toHaveCount(0)
})

test('E2E-B5-CT-08 高频访问拦截', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.views = 10
  session.world.certs.push({
    id: 'a', holderName: 'CERT-A', holderType: 'REALNAME', realnameId: '1', certType: 'ID_CARD',
    certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '3', daysLeft: 30, isLocked: false, external: false,
  })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '查看原图' }).click()
  await expect(page.getByText('查看次数过多')).toBeVisible()
  await session.switchRole('admin')
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '分级与审计' }).click()
  await expect(page.getByText('test_xz', { exact: true })).toBeVisible()
})

test('E2E-B5-CT-09 只看本人证件与数字化率', async ({ page }) => {
  const session = await boot(page, 'self')
  session.world.certs.push(
    { id: 's', holderName: 'CERT-S 自', holderType: 'REALNAME', realnameId: '5', certType: 'ID_CARD', certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '2', daysLeft: 1, isLocked: false, external: false },
    { id: 'o', holderName: 'CERT-A', holderType: 'REALNAME', realnameId: '1', certType: 'ID_CARD', certNo: ID_B, status: 'EFFECTIVE', warnLevel: '', creatorId: '2', daysLeft: 1, isLocked: false, external: false },
  )
  await page.goto('/ims/corp/resource/certificate')
  await expect(page.getByText('CERT-S 自')).toBeVisible()
  await expect(page.getByText('CERT-A')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '上传证件' })).toHaveCount(0)
  await expect(page.getByRole('tab', { name: '到期预警' })).toHaveCount(0)
  await session.switchRole('xz')
  session.world.people.push({ id: '1', name: '甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  await page.goto('/ims/corp/resource/certificate')
  await expect(page.getByTestId('digital-rate')).toBeVisible()
  await expect(page.getByRole('button', { name: '查看统计' })).toBeVisible()
})

test('E2E-B5-CT-10 OCR 识别预填（mock）', async ({ page }) => {
  const session = await boot(page, 'xz')
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '上传证件' }).click()
  await page.getByLabel('扫描件').setInputFiles({ name: 'id.png', mimeType: 'image/png', buffer: Buffer.from('png') })
  await page.getByRole('button', { name: '识别' }).click()
  await expect(page.getByText('识别结果，请核对')).toBeVisible()
  await expect(inDrawer(page, '证件号')).toHaveValue(ID_A)
  session.world.ocr = false
  await page.getByRole('button', { name: '识别' }).click()
  await expect(page.getByText('识别失败，请手工填写')).toBeVisible()
})

test('E2E-B5-CT-11 证件删除与锁定拦截', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.certs.push(
    { id: 'x', holderName: 'CERT-X', holderType: 'EXTERNAL', realnameId: '', certType: 'PASSPORT', certNo: 'P9', status: 'EFFECTIVE', warnLevel: '', creatorId: '1', daysLeft: 1, isLocked: false, external: true },
    { id: 'l', holderName: 'CERT-L', holderType: 'EXTERNAL', realnameId: '', certType: 'PASSPORT', certNo: 'P8', status: 'EFFECTIVE', warnLevel: '', creatorId: '1', daysLeft: 1, isLocked: true, external: true },
  )
  await page.goto('/ims/corp/resource/certificate')
  await expect(page.getByRole('button', { name: '删除' })).toHaveCount(0)
  const denied = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/cert/archive/x', { method: 'DELETE' })
    return response.json()
  })
  expect(denied.code).toBe(1008)
  await session.switchRole('admin')
  await page.goto('/ims/corp/resource/certificate')
  await page.locator('tr', { hasText: 'CERT-L' }).getByRole('button', { name: '删除' }).click()
  await expect(page.getByText('证件已锁定，不可删除')).toBeVisible()
  await page.locator('tr', { hasText: 'CERT-X' }).getByRole('button', { name: '删除' }).click()
  await expect(page.getByText('CERT-X')).toHaveCount(0)
})

test('E2E-B5-EX-01 每日扫描分级与待办', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.tasks.push(
    { id: 't1', certName: 'CERT-D', level: 'YELLOW', status: '预警', remindCount: 0 },
    { id: 't2', certName: 'CERT-B', level: 'RED', status: '预警', remindCount: 0 },
    { id: 't3', certName: 'CERT-C', level: 'LOCKED', status: '已过期', remindCount: 0 },
  )
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '到期预警' }).click()
  await expect(page.getByTestId('expire-stats')).toContainText('黄 1')
  await expect(page.getByTestId('expire-stats')).toContainText('红 1')
  await expect(page.getByTestId('expire-stats')).toContainText('锁定 1')
})

test('E2E-B5-EX-02 同级别不重复推、升级再推', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.tasks.push({ id: 't1', certName: 'CERT-D', level: 'YELLOW', status: '预警', remindCount: 0 })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '到期预警' }).click()
  await page.getByRole('button', { name: '手动扫描' }).click()
  await page.getByRole('button', { name: '确定' }).click()
  await expect(page.getByText('CERT-D')).toBeVisible()
})

test('E2E-B5-EX-03 换证恢复', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.certs.push({
    id: 'old', holderName: 'CERT-C', holderType: 'REALNAME', realnameId: '9', certType: 'ID_CARD',
    certNo: ID_A, status: 'EXPIRED', warnLevel: 'LOCKED', creatorId: '2', daysLeft: -1, isLocked: false, external: false,
  })
  session.world.people.push({ id: '9', name: 'TC实名人丙', idCard: ID_B, phone: '13900001111', statusCode: 'ON_JOB', people: [] })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '到期预警' }).click()
  await expect(page.getByRole('button', { name: '换证' })).toHaveCount(0)
  await page.getByRole('tab', { name: '档案' }).click()
  await expect(page.getByText('已过期-锁定')).toBeVisible()
})

test('E2E-B5-EX-04 人工催办', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.tasks.push({ id: 't9', certName: 'CERT-B', level: 'RED', status: '预警', remindCount: 0 })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '到期预警' }).click()
  await page.getByRole('button', { name: '催办' }).click()
  await expect(page.getByText('已催办 1')).toBeVisible()
  await page.getByRole('button', { name: '催办' }).click()
  await expect(page.getByText('10 分钟内不再发消息')).toBeVisible()
})

test('E2E-B5-EX-05 无预警权限', async ({ page }) => {
  await boot(page, 'self')
  await page.goto('/ims/corp/resource/certificate')
  await expect(page.getByRole('tab', { name: '到期预警' })).toHaveCount(0)
  await expect(page.getByRole('tab', { name: '分级与审计' })).toHaveCount(0)
  const denied = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/cert/expire/list')
    return response.json()
  })
  expect(denied.code).toBe(1008)
})

test('E2E-B5-SC-01 配置 L2 立即生效', async ({ page }) => {
  const session = await boot(page, 'admin')
  session.world.certs.push({
    id: 'a', holderName: 'CERT-A', holderType: 'REALNAME', realnameId: '1', certType: 'ID_CARD',
    certNo: ID_A, status: 'EFFECTIVE', warnLevel: '', creatorId: '2', daysLeft: 9, isLocked: false, external: false,
  })
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '分级与审计' }).click()
  await page.getByRole('button', { name: '保存级别' }).click()
  await expect(page.getByText('下次查看即按新级别')).toBeVisible()
  await session.switchRole('ro')
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('button', { name: '查看原图' }).click()
  await expect(page.getByTestId('cert-preview')).toBeVisible()
})

test('E2E-B5-SC-02 审计日志', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.logs.push(
    { viewerName: 'test_ro', result: '拒绝' },
    { viewerName: 'test_ro', result: '成功' },
  )
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '分级与审计' }).click()
  await page.getByPlaceholder('查看人').fill('test_ro')
  await page.getByRole('button', { name: '筛选' }).click()
  await expect(page.getByText('拒绝')).toBeVisible()
  await expect(page.getByText('成功')).toBeVisible()
  await expect(page.getByText('—').first()).toBeVisible()
})

test('E2E-B5-SC-03 非 R1 不能配置', async ({ page }) => {
  await boot(page, 'xz')
  await page.goto('/ims/corp/resource/certificate')
  await page.getByRole('tab', { name: '分级与审计' }).click()
  await expect(page.getByTestId('level-config')).toHaveCount(0)
  await expect(page.getByPlaceholder('查看人')).toBeVisible()
  const denied = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/cert/security/level-config', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: '{}',
    })
    return response.json()
  })
  expect(denied.code).toBe(1008)
})

test('E2E-B5-BG-01 无菜单权限', async ({ page }) => {
  await boot(page, 'yg')
  await page.goto('/ims/corp/resource/company')
  if ((page.viewportSize()?.width || 1440) < 768) await page.locator('.menu-btn').click()
  await expect(page.locator('.sidebar').getByText('公司资产')).toHaveCount(0)
  await expect(page.getByTestId('denied-panel')).toBeVisible()
  const denied = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/corp/resource/company/page')
    return response.json()
  })
  expect(denied.code).toBe(1008)
})

test('E2E-B5-BG-02 只读账号无写按钮', async ({ page }) => {
  await boot(page, 'ro')
  for (const path of [
    '/ims/corp/resource/company',
    '/ims/corp/resource/realname',
    '/ims/corp/resource/sim-card',
    '/ims/corp/resource/certificate',
  ]) {
    await page.goto(path)
    await expect(page.getByRole('button', { name: '新建公司' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '新增实名人' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '上传证件' })).toHaveCount(0)
    await expect(page.getByRole('button', { name: '删除' })).toHaveCount(0)
  }
  const denied = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/corp/resource/company', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    })
    return response.json()
  })
  expect(denied.code).toBe(1008)
})

test('E2E-B5-BG-03 跨租户与不存在 1504', async ({ page }) => {
  await boot(page, 'xz')
  await page.goto('/ims/corp/resource/company')
  const missing = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/cert/archive/missing-id')
    return response.json()
  })
  expect(missing.code).toBe(1504)
  expect(JSON.stringify(missing)).not.toContain('TC公司A')
  const task = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/cert/expire/missing/remind', { method: 'PUT' })
    return response.json()
  })
  expect(task.code).toBe(1504)
})

test('E2E-B5-BG-04 须改密阶段 1008', async ({ page }) => {
  await boot(page, 'reset')
  await page.goto('/ims/corp/resource/company')
  await expect(page).toHaveURL(/password-reset/)
  const company = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/corp/resource/company/simple-list')
    return response.json()
  })
  const certs = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/cert/archive/list')
    return response.json()
  })
  const me = await page.evaluate(async () => {
    const response = await fetch('/admin-api/ims/auth/me')
    return response.json()
  })
  expect(company.code).toBe(1008)
  expect(certs.code).toBe(1008)
  expect(me.code).toBe(0)
})

test('E2E-B5-BG-05 库内加密核对', async ({ page }) => {
  const session = await boot(page, 'xz')
  session.world.people.push({ id: '1', name: 'TC实名人甲', idCard: ID_A, phone: '13812345678', statusCode: 'ON_JOB', people: [] })
  session.world.companies.push({
    id: '1', name: 'TC公司A', creditCode: '', mpCapacity: 1, mpRegistered: 0,
    statusCode: 'ENABLED', legalIdCard: ID_A, expansions: [],
  })
  await page.goto('/ims/corp/resource/realname')
  await expect(page.getByText(ID_A)).toHaveCount(0)
  await expect(page.getByText(maskId(ID_A))).toBeVisible()
  const stored = session.world.people[0]
  expect(stored.idCard).not.toBe(maskId(stored.idCard))
  expect(stored.phone).not.toContain('****')
})

/**
 * 对照 crCompany / crRealname / crSim / crCert 的页头、筛选、表头和 390 侧栏。
 * 公司表多一列「信用代码」、筛选用「名称」而不是「公司名称」，以 02 的 E2E-B5-CO-01 为准。
 * 实名人多一列「手机号」，同样以 02 的脱敏列表为准。证件三个 Tab 来自工作包，不在静态快照里。
 */
test('E2E-B5-PROTO 四页结构文案与响应式', async ({ page }) => {
  await boot(page, 'xz')
  const width = page.viewportSize()?.width || 1440
  const mobile = width < 768
  const pages: Array<{
    path: string
    title: string
    buttons: string[]
    headers: string[]
    placeholders: string[]
    tabs?: string[]
  }> = [
    {
      path: '/ims/corp/resource/company',
      title: '公司管理',
      buttons: ['导出', '新建公司', '查询', '重置'],
      headers: ['公司 ID', '名称', '信用代码', '公众号容量', '状态', '操作'],
      placeholders: ['名称', '信用代码'],
    },
    {
      path: '/ims/corp/resource/realname',
      title: '实名人管理',
      buttons: ['导出', '新增实名人', '查询', '重置'],
      headers: ['实名人 ID', '姓名', '证件号', '手机号', '中介人', '状态', '操作'],
      placeholders: ['姓名', '证件号'],
    },
    {
      path: '/ims/corp/resource/sim-card',
      title: '手机卡管理',
      buttons: ['导出', '新增手机卡', '查询', '重置'],
      headers: ['卡 ID', '号码', '运营商', '实名人', '月租', '操作'],
      placeholders: ['号码', '实名人'],
    },
    {
      path: '/ims/corp/resource/certificate',
      title: '证件管理',
      buttons: ['上传证件', '查询', '重置'],
      headers: ['持有人', '类型', '证件号', '有效期至', '状态', '操作'],
      placeholders: ['持有人'],
      tabs: ['档案', '到期预警', '分级与审计'],
    },
  ]
  for (const spec of pages) {
    await page.goto(spec.path)
    const title = page.getByRole('heading', { level: 1, name: spec.title })
    await expect(title).toBeVisible()
    for (const name of spec.buttons) {
      await expect(page.getByRole('button', { name, exact: true }).first()).toBeVisible()
    }
    for (const placeholder of spec.placeholders) {
      await expect(page.locator('.filters').getByPlaceholder(placeholder)).toBeVisible()
    }
    for (const tab of spec.tabs || []) {
      await expect(page.getByRole('tab', { name: tab })).toBeVisible()
    }
    const cells = page.locator('.el-table:visible').first().locator('.el-table__header-wrapper th .cell')
    const count = await cells.count()
    const labels: string[] = []
    for (let index = 0; index < count; index += 1) {
      const text = (await cells.nth(index).innerText()).replace(/\s+/g, ' ').trim()
      if (text) labels.push(text)
    }
    expect(labels).toEqual(spec.headers)
    const titleBox = await title.boundingBox()
    expect(titleBox).not.toBeNull()
    expect(titleBox!.x).toBeGreaterThanOrEqual(0)
    expect(titleBox!.x + titleBox!.width).toBeLessThanOrEqual(width + 1)
    const sidebar = page.locator('[data-testid="app-sidebar"]')
    if (mobile) {
      await expect(sidebar).toHaveClass(/mobile-hidden/)
      await expect(page.locator('.menu-btn')).toBeVisible()
    } else {
      await expect(sidebar).not.toHaveClass(/mobile-hidden/)
      const side = await sidebar.boundingBox()
      expect(side).not.toBeNull()
      expect(titleBox!.x).toBeGreaterThanOrEqual(side!.x + side!.width - 1)
    }
    const fits = await page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1,
    )
    expect(fits).toBe(true)
  }
})
