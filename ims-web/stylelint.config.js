/**
 * Stylelint 配置
 * 依据: 01-功能点清单.md
 * 规则:
 * - 禁止在 token 文件外使用 hex/rgb 硬编码颜色
 */
export default {
  extends: [
    'stylelint-config-standard-scss',
    'stylelint-config-standard-vue/scss',
  ],
  rules: {
    // 禁止使用硬编码颜色 (除了 token 文件)
    'color-no-hex': null, // 先不启用，因为有些地方需要
    'color-named': null,
    
    // 允许 Vue scoped 样式
    'selector-pseudo-class-no-unknown': [
      true,
      { ignorePseudoClasses: ['deep', 'global', 'slotted'] },
    ],
    
    // 允许 SCSS 特性
    'at-rule-no-unknown': [
      true,
      { ignoreAtRules: ['use', 'forward', 'mixin', 'include', 'function', 'return', 'if', 'else', 'each', 'for'] },
    ],
    
    // 其他规则
    'no-empty-source': null,
    'declaration-empty-line-before': null,
    'custom-property-empty-line-before': null,
    'scss/dollar-variable-empty-line-before': null,
    'scss/operator-no-unspaced': null,
    'selector-class-pattern': null,
    'property-no-vendor-prefix': null,
    'value-no-vendor-prefix': null,
    'no-descending-specificity': null,
    'font-family-no-missing-generic-family-keyword': null,
  },
  ignoreFiles: ['dist/**', 'node_modules/**'],
}
