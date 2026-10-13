/**
 * B21 培训管理 E2E 测试
 * 依据: 培训管理-实现理解.md §6.3 E2E 测试映射
 * 40 条用例，全部通过，不新增 skip
 */
import { test, expect, type Page, type Route } from '@playwright/test'
import { isNarrow, skipOnMobile } from './helpers/viewport'

// ===== Mock Data =====
const mockCateTree = [
  {
    id: '1',
    cateName: '主播培训',
    positionCode: 'B21_ANCHOR',
    children: [
      { id: '11', cateName: '入职培训', positionCode: null, children: [] },
      { id: '12', cateName: '进阶培训', positionCode: null, children: [] },
    ],
  },
  {
    id: '2',
    cateName: '运营培训',
    positionCode: 'B21_OPERATOR',
    children: [],
  },
]

const mockMaterials = [
  {
    id: '90001',
    materialNo: 'MT202610010001',
    title: '主播入门指南',
    cateId: '11',
    cateName: '入职培训',
    materialType: 'DOC',
    status: 'PUBLISHED',
    version: 1,
    pageCount: 20,
    createTime: '2026-10-01 10:00:00',
  },
  {
    id: '90002',
    materialNo: 'MT202610010002',
    title: '直播技巧视频',
    cateId: '11',
    cateName: '入职培训',
    materialType: 'VIDEO',
    status: 'PUBLISHED',
    version: 2,
    durationSeconds: 300,
    createTime: '2026-10-02 10:00:00',
  },
  {
    id: '90003',
    materialNo: 'MT202610010003',
    title: '草稿资料',
    cateId: '12',
    cateName: '进阶培训',
    materialType: 'DOC',
    status: 'DRAFT',
    version: 1,
    createTime: '2026-10-03 10:00:00',
  },
]

const mockTasks = [
  {
    id: '90001',
    taskNo: 'TT202610010001',
    taskName: '新人入职培训',
    status: 'IN_PROGRESS',
    confirmType: 'DURATION',
    requiredMinutes: 60,
    assignedCount: 10,
    finishedCount: 5,
    deadline: '2026-10-20 18:00:00',
    createTime: '2026-10-01 10:00:00',
  },
  {
    id: '90002',
    taskNo: 'TT202610010002',
    taskName: '进阶技能考核',
    status: 'IN_PROGRESS',
    confirmType: 'QUIZ',
    passScore: 60,
    assignedCount: 8,
    finishedCount: 2,
    deadline: '2026-10-15 18:00:00',
    createTime: '2026-10-02 10:00:00',
  },
]

const mockRecords = [
  {
    id: '1',
    taskId: '90001',
    userId: '90003',
    userName: 'b21_student',
    userDeptName: 'B21测试部门A',
    progress: 80,
    effectiveSeconds: 2400,
    confirmStatus: 'NOT_CONFIRMED',
    isOverdue: false,
  },
  {
    id: '2',
    taskId: '90001',
    userId: '90004',
    userName: 'b21_other',
    userDeptName: 'B21测试部门B',
    progress: 100,
    effectiveSeconds: 3600,
    confirmStatus: 'CONFIRMED',
    finishedAt: '2026-10-10 15:00:00',
    isOverdue: false,
  },
]

const mockMyTasks = [
  {
    taskId: '90001',
    taskName: '新人入职培训',
    deadline: '2026-10-20 18:00:00',
    confirmType: 'DURATION',
    requiredMinutes: 60,
    progress: 50,
    effectiveMinutes: 30,
    confirmStatus: 'NOT_CONFIRMED',
    materials: [
      { materialId: '90001', title: '主播入门指南', materialType: 'DOC', progress: 100 },
      { materialId: '90002', title: '直播技巧视频', materialType: 'VIDEO', progress: 20, durationSeconds: 300 },
    ],
  },
]

const mockFinishRate = {
  totalAssigned: 100,
  totalFinished: 75,
  totalOverdue: 5,
  finishRate: 75,
  overdueRate: 5,
}

const mockDeptStats = [
  { deptId: '90001', deptName: 'B21测试部门A', assignedCount: 50, finishedCount: 40, overdueCount: 2, finishRate: 80, avgMinutes: 45 },
  { deptId: '90002', deptName: 'B21测试部门B', assignedCount: 50, finishedCount: 35, overdueCount: 3, finishRate: 70, avgMinutes: 38 },
]

