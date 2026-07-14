/**
 * profile-new 主页 静态契约锁
 * 1:1 复刻修复方案：上绿下白两段式布局
 * 验证：
 * - 两段式布局（.profile-green-zone / .profile-white-zone）
 * - Nav Bar 白底 + 黑标题 + 齿轮 ⚙️
 * - Hi 问候语 + 3 个 chips 在问候语下方
 * - 头像 🌿 在左侧
 * - 我的勋章（4 卡片：📷🎁⏰📖）
 * - 设置 4 项带 subtitle 副标题
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

function readProfileNewWxss(): string {
  return readFileSync(
    join(__dirname, '..', 'miniprogram', 'pages', 'profile-new', 'index.wxss'),
    'utf-8',
  );
}

describe('profile-new 主页（1:1 复刻修复：上绿下白两段式布局）', () => {

  // ── WXML 结构验证 ──

  it('用例 1: Nav Bar 白底 + 黑标题 + 齿轮按钮', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="profile-nav"');
    expect(wxml).toContain('class="profile-nav-title">我的</view>');
    expect(wxml).toContain('class="profile-nav-icon"');
    expect(wxml).toContain('⚙️');
    expect(wxml).toContain('bindtap="onOpenDrawer"');
  });

  it('用例 2: 上绿下白两段式布局', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="profile-green-zone"');
    expect(wxml).toContain('class="profile-white-zone"');
    // 绿底在前，白底在后
    const greenIdx = wxml.indexOf('class="profile-green-zone"');
    const whiteIdx = wxml.indexOf('class="profile-white-zone"');
    expect(greenIdx).toBeLessThan(whiteIdx);
  });

  it('用例 3: Hi 问候语 + 3 个 chips 在问候语下方', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="profile-greeting"');
    expect(wxml).toContain('Hi, {{nickname');
    expect(wxml).toContain('class="chips-row"');
    expect(wxml).toContain('class="chip"');
    // chips 在 greeting 下方（greeting 在 chips 前）
    const greetingIdx = wxml.indexOf('class="profile-greeting"');
    const chipsIdx = wxml.indexOf('class="chips-row"');
    expect(greetingIdx).toBeLessThan(chipsIdx);
  });

  it('用例 4: 头像 🌿 在左侧 + 年龄标签', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="profile-main-row"');
    expect(wxml).toContain('class="profile-avatar"');
    expect(wxml).toContain('🌿');
    expect(wxml).toContain('class="profile-tags"');
    expect(wxml).toContain('class="profile-tag-text"');
  });

  it('用例 5: 我的勋章区（标题 + 查看全部 + 4 卡片）', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="medals-section"');
    expect(wxml).toContain('class="section-header"');
    expect(wxml).toContain('我的勋章');
    expect(wxml).toContain('查看全部 ›');
    expect(wxml).toContain('class="medals-grid"');
    expect(wxml).toContain('class="medal-card"');
    // 4 个勋章 emoji
    expect(wxml).toContain('📷');
    expect(wxml).toContain('🎁');
    expect(wxml).toContain('⏰');
    expect(wxml).toContain('📖');
    expect(wxml).toContain('记录相册');
    expect(wxml).toContain('我的卡片');
    expect(wxml).toContain('我的时光');
    expect(wxml).toContain('自我档案');
  });

  it('用例 6: 设置 4 项带副标题 + 彩色方块图标', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('class="settings-section"');
    expect(wxml).toContain('class="settings-row"');
    expect(wxml).toContain('class="settings-content"');
    expect(wxml).toContain('class="settings-sub"');
    // 4 项设置 label
    expect(wxml).toContain('通知设置');
    expect(wxml).toContain('隐私政策');
    expect(wxml).toContain('关于自愈');
    expect(wxml).toContain('联系客服');
    // 4 项副标题
    expect(wxml).toContain('打卡提醒');
    expect(wxml).toContain('数据权限');
    expect(wxml).toContain('产品介绍');
    expect(wxml).toContain('在线反馈');
    // 4 个彩色方块背景
    expect(wxml).toMatch(/background:#FFCC80/); // 橙色-通知
    expect(wxml).toMatch(/background:#CE93D8/); // 紫色-隐私
    expect(wxml).toMatch(/background:#FFF9C4/); // 米黄-关于
    expect(wxml).toMatch(/background:#A5D6A7/); // 绿色-客服
  });

  it('用例 7: 设置项绑定 onTapSettings + data-id', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toMatch(/bindtap="onTapSettings"/);
    expect(wxml).toMatch(/data-id="notification"/);
    expect(wxml).toMatch(/data-id="privacy"/);
    expect(wxml).toMatch(/data-id="about"/);
    expect(wxml).toMatch(/data-id="contact"/);
  });

  it('用例 8: 抽屉 drawer-overlay', () => {
    const wxml = readProfileNewWxml();
    expect(wxml).toContain('<drawer-overlay');
    expect(wxml).toContain('visible="{{drawerVisible}}"');
    expect(wxml).toContain('bind:close="onCloseDrawer"');
    expect(wxml).toContain('wx:for="{{drawerItems}}"');
    expect(wxml).toContain('bindtap="onDrawerNav"');
  });

  // ── TS 数据逻辑验证 ──

  it('用例 9: ts 含新增字段 ageRange/crowd/level + 默认值', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('ageRange:');
    expect(ts).toContain('crowd:');
    expect(ts).toContain('level:');
    expect(ts).toMatch(/ageRange.*25-30 岁/);
    expect(ts).toMatch(/crowd.*久坐人群/);
    expect(ts).toMatch(/level.*自律 C/);
  });

  it('用例 10: ts settings 数组含 subtitle 副标题', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('settings:');
    expect(ts).toContain('subtitle:');
    expect(ts).toContain('打卡提醒');
    expect(ts).toContain('数据权限');
    expect(ts).toContain('产品介绍');
    expect(ts).toContain('在线反馈');
  });

  it('用例 11: ts 抽屉控制方法 + drawerItems（6 项）', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('drawerItems');
    expect(ts).toContain('onOpenDrawer');
    expect(ts).toContain('onCloseDrawer');
    expect(ts).toContain('onDrawerNav');
    for (const id of ['profile', 'album', 'notification', 'privacy', 'contact', 'about']) {
      expect(ts, `drawerItems 缺少 ${id}`).toContain(`id: '${id}'`);
    }
  });

  it('用例 12: ts onTapSettings 遍历 settings 数组路由分发', () => {
    const ts = readProfileNewTs();
    expect(ts).toMatch(/onTapSettings\s*\(\s*e/);
    expect(ts).toContain('settings.find');
    expect(ts).toContain('wx.navigateTo');
  });

  it('用例 13: ts fetchMe 填充 nickname + ageRange + crowd + level', () => {
    const ts = readProfileNewTs();
    expect(ts).toContain('fetchMe');
    expect(ts).toMatch(/\/users\/me/);
    expect(ts).toMatch(/nickname.*me\.nickname/);
    expect(ts).toMatch(/ageRange.*me\.age_range/);
    expect(ts).toMatch(/crowd.*me\.crowd/);
    expect(ts).toMatch(/level.*me\.level/);
  });

  // ── WXSS 样式验证 ──

  it('用例 14: wxss 两段式背景色（绿 + 白）', () => {
    const wxss = readProfileNewWxss();
    expect(wxss).toContain('.profile-green-zone');
    expect(wxss).toContain('background-color: #E8F5E9');
    expect(wxss).toContain('.profile-white-zone');
    expect(wxss).toContain('.profile-page');
    expect(wxss).toMatch(/profile-page[\s\S]*background-color:\s*#FFFFFF/);
  });

  it('用例 15: wxss Nav Bar 白底 + 黑标题', () => {
    const wxss = readProfileNewWxss();
    expect(wxss).toMatch(/\.profile-nav[\s\S]*background-color:\s*#FFFFFF/);
    expect(wxss).toMatch(/\.profile-nav-title[\s\S]*color:\s*#000000/);
    expect(wxss).toContain('.profile-nav-icon');
  });

  it('用例 16: wxss greeting + chips 样式', () => {
    const wxss = readProfileNewWxss();
    expect(wxss).toContain('.profile-greeting');
    expect(wxss).toMatch(/\.profile-greeting[\s\S]*font-size:\s*22px/);
    expect(wxss).toContain('.chips-row');
    expect(wxss).toContain('.chip');
    expect(wxss).toMatch(/\.chip[\s\S]*border-radius:\s*10px/);
  });

  it('用例 17: wxss 头像 🌿 圆形 + 尺寸', () => {
    const wxss = readProfileNewWxss();
    expect(wxss).toContain('.profile-avatar');
    expect(wxss).toMatch(/\.profile-avatar[\s\S]*border-radius:\s*28px/);
    expect(wxss).toMatch(/\.profile-avatar[\s\S]*background-color:\s*#FFFFFF/);
  });

  it('用例 18: wxss 勋章网格 + 卡片样式', () => {
    const wxss = readProfileNewWxss();
    expect(wxss).toContain('.medals-grid');
    expect(wxss).toMatch(/grid-template-columns:\s*repeat\(4,\s*1fr\)/);
    expect(wxss).toContain('.medal-card');
    expect(wxss).toMatch(/\.medal-card[\s\S]*border-radius:\s*12px/);
    expect(wxss).toContain('.medal-icon');
    expect(wxss).toContain('.medal-label');
  });

  it('用例 19: wxss 设置区独立行 + 分隔线 + 副标题', () => {
    const wxss = readProfileNewWxss();
    expect(wxss).toContain('.settings-section');
    expect(wxss).toContain('.settings-row');
    expect(wxss).toMatch(/\.settings-row[\s\S]*border-bottom:\s*1px solid #F0F0F0/);
    expect(wxss).toContain('.settings-content');
    expect(wxss).toContain('.settings-sub');
    expect(wxss).toMatch(/\.settings-sub[\s\S]*color:\s*#9E9E9E/);
    expect(wxss).toMatch(/\.settings-icon-wrap[\s\S]*border-radius:\s*8px/);
  });

});
