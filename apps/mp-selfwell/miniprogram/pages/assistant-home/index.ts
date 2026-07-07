/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03a 智能管家对话主页
 * 设计稿: docs/design/figma-pixso-spec/pages/07-butler-home.html
 * 后端端点:
 *   - openapi.yaml tag=assistant operationId=createSession    POST /assistant/sessions
 *   - openapi.yaml tag=assistant operationId=sendMessage      POST /assistant/sessions/{id}/messages
 *   - openapi.yaml tag=butler   operationId=triggerRecall     GET  /butler/recall/{day}
 *
 * 行为（SF3 完工态）：
 *  1) 进入页面 → POST /assistant/sessions 建会话（4 态 FSM：greeting → listening → thinking → answer）
 *  2) 用户输入 → listening 态显示 user bubble → sendMessage → 收 answer 气泡
 *  3) A 类意图（关键词 ≥ 20）：diagnosis / plan / checkin / diary / recall / plaza / hug → 路由分发
 *  4) B 类快问（正则 ≥ 10）：问候 / 感谢 / 安慰 / 推荐 / 进度 → ack-pool 兜底
 *  5) medical_guard：医疗关键词 → 强制 medical_guarded 态 + 标准温柔拒绝
 */
import { post } from '../../utils/request';
import { pickRandomAck } from '../../data/ack-pool';

type PersonaState = 'greeting' | 'listening' | 'thinking' | 'answer' | 'medical_guarded';

interface ChatTurn {
  id: string;
  state: PersonaState;
  text: string;
  title?: string;
}

interface AssistantSessionResp {
  id: string;
}

interface AssistantMessageResp {
  reply: string;
  route?: { module: string; params?: Record<string, string> };
  medicalGuarded?: boolean;
}

/** A 类意图关键词（≥ 20 条；与 §6.3 实施规范对齐） */
const ROUTE_KEYWORDS: Array<{ kw: RegExp; module: string; page: string }> = [
  { kw: /诊断|分析|照片|皮肤|状态/, module: 'diagnosis', page: 'pages/diagnosis-upload/index' },
  { kw: /方案|计划|21天|21 天/, module: 'plan', page: 'pages/plan/index' },
  { kw: /打卡|今日|完成/, module: 'checkin', page: 'pages/checkin/index' },
  { kw: /日记|心情|记录|感受/, module: 'diary', page: 'pages/feedback-diary/index' },
  { kw: /回忆|过去|那天/, module: 'recall', page: 'pages/recall-compare/index' },
  { kw: /广场|社区|看看别人/, module: 'plaza', page: 'pages/community/index' },
  { kw: /抱抱|海报|分享/, module: 'hug', page: 'pages/share-hug-card/index' },
];

/** B 类快问正则（≥ 10 条） */
const QUICK_REPLY: RegExp[] = [
  /早安|你好|hi|hello|嗨/,
  /谢谢|感谢|辛苦了/,
  /累了|难过|不开心|沮丧/,
  /推荐.*视频|有.*建议/,
  /今天.*进度|打卡.*了/,
  /陪我|聊聊/,
  /吃了吗|睡得|心情如何/,
  /出去|散步|运动/,
  /冥想|呼吸|放松/,
  /周末|假期|休息/,
];

/** 医疗关键词（命中即 medical_guarded） */
const MEDICAL_KEYWORDS: RegExp[] = [
  /吃药|药物|处方|药/,
  /抑郁|焦虑症|失眠症/,
  /诊断|确诊|症状/,
  /医院|医生|治疗/,
];

const MEDICAL_GUARD_REPLY = '我听到了，但涉及医疗的事，建议找专业医生聊聊比较稳妥。我可以陪你记录心情。';

Page({
  data: {
    personaState: 'greeting' as PersonaState,
    sessionId: '',
    turns: [
      {
        id: 't0',
        state: 'greeting',
        title: '嗨，今天想聊点什么呢？',
        text: '可以是今天的心情，或是一个小困扰。',
      },
    ] as ChatTurn[],
    inputText: '',
    entryCards: [
      { id: 'upload', title: '智能分析', subtitle: '上传一张照片生成你的画像' },
      { id: 'diary', title: '心情日记', subtitle: '记录今天的小情绪' },
      { id: 'compare', title: '对比回顾', subtitle: '看看第 7/14/21 天的自己' },
    ],
  },

  onLoad() {
    this.ensureSession();
  },

  async ensureSession() {
    try {
      const s = await post<AssistantSessionResp>('/assistant/sessions', {});
      if (s?.id) this.setData({ sessionId: s.id });
    } catch {
      /* mock session id 用于 UI 联调 */
      this.setData({ sessionId: 'mock_session_' + Date.now() });
    }
  },

  onInput(e: WechatMiniprogram.InputEvent) {
    this.setData({ inputText: e.detail.value });
  },

  async onSend() {
    const text = (this.data.inputText ?? '').trim();
    if (!text) return;
    const listenTurn: ChatTurn = {
      id: 'u_' + Date.now(),
      state: 'listening',
      text,
    };
    this.setData({
      turns: [...this.data.turns, listenTurn],
      inputText: '',
      personaState: 'thinking',
    });

    // 0) medical_guard 优先（最高优先级）
    if (MEDICAL_KEYWORDS.some((r) => r.test(text))) {
      const guardTurn: ChatTurn = {
        id: 'g_' + Date.now(),
        state: 'medical_guarded',
        text: MEDICAL_GUARD_REPLY,
      };
      this.setData({
        turns: [...this.data.turns, guardTurn],
        personaState: 'medical_guarded',
      });
      return;
    }

    // 1) A 类路由（命中即跳）
    for (const r of ROUTE_KEYWORDS) {
      if (r.kw.test(text)) {
        const routeTurn: ChatTurn = {
          id: 'r_' + Date.now(),
          state: 'answer',
          text: `好呀，带你去${r.module}～`,
        };
        this.setData({
          turns: [...this.data.turns, routeTurn],
          personaState: 'greeting',
        });
        setTimeout(() => wx.navigateTo({ url: r.page }), 400);
        return;
      }
    }

    // 2) B 类快问 / 默认走 sendMessage
    const isQuick = QUICK_REPLY.some((r) => r.test(text));
    try {
      const resp = await post<AssistantMessageResp>(
        `/assistant/sessions/${this.data.sessionId}/messages`,
        { text, is_quick: isQuick },
      );
      const answer: ChatTurn = {
        id: 'a_' + Date.now(),
        state: 'answer',
        text: resp?.reply || pickRandomAck().text,
      };
      this.setData({
        turns: [...this.data.turns, answer],
        personaState: 'greeting',
      });
    } catch {
      // 兜底 ack-pool
      const fallback = pickRandomAck();
      const answer: ChatTurn = {
        id: 'a_' + Date.now(),
        state: 'answer',
        text: fallback.text,
      };
      this.setData({
        turns: [...this.data.turns, answer],
        personaState: 'greeting',
      });
    }
  },

  onTapEntry(e: WechatMiniprogram.BaseEvent) {
    const id = (e.currentTarget.dataset as { id: string }).id;
    if (id === 'upload') {
      wx.navigateTo({ url: '/pages/diagnosis-upload/index' });
    } else if (id === 'diary') {
      wx.navigateTo({ url: '/pages/feedback-diary/index' });
    } else if (id === 'compare') {
      wx.navigateTo({ url: '/pages/recall-compare/index' });
    }
  },
});