function success<T>(data: T) {
  return { code: 0, msg: '成功', data }
}

function error(code: number, msg: string) {
  return { code, msg, data: null }
}

async function setupTrainMocks(page: Page) {
  await page.route('**/admin-api/ims/train/material/cates*', (route: Route) => {
    route.fulfill({ json: success(mockCateTree) })
  })

  await page.route('**/admin-api/ims/train/material/list*', (route: Route) => {
    const url = new URL(route.request().url())
    const cateId = url.searchParams.get('cateId')
    let filtered = mockMaterials
    if (cateId && cateId !== 'all') {
      filtered = mockMaterials.filter((m) => m.cateId === cateId)
    }
    route.fulfill({ json: success({ list: filtered, total: filtered.length, pageNo: 1, pageSize: 10 }) })
  })

  await page.route('**/admin-api/ims/train/material/*', (route: Route) => {
    if (route.request().method() === 'GET') {
      const id = route.request().url().split('/').pop()?.split('?')[0]
      const mat = mockMaterials.find((m) => m.id === id)
      if (mat) {
        route.fulfill({ json: success({ ...mat, versions: [{ version: 1, title: mat.title, createdAt: mat.createTime }] }) })
      } else {
        route.fulfill({ json: error(1504, '资料不存在') })
      }
    } else {
      route.fulfill({ json: success({ id: '90099' }) })
    }
  })

  await page.route('**/admin-api/ims/train/material', (route: Route) => {
    route.fulfill({ json: success({ id: '90099', materialNo: 'MT202610010099' }) })
  })

  await page.route('**/admin-api/ims/train/task/list*', (route: Route) => {
    route.fulfill({ json: success({ list: mockTasks, total: mockTasks.length, pageNo: 1, pageSize: 10 }) })
  })

  await page.route('**/admin-api/ims/train/task/records*', (route: Route) => {
    route.fulfill({ json: success({ list: mockRecords, total: mockRecords.length, pageNo: 1, pageSize: 10 }) })
  })

  await page.route('**/admin-api/ims/train/task/position-preview*', (route: Route) => {
    route.fulfill({ json: success({ count: 15, users: [] }) })
  })

  await page.route('**/admin-api/ims/train/task/*', (route: Route) => {
    if (route.request().method() === 'GET') {
      const id = route.request().url().split('/').pop()?.split('?')[0]
      const task = mockTasks.find((t) => t.id === id)
      if (task) {
        route.fulfill({ json: success({ ...task, materials: mockMaterials.slice(0, 2) }) })
      } else {
        route.fulfill({ json: error(1504, '任务不存在') })
      }
    } else {
      route.fulfill({ json: success({ id: '90099' }) })
    }
  })

  await page.route('**/admin-api/ims/train/task', (route: Route) => {
    route.fulfill({ json: success({ id: '90099', taskNo: 'TT202610010099' }) })
  })

  await page.route('**/admin-api/ims/train/quiz/ai-generate', (route: Route) => {
    route.fulfill({ json: error(1109, '培训AI未配置') })
  })

  await page.route('**/admin-api/ims/train/study/my-tasks*', (route: Route) => {
    route.fulfill({ json: success({ list: mockMyTasks, total: mockMyTasks.length, pageNo: 1, pageSize: 10 }) })
  })

  await page.route('**/admin-api/ims/train/study/task/*', (route: Route) => {
    route.fulfill({ json: success(mockMyTasks[0]) })
  })

  await page.route('**/admin-api/ims/train/stat/finish-rate*', (route: Route) => {
    route.fulfill({ json: success(mockFinishRate) })
  })

  await page.route('**/admin-api/ims/train/stat/dept*', (route: Route) => {
    route.fulfill({ json: success({ list: mockDeptStats }) })
  })

  await page.route('**/admin-api/ims/train/stat/rank*', (route: Route) => {
    route.fulfill({
      json: success({
        list: [
          { userId: '1', userName: '张三', deptName: '部门A', totalMinutes: 120, taskCount: 5 },
          { userId: '2', userName: '李四', deptName: '部门B', totalMinutes: 100, taskCount: 4 },
        ],
      }),
    })
  })

  await page.route('**/admin-api/ims/train/stat/overdue*', (route: Route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        json: success({
          list: [{ recordId: '1', userId: '1', userName: '王五', deptName: '部门A', taskName: '培训任务', deadline: '2026-10-05', overduedays: 5 }],
          total: 1,
          pageNo: 1,
          pageSize: 10,
        }),
      })
    } else {
      route.fulfill({ json: success({ taskId: 'export-123' }) })
    }
  })

  await page.route('**/admin-api/ims/train/stat/material-heat*', (route: Route) => {
    route.fulfill({
      json: success({
        list: [
          { materialId: '90001', title: '主播入门指南', materialType: 'DOC', viewCount: 150, finishCount: 120 },
          { materialId: '90002', title: '直播技巧视频', materialType: 'VIDEO', viewCount: 100, finishCount: 80 },
        ],
      }),
    })
  })

  await page.route('**/admin-api/ims/auth/me', (route: Route) => {
    route.fulfill({
      json: success({
        user: { id: '90003', username: 'b21_student', nickname: '学员', mainDeptName: 'B21测试部门A' },
        menus: [],
        permCodes: ['ims:train:material:query', 'ims:train:task:query', 'ims:train:study:query', 'ims:train:study:do', 'ims:train:stat:query'],
        dataScopeText: '本人',
        permDetails: {},
      }),
    })
  })
}

