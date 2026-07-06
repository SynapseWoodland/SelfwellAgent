#!/usr/bin/env node
// Stage SF1 files only
'use strict';
const { execSync } = require('node:child_process');

const FILES = [
  'apps/mp-selfwell/miniprogram/pages/splash/index.ts',
  'apps/mp-selfwell/miniprogram/pages/splash/index.wxml',
  'apps/mp-selfwell/miniprogram/pages/login/index.ts',
  'apps/mp-selfwell/miniprogram/pages/login/index.wxml',
  'apps/mp-selfwell/miniprogram/pages/home/index.ts',
  'apps/mp-selfwell/miniprogram/pages/home/index.wxml',
  'apps/mp-selfwell/miniprogram/pages/checkin/index.ts',
  'apps/mp-selfwell/miniprogram/pages/checkin/index.wxml',
  'apps/mp-selfwell/miniprogram/pages/checkin/index.wxss',
  'apps/mp-selfwell/miniprogram/pages/checkin/index.json',
  'apps/mp-selfwell/miniprogram/utils/config.ts',
  'apps/mp-selfwell/miniprogram/utils/request.js',
  'apps/mp-selfwell/miniprogram/utils/error-code.ts',
  'apps/mp-selfwell/tests/sf1-pages.test.js',
  'apps/mp-selfwell/tests/sf1/splash-screenshot.test.js',
  'apps/mp-selfwell/tests/sf1/login-screenshot.test.js',
  'apps/mp-selfwell/tests/sf1/home-screenshot.test.js',
  'apps/mp-selfwell/tests/sf1/checkin-screenshot.test.js',
  'apps/mp-selfwell/tests/check-forbidden-colors.js',
  'apps/mp-selfwell/tests/package.json',
  'apps/mp-selfwell/README.md',
  'apps/mp-selfwell/docs/sf1-delivery.md',
];

for (const f of FILES) {
  try {
    execSync(`git add "${f}"`, { stdio: 'inherit' });
    console.log('STAGED', f);
  } catch (e) {
    console.log('SKIP (not modified)', f);
  }
}
