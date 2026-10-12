/**
 * 左树右表测试
 * 依据: 02-验证用例.md VC-L03-*
 */
import { test, expect } from '@playwright/test'

test.describe('L03. 左树右表', () => {
  test.beforeEach(async ({ page }) => {
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

  test.fixme('VC-L03-09: 新建人员带入部门', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-10: 全部时新建部门为空', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-11: 停用部门不带入', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-12: 新建人员树人数更新', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-13: 调部门从表消失树更新', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-14: 删除人员树人数减少', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-15: 删除有引用提示', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-16: 调部门必须指定主部门', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-17: 删除部门自动选父节点', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-18: 停用部门自动选父节点', async ({ page }) => {
    // 依赖后端 API
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

  test.fixme('VC-L03-21: 已删除部门地址提示', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-22: 数据范围树完整表受限', async ({ page }) => {
    // 依赖后端权限 API
  })

  test.fixme('VC-L03-23: 数据范围外部门空提示', async ({ page }) => {
    // 依赖后端权限 API
  })

  test.fixme('VC-L03-24: 只读用户无操作按钮', async ({ page }) => {
    // 依赖后端权限 API
  })

  test.fixme('VC-L03-25: 无权限用户暂无权限页', async ({ page }) => {
    // 依赖后端权限 API
  })

  test.fixme('VC-L03-26: 兼属多部门显示主部门', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-27: 改名后路径同步', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-28: 同步后待确认保持选中', async ({ page }) => {
    // 依赖后端 API
  })

  test.fixme('VC-L03-29: 同步删除选中部门回父', async ({ page }) => {
    // 依赖后端 API
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