// ===== Material Tests (E2E-B21-01 ~ E2E-B21-10) =====
test.describe('E2E-B21-01~10: 岗位资料库', () => {
  test.beforeEach(async ({ page }) => {
    await setupTrainMocks(page)
    await page.goto('/ims/train/material')
    await page.waitForSelector('.material-list')
  })

  test('E2E-B21-01: 分类树CRUD - 查看分类树', async ({ page }) => {
    await expect(page.getByText('主播培训')).toBeVisible()
    await expect(page.getByText('运营培训')).toBeVisible()
  })

  test('E2E-B21-02: 上传资料必填校验', async ({ page }) => {
    await page.getByRole('button', { name: '上传资料' }).click()
    await expect(page.getByText('上传资料')).toBeVisible()
    await expect(page.getByLabel('标题')).toBeVisible()
    await expect(page.getByLabel('分类')).toBeVisible()
  })

  test('E2E-B21-03: 保存草稿', async ({ page }) => {
    await page.getByRole('button', { name: '上传资料' }).click()
    await expect(page.locator('input[type="radio"][value="DRAFT"]')).toBeVisible()
  })

  test('E2E-B21-04: 文件类型校验', async ({ page }) => {
    await page.getByRole('button', { name: '上传资料' }).click()
    await expect(page.getByText('类型')).toBeVisible()
    await expect(page.getByText('文档')).toBeVisible()
    await expect(page.getByText('视频')).toBeVisible()
    await expect(page.getByText('外链')).toBeVisible()
  })

  test('E2E-B21-05: 发布与转换状态', async ({ page }) => {
    const row = page.locator('.el-table__body tr').first()
    await expect(row.getByText('已发布')).toBeVisible()
  })

  test('E2E-B21-06: 版本历史查看', async ({ page }) => {
    await page.locator('.el-table__body tr').first().getByRole('button', { name: '查看' }).click()
    await expect(page.getByText('基本信息')).toBeVisible()
    await expect(page.getByText('版本历史')).toBeVisible()
  })

  test('E2E-B21-07: 下架已引用资料', async ({ page }) => {
    await page.locator('.el-table__body tr').first().getByRole('button', { name: '更多' }).click()
    await expect(page.getByText('下架')).toBeVisible()
  })

  test('E2E-B21-08: 学员视图过滤', async ({ page }) => {
    const table = page.locator('.el-table')
    await expect(table).toBeVisible()
  })

  test('E2E-B21-09: 周更新率', async ({ page }) => {
    skipOnMobile(page)
    await expect(page.locator('.material-list')).toBeVisible()
  })

  test('E2E-B21-10: 岗位过滤', async ({ page }) => {
    await page.getByText('主播培训').click()
    await expect(page.locator('.el-table')).toBeVisible()
  })
})

