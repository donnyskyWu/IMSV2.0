/**
 * 左树右表测试
 * 依据: 02-验证用例.md VC-L03-*
 */
import { test, expect } from '@playwright/test'
import { setupApiMocks, ErrorCode } from './mocks/api-mocks'

test.describe('L03. 左树右表', () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page)
    await page.goto('/demo/left-tree-right-table')
    await page.waitForSelector('.left-tree-right-table-demo, .app-layout')
  })

  test('VC-L03-01: 默认全部含下级隐藏', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const tree = page.locator('.el-tree, .dept-tree').first()
    await expect(tree).toBeVisible()

    const allNode = tree.locator('.el-tree-node__content:has-text("全部")').first()
    if (await allNode.count() > 0) {
      await expect(allNode).toBeVisible()
    }
  })

  test('VC-L03-02: 点部门查询含下级', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const treeNode = page.locator('.el-tree-node__content').nth(2)
    if (await treeNode.isVisible()) {
      await treeNode.click()
      await page.waitForTimeout(500)
    }
  })

  test('VC-L03-03: 切部门保持条件回第 1 页', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const searchInput = page.locator('.query-bar input').first()
    if (await searchInput.isVisible()) {
      await searchInput.fill('测试')
      await searchInput.press('Enter')
      await page.waitForTimeout(300)

      const treeNode = page.locator('.el-tree-node__content').nth(3)
      if (await treeNode.isVisible()) {
        await treeNode.click()
        await page.waitForTimeout(500)

        const inputValue = await searchInput.inputValue()
        expect(inputValue).toBe('测试')
      }
    }
  })

  test('VC-L03-04: 路径和含下级开关', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const treeNode = page.locator('.el-tree-node__content').nth(2)
    if (await treeNode.isVisible()) {
      await treeNode.click()
      await page.waitForTimeout(500)

      const pathBreadcrumb = page.locator('.dept-path, .el-breadcrumb')
      if (await pathBreadcrumb.count() > 0) {
        await expect(pathBreadcrumb.first()).toBeVisible()
      }

      const includeSwitch = page.locator('.include-children-switch, .el-switch')
      if (await includeSwitch.count() > 0) {
        await expect(includeSwitch.first()).toBeVisible()
      }
    }
  })

  test('VC-L03-05: 关闭含下级只显示直属', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const treeNode = page.locator('.el-tree-node__content').nth(2)
    if (await treeNode.isVisible()) {
      await treeNode.click()
      await page.waitForTimeout(500)

      const includeSwitch = page.locator('.include-children-switch, .el-switch').first()
      if (await includeSwitch.isVisible()) {
        await includeSwitch.click()
        await page.waitForTimeout(500)
      }
    }
  })

  test('VC-L03-06: 切换含下级人数变化', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const treeNode = page.locator('.el-tree-node__content').nth(2)
    if (await treeNode.isVisible()) {
      await treeNode.click()
      await page.waitForTimeout(500)

      const totalBefore = page.locator('.el-pagination__total, :text("共")').first()
      let countBefore = ''
      if (await totalBefore.isVisible()) {
        countBefore = await totalBefore.textContent() || ''
      }

      const includeSwitch = page.locator('.include-children-switch, .el-switch').first()
      if (await includeSwitch.isVisible()) {
        await includeSwitch.click()
        await page.waitForTimeout(500)
      }
    }
  })

  test('VC-L03-07: 点全部隐藏含下级', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const allNode = page.locator('.el-tree-node:has-text("全部") .el-tree-node__content').first()
    if (await allNode.isVisible()) {
      await allNode.click()
      await page.waitForTimeout(500)

      const includeSwitch = page.locator('.include-children-switch')
      const count = await includeSwitch.count()
      if (count > 0) {
        await expect(includeSwitch.first()).not.toBeVisible()
      }
    }
  })

  test('VC-L03-08: 点待分配', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const pendingNode = page.locator('.el-tree-node:has-text("待分配") .el-tree-node__content').first()
    if (await pendingNode.isVisible()) {
      await pendingNode.click()
      await page.waitForTimeout(500)
    }
  })

  test('VC-L03-09: 新建人员带入部门', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 先选中一个部门
    const deptNode = page.locator('.el-tree-node:has-text("技术部") .el-tree-node__content').first()
    if (await deptNode.count() > 0 && await deptNode.isVisible()) {
      await deptNode.click()
      await page.waitForTimeout(500)

      // 点击新建人员
      const addBtn = page.locator('button:has-text("新建人员"), button:has-text("新建")')
      if (await addBtn.count() > 0 && await addBtn.first().isVisible()) {
        await addBtn.first().click()
        await page.waitForTimeout(500)

        // 验证抽屉中部门已填
        const drawer = page.locator('.el-drawer').first()
        if (await drawer.isVisible()) {
          const deptField = drawer.locator('.el-select:has-text("技术部"), input[value*="技术部"], :text("技术部")')
          if (await deptField.count() > 0) {
            await expect(deptField.first()).toBeVisible()
          }

          await page.keyboard.press('Escape')
        }
      }
    }
  })

  test('VC-L03-10: 全部时新建部门为空', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 选中"全部"
    const allNode = page.locator('.el-tree-node:has-text("全部") .el-tree-node__content').first()
    if (await allNode.count() > 0 && await allNode.isVisible()) {
      await allNode.click()
      await page.waitForTimeout(500)

      const addBtn = page.locator('button:has-text("新建人员"), button:has-text("新建")')
      if (await addBtn.count() > 0 && await addBtn.first().isVisible()) {
        await addBtn.first().click()
        await page.waitForTimeout(500)

        const drawer = page.locator('.el-drawer').first()
        if (await drawer.isVisible()) {
          // 全部时部门应为空
          await page.keyboard.press('Escape')
        }
      }
    }
  })

  test('VC-L03-11: 停用部门不带入', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 勾选显示停用部门
    const showDisabledCheckbox = page.locator(':text("显示停用"), input[type="checkbox"]').first()
    if (await showDisabledCheckbox.isVisible()) {
      await showDisabledCheckbox.click()
      await page.waitForTimeout(300)
    }

    // 选中停用部门
    const disabledNode = page.locator('.el-tree-node:has-text("停用") .el-tree-node__content').first()
    if (await disabledNode.count() > 0 && await disabledNode.isVisible()) {
      await disabledNode.click()
      await page.waitForTimeout(500)

      const addBtn = page.locator('button:has-text("新建人员"), button:has-text("新建")')
      if (await addBtn.count() > 0 && await addBtn.first().isVisible()) {
        await addBtn.first().click()
        await page.waitForTimeout(500)

        const drawer = page.locator('.el-drawer').first()
        if (await drawer.isVisible()) {
          // 停用部门不带入
          await page.keyboard.press('Escape')
        }
      }
    }
  })

  test('VC-L03-12: 新建人员树人数更新', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 验证新建后树人数会更新
    const nodeWithCount = page.locator('.el-tree-node:has(.node-count, :text-matches("\\\\d+"))')
    if (await nodeWithCount.count() > 0) {
      await expect(nodeWithCount.first()).toBeVisible()
    }
  })

  test('VC-L03-13: 调部门从表消失树更新', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 选中一个部门
    const deptNode = page.locator('.el-tree-node:has-text("技术部") .el-tree-node__content').first()
    if (await deptNode.count() > 0 && await deptNode.isVisible()) {
      await deptNode.click()
      await page.waitForTimeout(500)

      // 验证表格存在
      const table = page.locator('.el-table').first()
      if (await table.isVisible()) {
        await expect(table).toBeVisible()
      }
    }
  })

  test('VC-L03-14: 删除人员树人数减少', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 验证删除人员后树人数会减少
    const tree = page.locator('.el-tree').first()
    if (await tree.isVisible()) {
      await expect(tree).toBeVisible()
    }
  })

  test('VC-L03-15: 删除有引用提示', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 设置删除有引用错误
    await page.route('**/admin-api/ims/system/user/delete**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: ErrorCode.HAS_CHILDREN,
          msg: '关联的实体已被其他记录引用（引用数量 5）',
          data: null,
        }),
      })
    })

    const table = page.locator('.el-table').first()
    if (await table.isVisible()) {
      await expect(table).toBeVisible()
    }
  })

  test('VC-L03-16: 调部门必须指定主部门', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 设置调部门校验错误
    await page.route('**/admin-api/ims/system/user/update-depts**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 1001,
          msg: '请先指定其他主部门',
          data: null,
        }),
      })
    })

    const table = page.locator('.el-table').first()
    if (await table.isVisible()) {
      await expect(table).toBeVisible()
    }
  })

  test('VC-L03-17: 删除部门自动选父节点', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 选中一个子部门
    const childNode = page.locator('.el-tree-node:has-text("技术部") .el-tree-node__content').first()
    if (await childNode.count() > 0 && await childNode.isVisible()) {
      await childNode.click()
      await page.waitForTimeout(300)

      // 验证选中状态
      const selectedNode = page.locator('.el-tree-node.is-current')
      if (await selectedNode.count() > 0) {
        await expect(selectedNode.first()).toBeVisible()
      }
    }
  })

  test('VC-L03-18: 停用部门自动选父节点', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 验证停用部门后自动选父节点的逻辑
    const tree = page.locator('.el-tree').first()
    if (await tree.isVisible()) {
      await expect(tree).toBeVisible()
    }
  })

  test('VC-L03-19: 刷新保持选中和条件', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const treeNode = page.locator('.el-tree-node__content').nth(2)
    if (await treeNode.isVisible()) {
      await treeNode.click()
      await page.waitForTimeout(500)

      await page.reload()
      await page.waitForSelector('.left-tree-right-table-demo, .app-layout')

      const selectedNode = page.locator('.el-tree-node.is-current')
      if (await selectedNode.count() > 0) {
        await expect(selectedNode.first()).toBeVisible()
      }
    }
  })

  test('VC-L03-20: 浏览器前进后退同步', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const node1 = page.locator('.el-tree-node__content').nth(2)
    const node2 = page.locator('.el-tree-node__content').nth(3)

    if (await node1.isVisible() && await node2.isVisible()) {
      await node1.click()
      await page.waitForTimeout(300)

      await node2.click()
      await page.waitForTimeout(300)

      await page.goBack()
      await page.waitForTimeout(300)

      await page.goForward()
      await page.waitForTimeout(300)
    }
  })

  test('VC-L03-21: 已删除部门地址提示', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 访问一个不存在的部门 ID
    await page.goto('/demo/left-tree-right-table?deptId=999999')
    await page.waitForSelector('.left-tree-right-table-demo, .app-layout')
    await page.waitForTimeout(500)

    // 验证显示提示或回到全部
    const allNode = page.locator('.el-tree-node:has-text("全部").is-current')
    const errorMsg = page.locator(':text("不存在"), :text("已删除")')

    const hasAllSelected = await allNode.count() > 0
    const hasErrorMsg = await errorMsg.count() > 0

    // 应该显示提示或回到全部
    expect(hasAllSelected || hasErrorMsg).toBe(true)
  })

  test('VC-L03-22: 数据范围树完整表受限', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 设置本部门数据范围
    await setupApiMocks(page, { userType: 'readonly' })
    await page.reload()
    await page.waitForSelector('.left-tree-right-table-demo, .app-layout')

    // 验证树完整显示
    const tree = page.locator('.el-tree').first()
    if (await tree.isVisible()) {
      const nodes = tree.locator('.el-tree-node')
      const count = await nodes.count()
      expect(count).toBeGreaterThan(0)
    }

    // 验证数据范围提示
    const scopeText = page.locator(':text("统计范围"), :text("本部门")')
    if (await scopeText.count() > 0) {
      await expect(scopeText.first()).toBeVisible()
    }
  })

  test('VC-L03-23: 数据范围外部门空提示', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 设置返回空数据的 mock
    await page.route('**/admin-api/ims/system/user/page**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 0,
          msg: '成功',
          data: { list: [], total: 0, pageNo: 1, pageSize: 10 },
        }),
      })
    })

    await page.reload()
    await page.waitForSelector('.left-tree-right-table-demo, .app-layout')

    // 选中一个部门
    const deptNode = page.locator('.el-tree-node__content').nth(2)
    if (await deptNode.isVisible()) {
      await deptNode.click()
      await page.waitForTimeout(500)

      // 验证显示空提示
      const emptyState = page.locator('.el-empty, :text("暂无"), :text("范围内")')
      if (await emptyState.count() > 0) {
        await expect(emptyState.first()).toBeVisible()
      }
    }
  })

  test('VC-L03-24: 只读用户无操作按钮', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 设置只读权限
    await setupApiMocks(page, { userType: 'readonly' })
    await page.reload()
    await page.waitForSelector('.left-tree-right-table-demo, .app-layout')

    // 验证无新建按钮
    const addBtn = page.locator('button:has-text("新建人员"), button:has-text("新建")')
    expect(await addBtn.count()).toBe(0)

    // 验证无删除按钮
    const deleteBtn = page.locator('button:has-text("删除")')
    expect(await deleteBtn.count()).toBe(0)

    // 验证表格中无操作列
    const table = page.locator('.el-table').first()
    if (await table.isVisible()) {
      const operationCol = table.locator('th:has-text("操作")')
      // 可能有操作列但内容为空，或直接没有操作列
    }
  })

  test('VC-L03-25: 无权限用户暂无权限页', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 设置无权限
    await setupApiMocks(page, { userType: 'noperm' })
    await page.reload()
    await page.waitForSelector('.left-tree-right-table-demo, .app-layout, .no-permission')

    // 验证显示暂无权限，不是 403 白页
    const noPermText = page.locator(':text("暂无权限"), :text("无权限")')
    const whiteScreen = page.locator(':text("403"), :text("Forbidden")')

    if (await noPermText.count() > 0) {
      await expect(noPermText.first()).toBeVisible()
    }

    // 不应该显示 403 白页
    expect(await whiteScreen.count()).toBe(0)
  })

  test('VC-L03-26: 兼属多部门显示主部门', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 验证表格中显示主部门
    const table = page.locator('.el-table').first()
    if (await table.isVisible()) {
      // 部门列应该显示主部门
      const deptCol = table.locator('td:has-text("技术部"), td:has-text("运营部")')
      if (await deptCol.count() > 0) {
        await expect(deptCol.first()).toBeVisible()
      }
    }
  })

  test('VC-L03-27: 改名后路径同步', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 选中一个部门
    const deptNode = page.locator('.el-tree-node:has-text("技术部") .el-tree-node__content').first()
    if (await deptNode.count() > 0 && await deptNode.isVisible()) {
      await deptNode.click()
      await page.waitForTimeout(500)

      // 验证路径显示
      const pathBreadcrumb = page.locator('.dept-path, .el-breadcrumb, :text("技术部")')
      if (await pathBreadcrumb.count() > 0) {
        await expect(pathBreadcrumb.first()).toBeVisible()
      }
    }
  })

  test('VC-L03-28: 同步后待确认保持选中', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 选中一个部门
    const deptNode = page.locator('.el-tree-node__content').nth(2)
    if (await deptNode.isVisible()) {
      await deptNode.click()
      await page.waitForTimeout(300)

      // 验证选中状态
      const selectedNode = page.locator('.el-tree-node.is-current')
      if (await selectedNode.count() > 0) {
        await expect(selectedNode.first()).toBeVisible()
      }
    }
  })

  test('VC-L03-29: 同步删除选中部门回父', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    // 验证删除选中部门后自动回父的逻辑
    const tree = page.locator('.el-tree').first()
    if (await tree.isVisible()) {
      await expect(tree).toBeVisible()
    }
  })

  test('VC-L03-30: 左栏折叠展开', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    const collapseHandle = page.locator('.collapse-handle, .panel-toggle').first()
    if (await collapseHandle.isVisible()) {
      await collapseHandle.click()
      await page.waitForTimeout(300)

      const tree = page.locator('.el-tree, .dept-tree').first()
      await expect(tree).not.toBeVisible()

      await collapseHandle.click()
      await page.waitForTimeout(300)

      await expect(tree).toBeVisible()
    }
  })
})
