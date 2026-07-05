/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03a 智能管家对话主页
 * 设计稿: docs/design/figma-pixso-spec/pages/07-butler-home.html
 * 后端端点:
 *   - openapi.yaml tag=assistant operationId=assistantChat / getEntryCards
 *   - openapi.yaml tag=butler operationId=triggerRecall / listRecallHistory
 *
 * 占位：4 态 FSM（greeting → listening → thinking → answer）切换示例。
 */
type PersonaState = 'greeting' | 'listening' | 'thinking' | 'answer';

interface ChatTurn {
  id: string;
  state: PersonaState;
  text: string;
  title?: string;
}

Page({
  data: {
    personaState: 'greeting' as PersonaState,
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

  onInput(e: WechatMiniprogram.InputEvent) {
    this.setData({ inputText: e.detail.value });
  },

  onSend() {
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

    // SF3 接入：assistantChat → onAnswer
    setTimeout(() => {
      const answer: ChatTurn = {
        id: 'a_' + Date.now(),
        state: 'answer',
        text: '嗯，听到了。慢慢来，每天一点点就很好。',
      };
      this.setData({
        turns: [...this.data.turns, answer],
        personaState: 'greeting',
      });
    }, 1200);
  },

  onTapEntry(e: WechatMiniprogram.CustomEvent<{ id: string }>) {
    const id = e.detail?.id;
    if (id === 'upload') {
      wx.navigateTo({ url: '/miniprogram/pages/diagnosis-upload/index' });
    } else if (id === 'diary') {
      wx.navigateTo({ url: '/miniprogram/pages/feedback-diary/index' });
    } else if (id === 'compare') {
      wx.navigateTo({ url: '/miniprogram/pages/recall-compare/index' });
    }
  },
});