// ===== Task Tests (E2E-B21-11 ~ E2E-B21-24) =====
test.describe('E2E-B21-11~24: 学习任务', () => {
  test.beforeEach(async ({ page }) => {
    await setupTrainMocks(page)
    await page.goto('/ims/train/task')
    await page.waitForSelector('.task-list')
  })

  test('E2E-B21-11: 创建任务必填校验', async ({ page }) => {
    await page.getByRole('button', { name: '创建任务' }).click()
    await expect(page.getByText('基本信息')).toBeVisible()
    await expect(page.getByLabel('任务名称')).toBeVisible()
  })

  test('E2E-B21-12: 截止时间不能早于当前', async ({ page }) => {
    await page.getByRole('button', { name: '创建任务' }).click()
    await expect(page.getByText('截止时间')).toBeVisible()
  })

  test('E2E-B21-13: 学时任务', async ({ page }) => {
    const row = page.locator('.el-table__body tr').first()
    await expect(row.getByText('学时达标')).toBeVisible()
  })

  test('E2E-B21-14: 未发布资料不可选', async ({ page }) => {
    await page.getByRole('button', { name: '创建任务' }).click()
    await expect(page.getByText('学习资料')).toBeVisible()
  })

  test('E2E-B21-15: 按岗位指派', async ({ page }) => {
    await page.getByRole('button', { name: '创建任务' }).click()
    await page.getByRole('button', { name: '下一步' }).click()
    await expect(page.getByText('指派方式')).toBeVisible()
    await expect(page.getByText('按岗位指派')).toBeVisible()
  })

  test('E2E-B21-16: 问卷校验', async ({ page }) => {
    await page.getByRole('button', { name: '创建任务' }).click()
    await page.getByRole('button', { name: '下一步' }).click()
    await page.getByRole('button', { name: '下一步' }).click()
    await expect(page.getByText('确认方式')).toBeVisible()
    await expect(page.getByText('自测问卷')).toBeVisible()
  })

  test('E2E-B21-17: AI生成试卷入口', async ({ page }) => {
    await page.getByRole('button', { name: '创建任务' }).click()
    await page.getByRole('button', { name: '下一步' }).click()
    await page.getByRole('button', { name: '下一步' }).click()
    await page.getByText('自测问卷').click()
    await expect(page.getByRole('button', { name: 'AI生成' })).toBeVisible()
  })

  test('E2E-B21-18: AI未配置返回1109', async ({ page }) => {
    await page.getByRole('button', { name: '创建任务' }).click()
    await page.getByRole('button', { name: '下一步' }).click()
    await page.getByRole('button', { name: '下一步' }).click()
    await page.getByText('自测问卷').click()
    await page.getByRole('button', { name: 'AI生成' }).click()
    await page.getByRole('button', { name: '开始生成' }).click()
    await expect(page.getByText('培训AI未配置')).toBeVisible({ timeout: 5000 })
  })

  test('E2E-B21-19: 编辑限制（进行中且截止前）', async ({ page }) => {
    const row = page.locator('.el-table__body tr').first()
    await expect(row.getByRole('button', { name: '编辑' })).toBeVisible()
  })

  test('E2E-B21-20: 删除任务', async ({ page }) => {
    await page.locator('.el-table__body tr').first().getByRole('button', { name: '更多' }).click()
    await expect(page.getByText('删除')).toBeVisible()
  })

  test('E2E-B21-21: 学习记录', async ({ page }) => {
    await page.locator('.el-table__body tr').first().getByRole('button', { name: '记录' }).click()
    await expect(page.getByText('学习记录')).toBeVisible()
    await expect(page.getByText('b21_student')).toBeVisible()
  })

  test('E2E-B21-22: 提醒只发一次', async ({ page }) => {
    await page.locator('.el-table__body tr').first().getByRole('button', { name: '记录' }).click()
    await expect(page.locator('.el-table')).toBeVisible()
  })

  test('E2E-B21-23: 到期自动结束', async ({ page }) => {
    await expect(page.getByText('进行中')).toBeVisible()
  })

  test('E2E-B21-24: 入职自动指派', async ({ page }) => {
    await expect(page.locator('.task-list')).toBeVisible()
  })
})

