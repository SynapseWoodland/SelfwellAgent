/**
 * Selfwell · 选图 + 压缩工具
 * ─────────────────────────
 * 约束（§1.5）：
 *  - 调用 wx.chooseImage
 *  - 客户端压缩到最长边 ≤ IMAGE_MAX_EDGE_PX（默认 1024px）
 *  - 输出可直接喂给 utils/request.ts 上传或送 /uploads/presign
 *
 * 注意：微信 canvas 2d 在 <2.9.0 基础库下类型为 CanvasContext；这里用 any 兼容，
 * 后续 SF1 接入 unionid 后再切类型。
 */

import { IMAGE_MAX_EDGE_PX } from './config';

export interface PickedImage {
  /** 微信本地临时路径（已压缩） */
  path: string;
  /** 原图大小（byte） */
  size: number;
  /** 压缩后大小（byte） */
  compressedSize: number;
  /** 压缩后宽高（px） */
  width: number;
  height: number;
}

/** 选图参数 */
export interface ChooseOptions {
  /** 最多选取张数 */
  count?: number;
  /** 来源：album | camera | 默认 both */
  sourceType?: Array<'album' | 'camera'>;
  /** 压缩目标边长（px），默认 1024 */
  maxEdge?: number;
}

/** 选图（多张，自动压缩） */
export async function chooseImages(opts: ChooseOptions = {}): Promise<PickedImage[]> {
  const chosen = await pickFromAlbum(opts.count ?? 9, opts.sourceType ?? ['album', 'camera']);
  const maxEdge = opts.maxEdge ?? IMAGE_MAX_EDGE_PX;
  const out: PickedImage[] = [];
  for (const path of chosen) {
    out.push(await compressOne(path, maxEdge));
  }
  return out;
}

/** 选图（单张，自动压缩） */
export async function chooseSingleImage(opts: ChooseOptions = {}): Promise<PickedImage> {
  const all = await chooseImages({ ...opts, count: 1 });
  return all[0];
}

function pickFromAlbum(
  count: number,
  sourceType: Array<'album' | 'camera'>,
): Promise<string[]> {
  return new Promise((resolve, reject) => {
    wx.chooseImage({
      count,
      sizeType: ['compressed'],
      sourceType,
      success: (res) => resolve(res.tempFilePaths),
      fail: (err) => reject(new Error(`chooseImage fail: ${err.errMsg ?? 'unknown'}`)),
    });
  });
}

interface ImgInfo {
  width: number;
  height: number;
  size?: number;
}

/** 获取图片信息 */
function getImageInfo(path: string): Promise<ImgInfo> {
  return new Promise((resolve, reject) => {
    wx.getImageInfo({
      src: path,
      success: (res) => resolve({ width: res.width, height: res.height, size: res.byteLength }),
      fail: (err) => reject(new Error(`getImageInfo fail: ${err.errMsg ?? 'unknown'}`)),
    });
  });
}

/**
 * 压缩到最长边 ≤ maxEdge。
 * 策略：
 *  - 长边已 ≤ maxEdge：直接返回原图信息
 *  - 否则使用 canvas 2d 缩放后导出为 jpg quality 80
 */
async function compressOne(path: string, maxEdge: number): Promise<PickedImage> {
  const info = await getImageInfo(path);
  const longEdge = Math.max(info.width, info.height);
  if (longEdge <= maxEdge) {
    return {
      path,
      size: info.size ?? 0,
      compressedSize: info.size ?? 0,
      width: info.width,
      height: info.height,
    };
  }

  const ratio = maxEdge / longEdge;
  const targetW = Math.round(info.width * ratio);
  const targetH = Math.round(info.height * ratio);

  // Canvas 2d 缩放（基础库 2.9.0+ 推荐；旧版回退 wx.canvasToTempFilePath）
  const filePath = await drawToTempFile(path, targetW, targetH);
  const out = await getImageInfo(filePath);
  return {
    path: filePath,
    size: info.size ?? 0,
    compressedSize: out.size ?? 0,
    width: out.width,
    height: out.height,
  };
}

function drawToTempFile(
  src: string,
  targetW: number,
  targetH: number,
): Promise<string> {
  return new Promise<string>((resolve, reject) => {
    // 走离屏 canvas：先创建 1x1 的 query 选择器获取 canvas
    // 真实实现见 page 调用方（image-uploader 组件）注入 canvasId
    // 这里给出一个"足够通用"的纯文件方案：直接走 wx.compressImage
    wx.compressImage({
      src,
      quality: 80,
      compressedWidth: targetW,
      compressedHeight: targetH,
      success: (res) => resolve(res.tempFilePath),
      fail: (err) =>
        reject(new Error(`compressImage fail: ${err.errMsg ?? 'unknown'}`)),
    });
  });
}