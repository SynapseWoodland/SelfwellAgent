/**
 * 智能管家对话气泡（4 态 FSM）
 * ────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/07-butler-home.html
 *        docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
 *        docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
 *
 * 4 个 persona_state（与 openapi.yaml 中 feedback/assistant state 对齐）：
 *   - greeting   入口问候气泡（白色卡片）
 *   - listening  对话倾听气泡（左侧薄荷绿）
 *   - thinking   AI 思考气泡（带动态三点）
 *   - answer     AI 答复气泡（白色 + 卡片阴影）
 *
 * 注意：所有状态默认不对抗焦虑，颜色仅使用 mint/cream/peach/skyblue/lavender。
 */
type PersonaState = 'greeting' | 'listening' | 'thinking' | 'answer';

Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 4 态 FSM 当前状态 */
    state: {
      type: String,
      value: 'greeting' as PersonaState,
    },
    /** 气泡正文（greeting/listening/answer 用） */
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