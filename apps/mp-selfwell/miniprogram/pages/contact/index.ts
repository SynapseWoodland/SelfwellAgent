/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P22 联系客服（V2 我的 Tab 子页）
 *
 * PR-5 · 联系客服子页（不带 tabBar）
 * ─────────────────────────────────────────────────────────────────
 * - 联系邮箱（点击复制）
 * - 客服微信二维码占位（assets/images/qrcode-placeholder.png；后续 PR 替换为真实二维码）
 * - FAQ 列表（写死 4 条常见问题；后端 GET /support/faq 已在 PR-2 落地，本页暂用静态避免冷启动）
 */

interface FaqItem {
  q: string;
  a: string;
}

interface ContactData {
  email: string;
  wechatId: string;
  workingHours: string;
  faqs: FaqItem[];
  expandedIndex: number;
}

const CONTACT_EMAIL = 'selfwell@example.com';
const WECHAT_ID = 'selfwell_helper';

const FAQS: FaqItem[] = [
  {
    q: '如何修改档案？',
    a: '进入「我的 → 用户档案 → 编辑」即可修改 6 字段，保存后立即生效并同步到后端。',
  },
  {
    q: '打卡漏了一天怎么办？',
    a: '打卡窗口期内（最近 3 天）可补卡；超出窗口则无法补打卡，会影响连续天数。',
  },
  {
    q: '21 天方案可以重新生成吗？',
    a: '可以在「智能管家」发起新的诊断流程；新方案会替换当前方案，但保留历史数据。',
  },
  {
    q: '如何注销账号？',
    a: '进入「我的 → 隐私政策 → 注销账号」提交申请，15 天冷静期内可撤回。',
  },
];

Page<ContactData>({
  data: {
    email: CONTACT_EMAIL,
    wechatId: WECHAT_ID,
    workingHours: '工作日 9:00-18:00',
    faqs: FAQS,
    expandedIndex: -1,
  },

  onCopyEmail() {
    wx.setClipboardData({
      data: this.data.email,
      success: () => wx.showToast({ title: '邮箱已复制', icon: 'success' }),
    });
  },

  onCopyWechat() {
    wx.setClipboardData({
      data: this.data.wechatId,
      success: () => wx.showToast({ title: '微信号已复制', icon: 'success' }),
    });
  },

  onTapFaq(e: WechatMiniprogram.BaseEvent) {
    const index = (e.currentTarget.dataset as { index?: number }).index ?? -1;
    const next = this.data.expandedIndex === index ? -1 : index;
    this.setData({ expandedIndex: next });
  },
});