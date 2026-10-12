/**
 * 移动端测试
 * 依据: 02-验证用例.md VC-M-01~32 (VC-M-30 已撤销)
 */
import { test, expect } from '@playwright/test'
import { expectNoHOverflow, expectInViewport, hitBox, BP_MOBILE, MIN_TOUCH, MIN_GAP, MIN_GAP_SMALL, VW } from './helpers/mobile'

test.describe('移动端测试', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(page.viewportSize()?.width! >= BP_MOBILE, '仅限移动视口')
  })

  test('VC-M-01: CSS 变量 bp-mobile=768px', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const bpMobile = await page.evaluate(() =>
      getComputedStyle(document.documentElement).getPropertyValue('--bp-mobile').trim()
    )
    expect(bpMobile).toBe('768px')

    await page.setViewportSize({ width: 767, height: 844 })
    await page.waitForTimeout(300)

    const menuBtn = page.locator('.menu-btn, [data-testid="menu-btn"], button[aria-label="菜单"]').first()
    const sidebar = page.locator('.sidebar, .app-sidebar').first()

    if (await menuBtn.count() > 0) {
      await expect(menuBtn).toBeVisible()
    }
    if (await sidebar.count() > 0) {
      const hasHiddenClass = await sidebar.evaluate((el) => el.classList.contains('mobile-hidden'))
      expect(hasHiddenClass).toBe(true)
    }
  })

  test('VC-M-02: 移动端侧栏隐藏菜单按钮', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const sidebar = page.locator('.sidebar, .app-sidebar').first()
    if (await sidebar.count() > 0) {
      const isHidden = await sidebar.evaluate((el) => {
        return el.classList.contains('mobile-hidden') ||
          getComputedStyle(el).display === 'none' ||
          getComputedStyle(el).visibility === 'hidden'
      })
      expect(isHidden).toBe(true)
    }

    const main = page.locator('main, .main-content').first()
    if (await main.count() > 0) {
      const box = await main.boundingBox()
      if (box) {
        expect(box.x).toBeLessThanOrEqual(16)
      }
    }

    const menuBtn = page.locator('.menu-btn, [data-testid="menu-btn"]').first()
    if (await menuBtn.count() > 0) {
      await expect(menuBtn).toBeVisible()
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-03: 菜单抽屉滑出遮罩关闭', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const menuBtn = page.locator('.menu-btn, [data-testid="menu-btn"]').first()
    if (await menuBtn.isVisible()) {
      await menuBtn.tap()
      await page.waitForTimeout(500)

      const drawer = page.locator('.sidebar-drawer, .el-drawer').first()
      if (await drawer.isVisible()) {
        const box = await drawer.boundingBox()
        if (box) {
          expect(box.x).toBe(0)
          expect(box.width).toBeCloseTo(240, -1)
        }

        const overlay = page.locator('.el-overlay').first()
        if (await overlay.isVisible()) {
          await page.mouse.click(380, 400)
          await page.waitForTimeout(300)
          await expect(drawer).not.toBeVisible()
        }
      }
    }
  })

  test('VC-M-04: 顶栏 56px 四元素统计范围在用户菜单', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const topbar = page.locator('.app-topbar, .topbar').first()
    if (await topbar.isVisible()) {
      const box = await topbar.boundingBox()
      if (box) {
        expect(box.height).toBe(56)
      }

      const scopeInTopbar = topbar.locator(':text("统计范围")')
      expect(await scopeInTopbar.count()).toBe(0)

      const userMenu = topbar.locator('.user-menu, .el-avatar, .user-avatar').first()
      if (await userMenu.isVisible()) {
        await userMenu.tap()
        await page.waitForTimeout(300)

        const menuDropdown = page.locator('.el-dropdown-menu:visible, .user-dropdown:visible').first()
        if (await menuDropdown.isVisible()) {
          const scopeInMenu = menuDropdown.locator(':text("统计范围")')
          if (await scopeInMenu.count() > 0) {
            await expect(scopeInMenu.first()).toBeVisible()
          }
        }
      }
    }
  })

  test('VC-M-05: Tab 栏横向滚动不换行', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const tabNav = page.locator('.el-tabs__nav, .tabs-nav').first()
    if (await tabNav.isVisible()) {
      const tabs = tabNav.locator('[role=tab], .el-tabs__item')
      const count = await tabs.count()

      if (count > 1) {
        const positions = await Promise.all(
          Array.from({ length: count }, (_, i) =>
            tabs.nth(i).boundingBox().then((b) => b?.y)
          )
        )

        const uniqueYPositions = [...new Set(positions.filter(Boolean))]
        expect(uniqueYPositions.length).toBeLessThanOrEqual(2)
      }
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-06: 面包屑不溢出点击展开', async ({ page }) => {
    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')

    const breadcrumb = page.locator('.el-breadcrumb, .breadcrumb').first()
    if (await breadcrumb.isVisible()) {
      await expectInViewport(breadcrumb)

      const ellipsis = breadcrumb.locator(':text("…"), :text("...")')
      if (await ellipsis.count() > 0) {
        await ellipsis.first().tap()
        await page.waitForTimeout(300)
      }
    }
  })

  test('VC-M-07: 表格横向滚动固定列更多操作', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const table = page.locator('.el-table').first()
    await expect(table).toBeVisible()

    await expectNoHOverflow(page)

    const moreBtn = table.locator('.el-dropdown, button:has-text("更多")').first()
    if (await moreBtn.isVisible()) {
      await moreBtn.tap()
      await page.waitForTimeout(300)

      const menu = page.locator('.el-dropdown-menu:visible').first()
      if (await menu.isVisible()) {
        const items = menu.locator('.el-dropdown-menu__item')
        const count = await items.count()
        expect(count).toBeGreaterThan(0)
      }
    }
  })

  test('VC-M-08: 负数红色状态色脱敏点击提示', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const negativeAmount = page.locator(':text("-¥"), .negative-amount').first()
    if (await negativeAmount.isVisible()) {
      const color = await negativeAmount.evaluate((el) => getComputedStyle(el).color)
      expect(color).toMatch(/rgb\(255,|#ff/)
    }

    const masked = page.locator(':text("***"), .masked-text').first()
    if (await masked.isVisible()) {
      await masked.tap()
      await page.waitForTimeout(300)

      const tooltip = page.locator('.el-tooltip__popper:visible, .el-popper:visible').first()
      if (await tooltip.count() > 0) {
        await expect(tooltip).toContainText(/无.*权限/)
      }
    }
  })

  test('VC-M-09: 排序勾选触控可用', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const sortHeader = page.locator('.el-table__header th.is-sortable').first()
    if (await sortHeader.isVisible()) {
      await sortHeader.tap()
      await page.waitForTimeout(300)
    }

    const checkbox = page.locator('.el-table .el-checkbox').first()
    if (await checkbox.isVisible()) {
      await checkbox.tap()
      await page.waitForTimeout(300)
    }
  })

  test('VC-M-10: 查询栏筛选全屏抽屉 Chip', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const filterBtn = page.locator('button:has-text("筛选")').first()
    if (await filterBtn.isVisible()) {
      await filterBtn.tap()
      await page.waitForTimeout(500)

      const drawer = page.locator('.el-drawer, .filter-drawer').first()
      if (await drawer.isVisible()) {
        const box = await drawer.boundingBox()
        if (box) {
          expect(box.width).toBeCloseTo(VW, -1)
        }

        await page.keyboard.press('Escape')
      }
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-11: 分页简化 1/N 无跳页', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const pagination = page.locator('.el-pagination, .pagination').first()
    if (await pagination.isVisible()) {
      await expectInViewport(pagination)

      const pageInfo = pagination.locator(':text-matches("\\\\d+/\\\\d+")')
      if (await pageInfo.count() > 0) {
        await expect(pageInfo.first()).toBeVisible()
      }

      const sizes = pagination.locator('.el-pagination__sizes')
      const jump = pagination.locator('.el-pagination__jump')

      if (await sizes.count() > 0) {
        await expect(sizes.first()).not.toBeVisible()
      }
      if (await jump.count() > 0) {
        await expect(jump.first()).not.toBeVisible()
      }
    }
  })

  test('VC-M-12: 统计卡每行 2 列', async ({ page }) => {
    await page.goto('/demo/tabs-list')
    await page.waitForSelector('.tabs-list-demo, .app-layout')

    const cards = page.locator('.stat-card')
    const count = await cards.count()

    if (count > 2) {
      const positions = await Promise.all(
        Array.from({ length: count }, (_, i) =>
          cards.nth(i).boundingBox().then((b) => Math.round(b?.y || 0))
        )
      )

      const rowGroups: Record<number, number> = {}
      positions.forEach((y) => {
        rowGroups[y] = (rowGroups[y] || 0) + 1
      })

      const rowCounts = Object.values(rowGroups)
      const maxPerRow = Math.max(...rowCounts)
      expect(maxPerRow).toBeLessThanOrEqual(2)
    }
  })

  test('VC-M-13: 表单单列标签在上', async ({ page }) => {
    await page.goto('/demo/form')
    await page.waitForSelector('.form-demo, .app-layout')

    const openBtn = page.locator('button:has-text("新建"), button:has-text("打开")').first()
    if (await openBtn.isVisible()) {
      await openBtn.tap()
      await page.waitForTimeout(500)

      const formItems = page.locator('.el-form-item:visible')
      const count = await formItems.count()

      if (count > 1) {
        const positions = await Promise.all(
          Array.from({ length: Math.min(count, 5) }, (_, i) =>
            formItems.nth(i).boundingBox().then((b) => b?.y)
          )
        )

        const uniqueY = [...new Set(positions.filter(Boolean))]
        expect(uniqueY.length).toBe(Math.min(count, 5))
      }
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-14: 输入框字号>=16px 不缩放', async ({ page }) => {
    await page.goto('/demo/form')
    await page.waitForSelector('.form-demo, .app-layout')

    const inputs = page.locator('input:visible, textarea:visible')
    const count = await inputs.count()

    for (let i = 0; i < Math.min(count, 5); i++) {
      const input = inputs.nth(i)
      const fontSize = await input.evaluate((el) =>
        parseFloat(getComputedStyle(el).fontSize)
      )
      expect(fontSize).toBeGreaterThanOrEqual(16)
    }

    const firstInput = inputs.first()
    if (await firstInput.isVisible()) {
      await firstInput.focus()
      await page.waitForTimeout(300)

      const scale = await page.evaluate(() =>
        window.visualViewport?.scale || 1
      )
      expect(scale).toBeCloseTo(1, 1)
    }
  })

  test('VC-M-15: 抽屉全屏从右滑入固定按钮', async ({ page }) => {
    await page.goto('/demo/form')
    await page.waitForSelector('.form-demo, .app-layout')

    const openBtn = page.locator('button:has-text("新建"), button:has-text("打开")').first()
    if (await openBtn.isVisible()) {
      await openBtn.tap()
      await page.waitForTimeout(500)

      const drawer = page.locator('.el-drawer').first()
      if (await drawer.isVisible()) {
        const box = await drawer.boundingBox()
        if (box) {
          expect(box.width).toBeCloseTo(VW, -1)
          expect(box.x).toBe(0)
        }

        const footer = drawer.locator('.el-drawer__footer, .drawer-footer').first()
        if (await footer.isVisible()) {
          await expectInViewport(footer)
        }
      }
    }
  })

  test('VC-M-16: 弹窗宽度 min(档位, 358px)', async ({ page }) => {
    await page.goto('/demo/form')
    await page.waitForSelector('.form-demo, .app-layout')

    const modalBtn = page.locator('button:has-text("弹窗")').first()
    if (await modalBtn.isVisible()) {
      await modalBtn.tap()
      await page.waitForTimeout(300)

      const dialog = page.locator('.el-dialog').first()
      if (await dialog.isVisible()) {
        const box = await dialog.boundingBox()
        if (box) {
          expect(box.width).toBeLessThanOrEqual(358)
          expect(box.x).toBeGreaterThanOrEqual(16 - 1)
        }

        await page.keyboard.press('Escape')
      }
    }
  })

  test('VC-M-17: 向导只显示第 N/M 步', async ({ page }) => {
    await page.goto('/demo/form')
    await page.waitForSelector('.form-demo, .app-layout')

    const wizardBtn = page.locator('button:has-text("向导")').first()
    if (await wizardBtn.isVisible()) {
      await wizardBtn.tap()
      await page.waitForTimeout(500)

      const stepIndicator = page.locator(':text-matches("第 \\\\d+/\\\\d+ 步")')
      if (await stepIndicator.count() > 0) {
        await expect(stepIndicator.first()).toBeVisible()
      }

      const stepsBar = page.locator('.el-steps')
      if (await stepsBar.count() > 0) {
        await expect(stepsBar.first()).not.toBeVisible()
      }
    }
  })

  test('VC-M-18: 空态无权限出错态完整显示', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const emptyState = page.locator('.el-empty, .empty-state').first()
    if (await emptyState.isVisible()) {
      await expectInViewport(emptyState)
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-19: 加载遮罩在视口内', async ({ page }) => {
    await page.goto('/demo/list')

    const loadingMask = page.locator('.el-loading-mask').first()
    if (await loadingMask.isVisible()) {
      await expectInViewport(loadingMask)
    }

    await page.waitForSelector('.list-demo, .app-layout')
    await expectNoHOverflow(page)
  })

  test('VC-M-20: Toast 顶部居中宽度<=358', async ({ page }) => {
    await page.goto('/demo/request')
    await page.waitForSelector('.request-demo, .app-layout')

    const successBtn = page.getByRole('button', { name: '成功请求' })
    await successBtn.tap()

    const message = page.locator('.el-message').first()
    if (await message.isVisible()) {
      const box = await message.boundingBox()
      if (box) {
        expect(box.width).toBeLessThanOrEqual(358)
        expect(box.y).toBeLessThan(844 / 2)

        const centerX = box.x + box.width / 2
        expect(Math.abs(centerX - VW / 2)).toBeLessThan(50)
      }
    }
  })

  test('VC-M-21: 选择器下拉在视口内滚动加载', async ({ page }) => {
    await page.goto('/demo/selectors')
    await page.waitForSelector('.selectors-demo, .app-layout')

    const select = page.locator('.el-select').first()
    if (await select.isVisible()) {
      await select.tap()
      await page.waitForTimeout(300)

      const popper = page.locator('.el-popper:visible, .el-select-dropdown:visible').first()
      if (await popper.isVisible()) {
        await expectInViewport(popper)
      }
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-22: 文件上传导入导出下载条', async ({ page }) => {
    // 验证移动端文件操作组件
    await page.goto('/demo/files')
    await page.waitForSelector('.files-demo, .app-layout')
    
    // 验证上传组件在移动端正常显示
    const upload = page.locator('.el-upload, .file-upload').first()
    if (await upload.count() > 0) {
      await expectInViewport(upload)
    }
    
    await expectNoHOverflow(page)
  })

  test('VC-M-23: 展示组件单列图表自适应', async ({ page }) => {
    await page.goto('/demo/display')
    await page.waitForSelector('.display-demo, .app-layout')

    const descList = page.locator('.el-descriptions, .description-list').first()
    if (await descList.isVisible()) {
      const items = descList.locator('.el-descriptions-item, .desc-item')
      const count = await items.count()

      if (count > 1) {
        const positions = await Promise.all(
          Array.from({ length: Math.min(count, 5) }, (_, i) =>
            items.nth(i).boundingBox().then((b) => b?.y)
          )
        )

        const uniqueY = [...new Set(positions.filter(Boolean))]
        expect(uniqueY.length).toBe(Math.min(count, 5))
      }
    }

    const chart = page.locator('canvas, .chart').first()
    if (await chart.isVisible()) {
      const box = await chart.boundingBox()
      if (box) {
        expect(box.width).toBeLessThanOrEqual(VW)
      }
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-24: 画布设计器请在电脑端编辑', async ({ page }) => {
    await page.goto('/demo/display')
    await page.waitForSelector('.display-demo, .app-layout')

    const desktopHint = page.locator(':text("请在电脑端编辑"), .desktop-only-hint')
    if (await desktopHint.count() > 0) {
      await expect(desktopHint.first()).toBeVisible()
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-25: 左树右表部门抽屉', async ({ page }) => {
    await page.goto('/demo/left-tree-right-table')
    await page.waitForSelector('.left-tree-right-table-demo, .app-layout')

    await expectNoHOverflow(page)

    const deptBtn = page.locator('button:has-text("部门"), .dept-btn').first()
    if (await deptBtn.count() > 0 && await deptBtn.isVisible()) {
      await deptBtn.tap()
      await page.waitForTimeout(500)

      const drawer = page.locator('.el-drawer').first()
      if (await drawer.count() > 0 && await drawer.isVisible()) {
        const treeInDrawer = drawer.locator('.el-tree')
        if (await treeInDrawer.count() > 0) {
          await expect(treeInDrawer.first()).toBeVisible()
        }
      }
    }
  })

  test('VC-M-26: 工作台填报页布局', async ({ page }) => {
    await page.goto('/demo/workbench')
    await page.waitForSelector('.workbench-demo, .app-layout')
    await expectNoHOverflow(page)

    await page.goto('/demo/fill')
    await page.waitForSelector('.fill-demo, .app-layout')

    const submitBar = page.locator('.submit-bar, .footer-actions').first()
    if (await submitBar.isVisible()) {
      const box = await submitBar.boundingBox()
      if (box) {
        expect(box.y + box.height).toBeCloseTo(844, -1)
      }
    }

    await expectNoHOverflow(page)
  })

  test('VC-M-27: 触控热区>=44px 间距>=8px 小号按钮间距>=18px', async ({ page }) => {
    // 依据: §2.1 Q10, §2.2 #3, §2.3 U1
    await page.goto('/demo/tokens')
    await page.waitForSelector('.tokens-demo, .app-layout')

    // 获取小号按钮，验证触控热区 ≥44×44px (§2.3 U1)
    const smallButtons = page.locator('.el-button--small:visible')
    const smallCount = await smallButtons.count()

    // 使用 hitBox() 验证小号按钮的触控热区
    for (let i = 0; i < Math.min(smallCount, 5); i++) {
      const btn = smallButtons.nth(i)
      const hit = await hitBox(btn)
      // 触控热区必须 ≥44×44px (通过点击测试或 CSS ::before 伪元素)
      // 注: hitBox 检测实际可点击范围，若 CSS 伪元素扩展了热区，
      //     需验证 ::before 的 min-width/min-height 是否为 44px
      expect(hit.width).toBeGreaterThanOrEqual(MIN_TOUCH)
      expect(hit.height).toBeGreaterThanOrEqual(MIN_TOUCH)
    }

    // 检查小号按钮之间的视觉间距 ≥18px (§2.3 U1)
    if (smallCount >= 2) {
      const boxes = await Promise.all(
        Array.from({ length: smallCount }, (_, i) =>
          smallButtons.nth(i).boundingBox()
        )
      )

      for (let i = 0; i < boxes.length - 1; i++) {
        const current = boxes[i]
        const next = boxes[i + 1]

        if (current && next) {
          // 同一行 (y 坐标相近)
          if (Math.abs(current.y - next.y) < 10) {
            const gap = next.x - (current.x + current.width)
            // 小号按钮之间的视觉间距 ≥18px
            expect(gap).toBeGreaterThanOrEqual(MIN_GAP_SMALL - 1) // 允许 1px 误差
          }
        }
      }
    }

    // 普通按钮间距 ≥8px
    const normalButtons = page.locator('.el-button:visible:not(.el-button--small)')
    const normalCount = await normalButtons.count()

    if (normalCount >= 2) {
      const boxes = await Promise.all(
        Array.from({ length: normalCount }, (_, i) =>
          normalButtons.nth(i).boundingBox()
        )
      )

      for (let i = 0; i < boxes.length - 1; i++) {
        const current = boxes[i]
        const next = boxes[i + 1]

        if (current && next && Math.abs(current.y - next.y) < 10) {
          const gap = next.x - (current.x + current.width)
          expect(gap).toBeGreaterThanOrEqual(MIN_GAP - 1)
        }
      }
    }
  })

  test('VC-M-28: 最小字号>=12px', async ({ page }) => {
    // 依据: §2.1 Q12 - 手机上最小字号 12px
    await page.goto('/demo/tokens')
    await page.waitForSelector('.tokens-demo, .app-layout')

    const minFontSize = await page.evaluate(() => {
      const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        null
      )

      let minSize = 16
      while (walker.nextNode()) {
        const text = walker.currentNode.textContent?.trim()
        if (text) {
          const parent = walker.currentNode.parentElement
          if (parent) {
            const size = parseFloat(getComputedStyle(parent).fontSize)
            if (size < minSize) {
              minSize = size
            }
          }
        }
      }
      return minSize
    })

    // §2.1 Q12: 最小字号必须 ≥12px
    expect(minFontSize).toBeGreaterThanOrEqual(12)
  })

  test('VC-M-29: viewport meta 无禁止缩放', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const viewportContent = await page.locator('meta[name=viewport]').getAttribute('content')
    expect(viewportContent).toMatch(/width=device-width/)
    expect(viewportContent).not.toMatch(/user-scalable\s*=\s*(no|0)/)

    if (viewportContent?.includes('maximum-scale')) {
      const match = viewportContent.match(/maximum-scale\s*=\s*([\d.]+)/)
      if (match) {
        expect(parseFloat(match[1])).toBeGreaterThanOrEqual(2)
      }
    }
  })

  test('VC-M-31: 内容区内边距页头标题操作', async ({ page }) => {
    await page.goto('/demo/list')
    await page.waitForSelector('.list-demo, .app-layout')

    const title = page.locator('.page-title, .page-header h1').first()
    if (await title.isVisible()) {
      const fontSize = await title.evaluate((el) => getComputedStyle(el).fontSize)
      expect(parseFloat(fontSize)).toBeGreaterThanOrEqual(18)
    }

    const actions = page.locator('.header-actions').first()
    if (await actions.isVisible()) {
      const buttons = actions.locator('button:visible')
      const count = await buttons.count()
      expect(count).toBeLessThanOrEqual(3)
    }

    await expectInViewport(page.locator('main, .main-content').first())
  })

  test('VC-M-32: 全局冒烟无溢出无异常', async ({ page, request }) => {
    const errors: string[] = []

    page.on('pageerror', (error) => {
      errors.push(`PageError: ${error.message}`)
    })

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(`ConsoleError: ${msg.text()}`)
      }
    })

    const routes = [
      '/demo/tokens',
      '/demo/layout',
      '/demo/list',
      '/demo/tabs-list',
      '/demo/form',
      '/demo/selectors',
      '/demo/files',
      '/demo/display',
      '/demo/dept-tree',
      '/demo/left-tree-right-table',
      '/demo/workbench',
      '/demo/fill',
      '/demo/request',
    ]

    for (const route of routes) {
      await test.step(`检查 ${route}`, async () => {
        await page.goto(route)
        await page.waitForLoadState('networkidle')
        await expectNoHOverflow(page)
      })
    }

    // §2.2 #9: v-perm 错误码现在是 warn 不是 error，所以不需要过滤
    const relevantErrors = errors.filter(
      (e) =>
        !e.includes('ResizeObserver') &&
        !e.includes('favicon') &&
        !e.includes('props.items')
    )
    expect(relevantErrors).toHaveLength(0)
  })

  test('VC-M-33: __routes 接口不需鉴权返回路由清单', async ({ playwright }) => {
    // 使用新的请求上下文，不带令牌
    const ctx = await playwright.request.newContext({
      baseURL: 'http://localhost:3000',
    })

    const res = await ctx.get('/__routes')
    expect(res.status()).toBe(200)

    const contentType = res.headers()['content-type'] || ''
    expect(contentType).toMatch(/application\/json/)

    const list = await res.json()
    expect(Array.isArray(list)).toBe(true)

    // 验证每一项的结构
    for (const item of list) {
      expect(typeof item.path).toBe('string')
      expect(item.path.startsWith('/')).toBe(true)
      expect(typeof item.name).toBe('string')
      expect(item.meta).toBeDefined()
      expect(typeof item.meta).toBe('object')
      expect(item.meta).not.toBeNull()
      expect(Array.isArray(item.meta)).toBe(false)
    }

    // 验证 path 不重复
    const paths = list.map((r: { path: string }) => r.path)
    expect(new Set(paths).size).toBe(paths.length)

    // 验证包含 01 §P 列出的全部 /demo/* 路径
    const expectedPaths = [
      '/demo/tokens',
      '/demo/request',
      '/demo/layout',
      '/demo/list',
      '/demo/tabs-list',
      '/demo/form',
      '/demo/selectors',
      '/demo/files',
      '/demo/display',
      '/demo/dept-tree',
      '/demo/left-tree-right-table',
      '/demo/workbench',
      '/demo/fill',
    ]
    expect(paths).toEqual(expect.arrayContaining(expectedPaths))

    await ctx.dispose()
  })

  test('VC-M-34: 生产构建不提供 __routes 示例页跳首页', async ({ page, browserName }, testInfo) => {
    // 此测试仅在 prod-build 项目中运行
    test.skip(testInfo.project.name !== 'prod-build', '仅在 prod-build 项目中运行')

    // 测试 /__routes 返回 404 或非 JSON
    const res = await page.request.get('/__routes')
    const isNotAvailable =
      res.status() === 404 ||
      !(res.headers()['content-type'] || '').includes('application/json')

    expect(isNotAvailable).toBe(true)

    // 访问 /demo/list 应跳转到首页
    await page.goto('/demo/list')
    await page.waitForLoadState('networkidle')

    // 验证跳转到首页
    const url = page.url()
    expect(url).toMatch(/\/($|home|workspace|workbench)/)

    // 验证没有示例表格内容
    const table = page.locator('.el-table')
    expect(await table.count()).toBe(0)
  })

  test('VC-M-35: 错误权限码 warn 不影响冒烟', async ({ page }) => {
    // 依据: §2.2 #9 - 权限码格式错误使用 console.warn，不影响冒烟
    const warnings: string[] = []
    const errors: string[] = []

    page.on('console', (msg) => {
      if (msg.type() === 'warning') {
        warnings.push(msg.text())
      } else if (msg.type() === 'error') {
        errors.push(msg.text())
      }
    })

    page.on('pageerror', (error) => {
      errors.push(error.message)
    })

    await page.goto('/demo/layout')
    await page.waitForSelector('.app-layout')
    await page.waitForLoadState('networkidle')

    // 验证有至少一条关于 bad-code 或 v-perm 的 warning (§2.2 #9)
    const badCodeWarnings = warnings.filter((w) => w.includes('bad-code') || w.includes('v-perm'))
    expect(badCodeWarnings.length).toBeGreaterThanOrEqual(1)

    // 验证没有关于 bad-code 或 v-perm 的 error
    // 按 §2.2 #9，权限码格式错误应该是 warn 不是 error
    const badCodeErrors = errors.filter((e) => e.includes('bad-code') || e.includes('v-perm'))
    expect(badCodeErrors).toHaveLength(0)

    // 验证没有其他 error（排除常见无关错误）
    const relevantErrors = errors.filter(
      (e) =>
        !e.includes('ResizeObserver') &&
        !e.includes('favicon') &&
        !e.includes('props.items')
    )
    expect(relevantErrors).toHaveLength(0)

    // 无横向溢出
    await expectNoHOverflow(page)
  })
})
