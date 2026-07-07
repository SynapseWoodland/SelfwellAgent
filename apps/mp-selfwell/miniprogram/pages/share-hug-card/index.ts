/**
 * IA-REF: docs/design/ia-and-wireframe.md §13 M10 抱抱卡
 * 设计稿:
 *   - docs/design/figma-pixso-spec/pages/12-hug-card-day7.html
 *   - docs/design/figma-pixso-spec/pages/13-hug-card-day14.html
 *   - docs/design/figma-pixso-spec/pages/14-hug-card-day21.html
 * 后端端点: openapi.yaml tag=share operationId=generateSharePoster POST /share/hug-card
 *
 * 行为（SF4 完工态）：
 *  - onLoad 解析 ?day=7|14|21 → 渲染对应卡片
 *  - 点击"保存到相册" → utils/poster.ts 走 canvas-2d v2 客户端合成
 *    失败时调 /share/hug-card?day=N 拿服务端 PIL 合成图兜底
 *  - 共享走 open-type="share" + onShareAppMessage
 *  - 颜色禁用：禁止使用 #FF4D4F/#D32F2F/#007BFF；统一 mint/cream/peach 渐变
 *  - 文案禁用：禁止 "坚持" 单独成段；改用 "和你走过的 N 天" / "你在这里"
 */
import { post } from '../../utils/request';
import { renderHugCardToCanvas, saveCanvasImageToAlbum } from '../../utils/poster';

type Day = 7 | 14 | 21;

interface Card {
  title: string;
  subtitle: string;
  badge: string;
  caption: string;
}

const CARDS: Record<Day, Card> = {
  7: {
    title: '第一周，慢慢来',
    subtitle: '你已经在这里了',
    badge: 'Day 7',
    caption: '和你走过的 7 天',
  },
  14: {
    title: '两周，节奏稳了',
    subtitle: '你比自己想象的更稳',
    badge: 'Day 14',
    caption: '和你走过的 14 天',
  },
  21: {
    title: '21 天，仪式达成',
    subtitle: '成为更温柔的自己',
    badge: 'Day 21',
    caption: '和你走过的 21 天',
  },
};

interface HugCardResp {
  /** 后端 share_router 返回 url（不是 imageUrl），与 backend/app/api/routers/business_v1.py POST /share/hug-card 对齐 */
  url?: string;
  imageUrl?: string; // 兼容
  day: Day;
  generatedAt?: string;
  template?: string;
  width?: number;
  height?: number;
}

Page({
  data: {
    day: 7 as Day,
    card: CARDS[7],
    posterUrl: '',
    saving: false,
  },

  onLoad(query: Record<string, string | undefined>) {
    const raw = Number(query?.day ?? 7);
    const day = (raw === 14 ? 14 : raw === 21 ? 21 : 7) as Day;
    this.setData({ day, card: CARDS[day] });
  },

  /** 客户端 canvas 合成（基础库 2.9.0+ canvas-2d v2） */
  async onSaveToAlbum() {
    if (this.data.saving) return;
    this.setData({ saving: true });
    try {
      const localPath = await renderHugCardToCanvas({
        day: this.data.day,
        card: this.data.card,
        width: 750,
        height: 1000,
      });
      await saveCanvasImageToAlbum(localPath);
      wx.showToast({ title: '已保存到相册', icon: 'success' });
    } catch (e) {
      console.warn('[hug-card] client canvas fail, fallback server', e);
      await this.fallbackServerImage();
    } finally {
      this.setData({ saving: false });
    }
  },

  /** 服务端兜底（/share/hug-card PIL 合成） */
  async fallbackServerImage() {
    try {
      const resp = await post<HugCardResp>('/share/hug-card', { day: this.data.day });
      const url = resp?.url || resp?.imageUrl;
      if (url) {
        this.setData({ posterUrl: url });
        wx.showToast({ title: '已生成服务器图，请长按保存', icon: 'none' });
      } else {
        wx.showToast({ title: '生成失败，请稍后再试', icon: 'none' });
      }
    } catch {
      wx.showToast({ title: '网络异常，请稍后再试', icon: 'none' });
    }
  },

  onShareAppMessage() {
    return {
      title: this.data.card.title,
      path: `pages/share-hug-card/index?day=${this.data.day}`,
    };
  },
});