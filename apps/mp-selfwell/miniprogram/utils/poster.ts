/**
 * Selfwell · 海报合成（canvas-2d v2）
 * ───────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/{12,13,14}-hug-card-day{7,14,21}.html
 * 真源：openapi.yaml tag=share operationId=generateSharePoster
 *
 * 行为（SF4 完工态）：
 *  - 客户端优先：走 wx.createSelectorQuery + Canvas 2d（v2）合成
 *  - 失败兜底：调用 /share/hug-card 拿服务端 PIL 图（详见 share-hug-card page）
 *  - 设计稿 750×1000 像素；输出 750×1000 jpg
 *  - 颜色禁用：禁止 #FF4D4F/#D32F2F/#007BFF；统一 mint/cream/peach
 *  - 文案禁用：禁止 "我坚持了" / "已坚持" 单独成段
 */

import { CLIENT_PLATFORM, STORAGE_KEYS } from './config';

export interface HugCardInput {
  day: 7 | 14 | 21;
  card: { title: string; subtitle: string; badge: string; caption: string };
  width: number;
  height: number;
}

interface CanvasContext2D {
  fillStyle: string;
  createLinearGradient(x0: number, y0: number, x1: number, y1: number): {
    addColorStop(offset: number, color: string): void;
  };
  fillRect(x: number, y: number, w: number, h: number): void;
  fillText(text: string, x: number, y: number, maxWidth?: number): void;
  font: string;
  textAlign: CanvasTextAlign;
  textBaseline: CanvasTextBaseline;
  beginPath(): void;
  moveTo(x: number, y: number): void;
  arc(x: number, y: number, r: number, startAngle: number, endAngle: number, anticlockwise?: boolean): void;
  closePath(): void;
  fill(): void;
  draw(): void;
}

interface Canvas2dInstance {
  canvas: WechatMiniprogram.Canvas;
  width: number;
  height: number;
}

const COLOR = {
  mint: '#A8C5B5',
  cream: '#F5E6D3',
  peach: '#F0D9C4',
  ink900: '#2D3436',
  ink700: '#4A5568',
  white: '#FFFFFF',
} as const;

/** 选 canvas node（page 端须有 <canvas type="2d" id="poster-canvas" /> 节点） */
function selectCanvasNode(id = 'poster-canvas'): Promise<Canvas2dInstance> {
  return new Promise((resolve, reject) => {
    const query = wx.createSelectorQuery();
    query
      .select(`#${id}`)
      .node()
      .exec((res) => {
        const node = res?.[0]?.node as Canvas2dInstance | undefined;
        if (!node) {
          reject(new Error(`canvas node #${id} not found in page`));
          return;
        }
        resolve(node);
      });
  });
}

/** 客户端 canvas-2d v2 合成抱抱卡，返回本地临时路径 */
export async function renderHugCardToCanvas(input: HugCardInput): Promise<string> {
  const { card, width, height, day } = input;
  const node = await selectCanvasNode('poster-canvas');
  const ctx = node.canvas.getContext('2d') as unknown as CanvasContext2D;
  if (!ctx) throw new Error('canvas 2d context unavailable');

  // 缩放 dpr 保持清晰
  const dpr = wx.getSystemInfoSync().pixelRatio || 2;
  node.canvas.width = width * dpr;
  node.canvas.height = height * dpr;
  ctx.fillStyle = COLOR.cream;
  ctx.fillRect(0, 0, width * dpr, height * dpr);

  // 渐变背景
  const grad = ctx.createLinearGradient(0, 0, width * dpr, height * dpr);
  grad.addColorStop(0, COLOR.cream);
  grad.addColorStop(1, COLOR.peach);
  ctx.fillStyle = grad as unknown as string;
  ctx.fillRect(0, 0, width * dpr, height * dpr);

  // badge
  ctx.fillStyle = COLOR.ink700;
  ctx.font = `500 ${28 * dpr}px "PingFang SC", sans-serif`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText(card.badge, (width * dpr) / 2, 96 * dpr);

  // 主标题
  ctx.fillStyle = COLOR.ink900;
  ctx.font = `600 ${64 * dpr}px "PingFang SC", sans-serif`;
  ctx.fillText(card.title, (width * dpr) / 2, 240 * dpr, width * dpr - 120 * dpr);

  // 副标题
  ctx.fillStyle = COLOR.ink700;
  ctx.font = `400 ${36 * dpr}px "PingFang SC", sans-serif`;
  ctx.fillText(card.subtitle, (width * dpr) / 2, 460 * dpr);

  // 心形 / emoji 圆
  ctx.beginPath();
  ctx.arc((width * dpr) / 2, 640 * dpr, 90 * dpr, 0, 2 * Math.PI);
  ctx.fillStyle = COLOR.mint;
  ctx.fill();

  ctx.fillStyle = COLOR.white;
  ctx.font = `600 ${80 * dpr}px "PingFang SC", sans-serif`;
  ctx.textBaseline = 'middle';
  ctx.fillText('🤗', (width * dpr) / 2, 642 * dpr);

  // caption
  ctx.fillStyle = COLOR.ink700;
  ctx.font = `400 ${28 * dpr}px "PingFang SC", sans-serif`;
  ctx.textBaseline = 'alphabetic';
  ctx.fillText(card.caption, (width * dpr) / 2, 880 * dpr);

  // day 数字（右下角水印式）
  ctx.fillStyle = COLOR.ink700;
  ctx.font = `500 ${24 * dpr}px "PingFang SC", sans-serif`;
  ctx.textAlign = 'right';
  ctx.fillText(`Day ${day}`, width * dpr - 48 * dpr, height * dpr - 48 * dpr);

  ctx.draw();

  return new Promise<string>((resolve, reject) => {
    wx.canvasToTempFilePath({
      canvas: node.canvas,
      fileType: 'jpg',
      quality: 0.9,
      success: (res) => resolve(res.tempFilePath),
      fail: (err) => reject(new Error(err.errMsg ?? 'canvasToTempFilePath fail')),
    });
  });
}

/** 保存图片到相册（含 traceparent 风格的 metadata 占位） */
export async function saveCanvasImageToAlbum(filePath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    wx.saveImageToPhotosAlbum({
      filePath,
      success: () => {
        // 记录推送 payload 风格的元数据（§17.17）
        try {
          const userId = wx.getStorageSync(STORAGE_KEYS.userId) || '';
          const meta = {
            client_platform: CLIENT_PLATFORM,
            user_id_pseudo: userId ? 'pseudo_' + userId.slice(-6) : 'pseudo_anon',
            saved_at: new Date().toISOString(),
            traceparent: '00-' + Date.now().toString(16).padStart(32, '0') + '-0000-01',
          };
          wx.setStorageSync('hug_card_meta', JSON.stringify(meta));
        } catch {
          /* ignore */
        }
        resolve();
      },
      fail: (err) => reject(new Error(err.errMsg ?? 'saveImageToPhotosAlbum fail')),
    });
  });
}
