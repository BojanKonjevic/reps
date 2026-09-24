
module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:svelte/recommended',
    'prettier',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: { ecmaVersion: 'latest', sourceType: 'module' },
  plugins: ['@typescript-eslint'],
  rules: {
    '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
    '@typescript-eslint/no-explicit-any': 'warn',
    'no-empty': ['error', { allowEmptyCatch: true }],
    // SSOT G10: the dashboard reads muscle list/colors/bands/thresholds from
    // snapshot.constants only (lib/vocab), never from constants.json.
    'no-restricted-imports': [
      'error',
      {
        paths: [
          {
            name: '../../constants.json',
            message: 'SSOT G10: read snapshot.constants via lib/vocab instead.',
          },
          {
            name: '../constants.json',
            message: 'SSOT G10: read snapshot.constants via lib/vocab instead.',
          },
        ],
        patterns: [
          {
            group: ['**/constants.json'],
            message: 'SSOT G10: read snapshot.constants via lib/vocab instead.',
          },
        ],
      },
    ],
    // SSOT G9: viewer-clock reads live only in lib/clock.ts (highlight-only)
    // and ISO parsing only in lib/format.ts. Calendar month-grid math uses
    // `new Date(y, m, 1)` on view state (layout, never "now") and carries a
    // local disable with this justification.
    'no-restricted-syntax': [
      'error',
      {
        selector:
          "CallExpression[callee.object.name='Date'][callee.property.name='now']",
        message: 'SSOT G9: clock reads live in lib/clock.ts only.',
      },
      {
        selector: "NewExpression[callee.name='Date'][arguments.length=0]",
        message: 'SSOT G9: clock reads live in lib/clock.ts only.',
      },
    ],
  },
  overrides: [
    {
      files: ['*.svelte'],
      parser: 'svelte-eslint-parser',
      parserOptions: { parser: '@typescript-eslint/parser' },
    },
    {
      // Allowed owners of Date construction.
      files: ['src/lib/clock.ts', 'src/lib/format.ts'],
      rules: { 'no-restricted-syntax': 'off' },
    },
    {
      // Calendar month-grid layout (not clock reads); sanctioned with reason.
      files: ['src/components/Calendar.svelte'],
      rules: {
        'no-restricted-syntax': [
          'error',
          {
            selector:
              "CallExpression[callee.object.name='Date'][callee.property.name='now']",
            message: 'SSOT G9: clock reads live in lib/clock.ts only.',
          },
          {
            selector: "NewExpression[callee.name='Date'][arguments.length=0]",
            message: 'SSOT G9: clock reads live in lib/clock.ts only.',
          },
        ],
      },
    },
    {
      files: ['src/__tests__/**', 'e2e/**'],
      rules: { 'no-restricted-syntax': 'off' },
    },
  ],
};
