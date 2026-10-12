/** VC-T-04：示例页硬编码颜色必须被检查命令拦住。 */
export default {
  customSyntax: 'postcss-html',
  rules: {
    'color-no-hex': true,
  },
}
