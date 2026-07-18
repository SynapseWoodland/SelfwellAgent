/**
 * profile-new 跳转入口契约锁
 * 真源：11-profile.png 截图
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

function readProfileNewWxml(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.wxml'),
    'utf-8',
  );
}

function readProfileNewTs(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.ts'),
    'utf-8',
  );
}

describe('profile-new 跳转入口（对齐 11-profile.png 原型）', () => {
  it('用例 1: 主页 4 项设置入口含 data-id', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toMatch(/data-id="profile"/);
    expect(wxml).toMatch(/data-id="album"/);
    expect(wxml).toMatch(/data-id="notification"/);
    expect(wxml).toMatch(/data-id="about"/);
  });

  it('用例 2: 用户档案 pagePath = /pages/profile-edit/index?mode=read', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/profile-edit/index?mode=read'");
  });

  it('用例 3: 我的时光 pagePath = /pages/album/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/album/index'");
    expect(ts).not.toContain("/pages/record-album/index'");
  });

  it('用例 4: 通知设置 pagePath = /pages/notification-settings/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/notification-settings/index'");
  });

  it('用例 5: 隐私政策 pagePath = /pages/privacy-policy/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/privacy-policy/index'");
  });

  it('用例 6: 联系客服 pagePath = /pages/contact/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/contact/index'");
  });

  it('用例 7: 关于自愈 pagePath = /pages/about/index', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain("'/pages/about/index'");
  });

  it('用例 8: 抽屉 drawerItems 6 项', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('drawerItems');
    for (const id of ['profile', 'album', 'notification', 'privacy', 'contact', 'about']) {
      expect(ts, `drawerItems 缺少 ${id}`).toContain(`id: '${id}'`);
    }
  });
});
