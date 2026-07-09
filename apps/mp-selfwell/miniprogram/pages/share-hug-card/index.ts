/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.9 P09 抱抱卡
 * 后端端点:
 *   - POST /share/hug-card      — 生成抱抱卡（返回 image_url + share_text）
 *   - GET  /share/hug-card/:day/template — 获取卡片模板元信息
 *
 * 行为：
 *   - onLoad 从 onLoad options 拿 day，未传则默认 7
 *   - 先拉模板元信息 → 再 POST 生成卡片
 *   - client-2d 路径：用 canvas 绘制，保存至相册
 *   - server 路径（兜底）：直接展示 image_url
 */
import { get, post, ApiException } from '../../utils/request';
import type { HugCardResp } from '../../types/api';
import { STORAGE_KEYS } from '../../utils/config';

interface CardMeta {
  badge: string;
  title: string;
  subtitle: string;
  caption: string;
}

interface PageData {
  day: number;
  card: CardMeta;
  cardReady: boolean;
  posterUrl: string;
  shareText: string;
  loading: boolean;
  saving: boolean;
  errMsg: string;
}

Page({
  data: {
    day: 7,
    card: { badge: '', title: '', subtitle: '', caption: '' },
    cardReady: false,
    posterUrl: '',
    shareText: '',
    loading: true,
    saving: false,
    errMsg: '',
  } as PageData,

  onLoad(options: { day?: string }) {
    const day = options?.day ? parseInt(options.day, 10) : 7;
    this.setData({ day });
    this._init(day);
  },

  async _init(day: number) {
    this.setData({ loading: true, errMsg: '' });

    try {
      // 1. 拉模板元信息
      const meta = await get<CardMeta>(`/share/hug-card/${day}/template`);
      const card: CardMeta = {
        badge: meta?.badge ?? `第 ${day} 天`,
        title: meta?.title ?? '你很棒',
        subtitle: meta?.subtitle ?? '每天都是新的开始',
        caption: meta?.caption ?? '继续加油 💪',
      };
      this.setData({ card });

      // 2. 生成卡片（client-2d 优先，失败兜底 server）
      try {
        await this._generateClient(card);
      } catch {
        // client 失败 → 走 server
        await this._generateServer(day);
      }
    } catch (e) {
      this.setData({ errMsg: e instanceof ApiException ? e.message : '加载失败' });
    } finally {
      this.setData({ loading: false });
    }
  },

  async _generateClient(card: CardMeta) {
    this.setData({ cardReady: true });

    // 延迟等 canvas 就绪
    await new Promise<void>((resolve) => setTimeout(resolve, 100));

    const ctx = wx.createCanvasContext('poster-canvas');
    const W = 750;
    const H = 1000;

    // 背景渐变（canvas 模拟 linear-gradient）
    const grd = ctx.createLinearGradient(0, 0, W, H);
    grd.addColorStop(0, '#F5E6D3');
    grd.addColorStop(1, '#F0D9C4');
    ctx.setFillStyle(grd);
    ctx.fillRect(0, 0, W, H);

    // badge
    ctx.setFillStyle('#4A5568');
    ctx.setFontSize(24);
    ctx.setTextAlign('center');
    ctx.fillText(card.badge, W / 2, 160);

    // title
    ctx.setFillStyle('#2D3436');
    ctx.setFontSize(56);
    ctx.setTextAlign('center');
    ctx.fillText(card.title, W / 2, 380);

    // subtitle
    ctx.setFillStyle('#4A5568');
    ctx.setFontSize(30);
    ctx.fillText(card.subtitle, W / 2, 460);

    // caption
    ctx.setFillStyle('#718096');
    ctx.setFontSize(24);
    ctx.fillText(card.caption, W / 2, 520);

    // emoji
    ctx.setFontSize(128);
    ctx.fillText('🤗', W / 2, 760);

    ctx.draw();

    // 导出图片
    await new Promise<void>((resolve, reject) => {
      wx.canvasToTempFilePath(
        {
          canvasId: 'poster-canvas',
          success: (res) => {
            this.setData({ posterUrl: res.tempFilePath, shareText: card.title });
            resolve();
          },
          fail: reject,
        },
        this,
      );
    });
  },

  async _generateServer(day: number) {
    const resp = await post<HugCardResp, { day: number; render_mode: string }>(
      '/share/hug-card',
      { day, render_mode: 'server' },
    );
    this.setData({
      posterUrl: resp?.image_url ?? '',
      shareText: resp?.share_text ?? '',
      cardReady: true,
    });
  },

  async onSaveToAlbum() {
    const { posterUrl } = this.data;
    if (!posterUrl) return;

    this.setData({ saving: true });
    try {
      await wx.saveImageToPhotosAlbum({ filePath: posterUrl });
      wx.showToast({ title: '保存成功', icon: 'success' });
    } catch {
      wx.showToast({ title: '保存失败，请重试', icon: 'none' });
    } finally {
      this.setData({ saving: false });
    }
  },

  onShareAppMessage() {
    const { day, shareText } = this.data;
    return {
      title: shareText || `第 ${day} 天的抱抱卡 🤗`,
      path: `/pages/share-hug-card/index?day=${day}`,
    };
  },
});
