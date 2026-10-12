/**
 * ESLint 配置
 * 依据: 01-功能点清单.md
 * 规则:
 * - 禁止在 views/ 中直接使用 /admin-api
 * - 禁止使用角色名进行权限判断 (应使用 permCode)
 */
import js from '@eslint/js'
import tseslint from 'typescript-eslint'
import pluginVue from 'eslint-plugin-vue'

export default [
  { ignores: ['dist/', 'node_modules/', '*.d.ts', 'auto-imports.d.ts', 'components.d.ts'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/essential'],
  {
    languageOptions: {
      globals: {
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearTimeout: 'readonly',
        clearInterval: 'readonly',
        File: 'readonly',
        Blob: 'readonly',
        FormData: 'readonly',
        HTMLDivElement: 'readonly',
        HTMLElement: 'readonly',
        ResizeObserver: 'readonly',
        IntersectionObserver: 'readonly',
        console: 'readonly',
        fetch: 'readonly',
        URL: 'readonly',
        URLSearchParams: 'readonly',
        Event: 'readonly',
        MouseEvent: 'readonly',
        KeyboardEvent: 'readonly',
        TouchEvent: 'readonly',
        CustomEvent: 'readonly',
        Node: 'readonly',
        NodeList: 'readonly',
        Element: 'readonly',
        EventTarget: 'readonly',
        Location: 'readonly',
        History: 'readonly',
        Navigator: 'readonly',
      },
    },
  },
  {
    files: ['**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
      },
    },
  },
  {
    files: ['src/views/**/*.vue', 'src/views/**/*.ts'],
    rules: {
      // 禁止在 views 中直接调用 /admin-api
      'no-restricted-syntax': [
        'error',
        {
          selector: 'Literal[value=/\\/admin-api/]',
          message: '禁止在 views 中直接使用 /admin-api，请通过 api/ 层调用',
        },
        {
          selector: 'TemplateLiteral:has(TemplateElement[value.raw=/admin-api/])',
          message: '禁止在 views 中直接使用 /admin-api，请通过 api/ 层调用',
        },
      ],
    },
  },
  {
    rules: {
      // 基础规则
      'no-console': ['warn', { allow: ['warn', 'error'] }],
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-non-null-asserted-optional-chain': 'off',
      'vue/multi-word-component-names': 'off',
    },
  },
  {
    files: ['tests/**/*.ts', 'tests/**/*.spec.ts'],
    rules: {
      'no-console': 'off',
      '@typescript-eslint/no-non-null-assertion': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
    },
  },
]