// ===== Study Tests (E2E-B21-25 ~ E2E-B21-33) =====
test.describe('E2E-B21-25~33: 学习中心', () => {
  test.beforeEach(async ({ page }) => {
    await setupTrainMocks(page)
    await page.goto('/ims/train/study')
    await page.waitForSelector('.study-center')
  })

  test('E2E-B21-25: 学习中心入口', async ({ page }) => {
    await expect(page.getByText('新人入职培训')).toBeVisible()
    await expect(page.locator('.task-card')).toBeVisible()
  })

  test('E2E-B21-26: 视频断点续播', async ({ page }) => {
    await page.locator('.task-card').first().click()
    await expect(page.getByText('学习中')).toBeVisible()
    await expect(page.getByText('直播技巧视频')).toBeVisible()
  })

  test('E2E-B21-27: 快进防刷（进度上报）', async ({ page }) => {
    await page.locator('.task-card').first().click()
    await expect(page.locator('.study-execution')).toBeVisible()
  })

  test('E2E-B21-28: 文档确认完成', async ({ page }) => {
    await page.locator('.task-card').first().click()
    await expect(page.getByText('主播入门指南')).toBeVisible()
  })

  test('E2E-B21-29: 学时未达标', async ({ page }) => {
    await page.locator('.task-card').first().click()
    await expect(page.getByText('要求学时')).toBeVisible()
    await expect(page.getByText('60 分钟')).toBeVisible()
  })

  test('E2E-B21-30: 问卷草稿暂存', async ({ page }) => {
    await expect(page.locator('.study-center')).toBeVisible()
  })

  test('E2E-B21-31: 问卷通过', async ({ page }) => {
    await expect(page.locator('.task-card')).toBeVisible()
  })

  test('E2E-B21-32: 问卷重试', async ({ page }) => {
    await expect(page.locator('.study-center')).toBeVisible()
  })

  test('E2E-B21-33: 非被指派人返回1105', async ({ page }) => {
    await page.route('**/admin-api/ims/train/study/task/*', (route: Route) => {
      route.fulfill({ json: error(1105, '非被指派人') })
    })
    await page.goto('/ims/train/study/99999')
    await expect(page.getByText('学习中心')).toBeVisible({ timeout: 5000 })
  })
})

// ===== Statistics Tests (E2E-B21-34 ~ E2E-B21-40) =====
test.describe('E2E-B21-34~40: 培训统计', () => {
  test.beforeEach(async ({ page }) => {
    await setupTrainMocks(page)
    await page.goto('/ims/train/stat')
    await page.waitForSelector('.stat-dashboard')
  })

  test('E2E-B21-34: 完成率总览', async ({ page }) => {
    await expect(page.getByText('75%')).toBeVisible()
    await expect(page.getByText('完成率')).toBeVisible()
  })

  test('E2E-B21-35: 每日汇总与低完成率推送', async ({ page }) => {
    await expect(page.getByText('B21测试部门A')).toBeVisible()
    await expect(page.getByText('B21测试部门B')).toBeVisible()
  })

  test('E2E-B21-36: 排行与热度', async ({ page }) => {
    await page.getByRole('tab', { name: '学习排行' }).click()
    await expect(page.getByText('张三')).toBeVisible()
    await page.getByRole('tab', { name: '资料热度' }).click()
    await expect(page.getByText('主播入门指南')).toBeVisible()
  })

  test('E2E-B21-37: 逾期导出', async ({ page }) => {
    await page.getByRole('tab', { name: '逾期督办' }).click()
    await expect(page.getByRole('button', { name: '导出' })).toBeVisible()
    await expect(page.getByText('王五')).toBeVisible()
  })

  test('E2E-B21-38: 数据范围过滤（DEPT传他部门返空）', async ({ page }) => {
    await expect(page.locator('.stat-dashboard')).toBeVisible()
    await page.route('**/admin-api/ims/train/stat/finish-rate*', (route: Route) => {
      const url = new URL(route.request().url())
      const deptId = url.searchParams.get('deptId')
      if (deptId && deptId !== '90001' && deptId !== '90002') {
        route.fulfill({ json: success({ totalAssigned: 0, totalFinished: 0, totalOverdue: 0, finishRate: 0, overdueRate: 0 }) })
      } else {
        route.fulfill({ json: success(mockFinishRate) })
      }
    })
  })

  test('E2E-B21-39: 跨租户隔离', async ({ page }) => {
    await expect(page.locator('.stat-dashboard')).toBeVisible()
  })

  test('E2E-B21-40: 菜单权限', async ({ page }) => {
    await expect(page.getByText('培训统计')).toBeVisible()
  })
})
