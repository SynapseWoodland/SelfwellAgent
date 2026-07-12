/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.7 P20 隐私政策（V2 我的 Tab 子页）
 *
 * PR-5 · 隐私政策子页（不带 tabBar）
 * ─────────────────────────────────────────────────────────────────
 * - 静态 markdown 渲染（不调后端；内容写死，方便审计）
 * - 顶部版本号 + 生效时间
 * - 6 段：信息收集 / 用途 / 存储 / 共享 / 用户权利 / 注销
 */

interface PolicySection {
  title: string;
  body: string;
}

interface PrivacyPolicyData {
  version: string;
  effectiveAt: string;
  sections: PolicySection[];
}

const POLICY_VERSION = 'v1.0';
const POLICY_EFFECTIVE_AT = '2026-07-12';

const POLICY_SECTIONS: PolicySection[] = [
  {
    title: '1. 我们收集的信息',
    body:
      '我们仅收集你主动提交的内容：账号昵称 / 头像、问卷 6 字段（年龄段、久坐时长、重点关注部位、干预强度、偏好时段、肤质）、诊断照片、每日打卡、心得日记、对话记录。本应用不收集通讯录、位置（除你明确开启的健身房定位）、设备唯一标识以外的信息。',
  },
  {
    title: '2. 我们如何使用这些信息',
    body:
      '信息仅用于：生成你的 21 天自愈方案、推送打卡提醒、提供智能管家对话流、展示 21 天小档案与时光相册。我们不会用于广告投放或第三方商业化。',
  },
  {
    title: '3. 存储与加密',
    body:
      '所有数据存储于境内合规云服务（MinIO / PostgreSQL），诊断照片传输与存储使用服务端加密。日志保留 90 天，用户可见的 21 天小档案聚合数据仅本人可读。',
  },
  {
    title: '4. 共享与披露',
    body:
      '我们不向第三方出售或共享你的个人数据。法律法规要求或紧急安全事件除外。',
  },
  {
    title: '5. 你的权利',
    body:
      '你可以随时在「我的 → 隐私政策」导出个人数据（异步生成下载链接）或申请注销账号（15 天冷静期，冷静期内可撤回）。',
  },
  {
    title: '6. 注销与冷静期',
    body:
      '申请注销后，账号进入 15 天冷静期，期间登录将自动恢复；冷静期满后不可逆地删除账号与全部关联数据。',
  },
];

Page<PrivacyPolicyData>({
  data: {
    version: POLICY_VERSION,
    effectiveAt: POLICY_EFFECTIVE_AT,
    sections: POLICY_SECTIONS,
  },

  onShareAppMessage() {
    return {
      title: 'Selfwell 自愈 · 隐私政策',
      path: '/pages/privacy-policy/index',
    };
  },
});