/**
 * Sprint A Phase 0 · 微信小程序代码层 jest 配置。
 *
 * 真源：V4.1 V&V 子计划（用户提供决策 q6）。
 *
 * 设计要点：
 * 1. preset='ts-jest'：保留生产代码的 ESM/Stripe-style imports；不强制 babel 转译。
 * 2. testEnvironment='node'：jest 默认 jsdom 与小程序真实环境不符；
 *    微信 wx.request/wx.uploadFile 在 setup.ts 里 mock 成 Promise，回调驱动即可。
 *    若后续 spec 真需要 wx API 的 DOM-ish 行为，可加 testEnvironment='jsdom' per file。
 * 3. testMatch 只扫本目录 *.test.ts（避免误吞 production utils 与 vitest 套件）。
 * 4. setupFilesAfterEach 加载 setup.ts，把全局 mock 注入到每个测试。
 * 5. moduleNameMapper：把 wx 全局与 production utils 路径映射到 __mocks__/ 或真实路径。
 *
 * 与 apps/mp-selfwell/tests/（vitest）并存：
 * - vitest 套件：业务层 utils / page-level Vitest spec。
 * - 本 jest 套件：implementation-layer（Promise 链、SSE consumer、AbortController 链）。
 * - 两套 Runner 由各自根目录的 `npm test` 触发，互不干扰。
 */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  testMatch: ['**/*.test.ts'],
  setupFiles: ['<rootDir>/setup.ts'],
  moduleNameMapper: {
    // 把生产 utils/sse-http.ts 与 utils/request.ts 等路径透传（ts-jest 默认就这么做）
    // 但 wx.* 全局通过 setup.ts 全局 mock 处理
    '^@/(.*)$': '<rootDir>/../$1',
  },
  collectCoverageFrom: [
    '../utils/**/*.ts',
    '!../utils/**/*.d.ts',
    '!../utils/**/index.ts',
  ],
  coverageThreshold: {
    global: {
      // Phase 0 门槛 50%（vite+jest 双套件后逐步调升）
      lines: 50,
      statements: 50,
      functions: 50,
      branches: 40,
    },
  },
  testTimeout: 10000,
  verbose: true,
};
