/**
 * Token 系统测试
 * 依据: 02-验证用例.md VC-T-01~04
 */
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { ESLint } from 'eslint'
import stylelint from 'stylelint'
import { test, expect } from '@playwright/test'

test.describe('T. Token 系统', () => {
  test('VC-T-01: CSS 变量色值与尺寸应与标注一致', async ({ page }) => {
    test.skip(page.viewportSize()?.width! < 768, '仅限桌面视口')

    await page.goto('/demo/tokens')
    await page.waitForSelector('.tokens-demo, .app-layout')

    const vars = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement)
      return {
        blue: style.getPropertyValue('--blue').trim(),
        sidebarWidth: style.getPropertyValue('--sidebar-width').trim(),
        topbarHeight: style.getPropertyValue('--topbar-height').trim(),
        drawerS: style.getPropertyValue('--drawer-s').trim(),
        drawerM: style.getPropertyValue('--drawer-m').trim(),
        drawerL: style.getPropertyValue('--drawer-l').trim(),
      }
    })

    expect(vars.blue).toBe('#0071e3')
    expect(vars.sidebarWidth).toBe('232px')
    expect(vars.topbarHeight).toBe('56px')
    expect(vars.drawerS).toBe('480px')
    expect(vars.drawerM).toBe('720px')
    expect(vars.drawerL).toBe('880px')
  })

  test('VC-T-02: 状态色 8 组应与标注一致', async ({ page }) => {
    await page.goto('/demo/tokens')
    await page.waitForSelector('.tokens-demo, .app-layout')

    const statusColors = await page.evaluate(() => {
      const style = getComputedStyle(document.documentElement)
      return {
        primaryText: style.getPropertyValue('--status-primary-text').trim(),
        successText: style.getPropertyValue('--status-success-text').trim(),
        warningText: style.getPropertyValue('--status-warning-text').trim(),
        dangerText: style.getPropertyValue('--status-danger-text').trim(),
        neutralText: style.getPropertyValue('--status-neutral-text').trim(),
        infoText: style.getPropertyValue('--status-info-text').trim(),
        purpleText: style.getPropertyValue('--status-purple-text').trim(),
        yellowText: style.getPropertyValue('--status-yellow-text').trim(),
      }
    })

    expect(statusColors.primaryText).toBe('#0071e3')
    expect(statusColors.successText).toBe('#1e8e3e')
    expect(statusColors.warningText).toBe('#c46a00')
    expect(statusColors.dangerText).toBe('#d70015')
    expect(statusColors.neutralText).toBe('#6d6d72')
    expect(statusColors.infoText).toBe('#0e7fb8')
    expect(statusColors.purpleText).toBe('#8944ab')
    expect(statusColors.yellowText).toBe('#a07d00')
  })

  test('VC-T-03: 示例页不应出现英文枚举码或接口路径', async ({ page }) => {
    const demoPages = [
      '/demo/layout',
      '/demo/list',
      '/demo/form',
      '/demo/selectors',
      '/demo/files',
      '/demo/display',
    ]

    for (const path of demoPages) {
      await page.goto(path)
      await page.waitForLoadState('networkidle')

      const pageContent = await page.evaluate(() => document.body.innerText)

      expect(pageContent).not.toMatch(/\/admin-api\/ims\//)
      expect(pageContent).not.toMatch(/\b(PENDING|APPROVED|REJECTED)\b/)
      expect(pageContent).not.toMatch(/BR-\d{3}/)
      expect(pageContent).not.toMatch(/ADR-\d{3}/)
    }
  })

  test('VC-T-04: ESLint 禁止硬编码颜色和接口路径', async () => {
    const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
    const eslint = new ESLint({
      cwd: root,
      overrideConfigFile: path.join(root, 'eslint.config.js'),
    })
    const bad = `<script setup>
const roles = ['admin']
if (roles.includes('admin')) {
  const api = '/admin-api/ims/demo'
  void api
}
</script>`
    const badResult = await eslint.lintText(bad, { filePath: path.join(root, 'src/views/_vc_t04_probe.vue') })
    const badText = badResult.flatMap((item) => item.messages.map((message) => message.message)).join('\n')
    expect(badText).toMatch(/admin-api/)
    expect(badText).toMatch(/角色/)

    const clean = `<script setup>
const permCodes = ['ims:demo:order:query']
const ok = permCodes.includes('ims:demo:order:query')
void ok
</script>`
    const cleanResult = await eslint.lintText(clean, { filePath: path.join(root, 'src/views/_vc_t04_clean.vue') })
    const cleanText = cleanResult.flatMap((item) => item.messages.map((message) => message.message)).join('\n')
    expect(cleanText).not.toMatch(/admin-api/)
    expect(cleanText).not.toMatch(/角色名/)

    const styled = await stylelint.lint({
      code: '.probe{color:#123456}',
      codeFilename: 'probe.css',
      config: { rules: { 'color-no-hex': true } },
    })
    expect(styled.errored).toBe(true)
    expect(styled.results[0]?.warnings.map((warning) => warning.text).join('\n')).toMatch(/[Hh]ex|color/)

    const plain = await stylelint.lint({
      code: '.probe{color:var(--blue)}',
      codeFilename: 'plain.css',
      config: { rules: { 'color-no-hex': true } },
    })
    expect(plain.errored).toBe(false)
  })
})
