/**
 * 智能管家对话气泡（7 态 FSM）
 * ────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/04a-smart-analyze-dialog.html
 *        docs/design/figma-pixso-spec/pages/07-butler-home.html
 *
 * 7 个 persona_state（与 docs/spec/SPEC-M5-persona-chat.md §3.5 对齐）：
 *   - greeting        入口问候气泡（白色卡片）
 *   - listening       对话倾听气泡（左侧薄荷绿）
 *   - thinking        AI 思考气泡（带动态三点）
 *   - answer          AI 答复气泡（白色 + 卡片阴影）
 *   - medical_guarded 医疗温柔拒绝气泡（与 answer 相同视觉，加描边）
 *   - upload          PR-A4 A 场景：内嵌 3 槽位上传卡（通过 slot="upload-card" 注入）
 *   - analyzing       PR-A4 A 场景：内嵌进度卡（通过 slot="progress-card" 注入）
 *   - report          PR-A4 A 场景：内嵌报告卡 + 21 天 CTA（通过 slot="report-card" 注入）
 *
 * 注意：所有状态默认不对抗焦虑，颜色仅使用 mint/cream/peach/skyblue/lavender。
 */
type PersonaState =
  | 'greeting'
  | 'listening'
  | 'thinking'
  | 'answer'
  | 'medical_guarded'
  | 'upload'
  | 'analyzing'
  | 'report';

Component({
  options: {
    styleIsolation: 'isolated',
    multipleSlots: true,
  },

  properties: {
    /** 7 态 FSM 当前状态 */
    state: {
      type: String,
      value: 'greeting' as PersonaState,
    },
    /** 气泡正文（greeting/listening/answer/upload/analyzing/report 用） */
    text: {
      type: String,
      value: '',
    },
    /** 标题（greeting 用，可选） */
    title: {
      type: String,
      value: '',
    },
  },

  data: {
    /** typing 三点偏移（CSS animation 自动；这里仅保留 hooks） */
    dots: [0, 1, 2],
  },

  methods: {},
});