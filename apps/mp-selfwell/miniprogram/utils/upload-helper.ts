/**
 * Selfwell · 上传 helper（diagnosis 1-3 张照片）
 * ──────────────────────────────────────────────
 * 真源：PRD V1.3 §3.2 / 后端 openapi.yaml tag=uploads + tag=diagnosis
 *
 * 行为（封装在 page 之外，供 page 直接调用）：
 *  1) 对每张 PickedImage 调 POST /uploads/presign 拿到 PUT 直传 URL
 *  2) wx.uploadFile PUT 上传本地文件到对象存储
 *  3) 收集 photos[] → POST /diagnosis
 *  4) 失败按 (1)→mock object_key / (2)→mock id 兜底，避免阻塞 UI 联调
 *
 * 约束（§17.16、§3.2.3）：
 *  - photos 1-3 张，每张必须带 body_part ∈ {face | head | shoulder_neck}
 *  - mock fallback 由 ?DEBUG=1 query 跳过（让 dev 自审能暴露真实 bug）
 *  - 不在 page 中直接写 wx.request / wx.uploadFile
 */

import { post } from './request';
import type { PickedImage } from './picker';
import type {
  CreateDiagnosisReq,
  DiagnosisReport,
  PhotoInput,
  PresignResp,
} from '../types/api';

/** 三类 body_part，与后端 _validate_photos 严格对齐 */
export type BodyPart = 'face' | 'head' | 'shoulder_neck';

/** PR-A4：后端 _validate_photos 接受 1..3 张；face 必含 */
export const MIN_PHOTOS = 1;
export const MAX_PHOTOS = 3;

export const BODY_PART_OPTIONS: ReadonlyArray<{ value: BodyPart; label: string }> = [
  { value: 'face', label: '面部' },
  { value: 'head', label: '头部' },
  { value: 'shoulder_neck', label: '肩颈' },
];

/** 单张待上传照片（UI 内部数据） */
export interface DiagnosisImageItem {
  /** 本地临时路径（来自 PickedImage） */
  path: string;
  /** 上传后服务端给的 object_key（上传成功后回填） */
  objectKey: string;
  /** 用户为该张图选的 body_part chip */
  bodyPart: BodyPart;
  /** 压缩后大小（byte） */
  sizeBytes: number;
  /** MIME（默认 image/jpeg） */
  contentType: string;
}

/** 单张上传结果 */
export interface UploadedPhoto {
  objectKey: string;
  bodyPart: BodyPart;
  format?: string;
  sizeBytes?: number;
}

/** 完整调用结果 */
export interface DiagnosisCreateResult {
  report: DiagnosisReport;
  /** 是否走 mock 兜底（DEBUG=1 时强制为 false） */
  isMock: boolean;
}

/** dev env 自动加 ?DEBUG=1 → 跳过 mock fallback，便于暴露真实 bug */
function isDebugMode(): boolean {
  // 小程序无 window.location，只能从 entryPageQuery 推断；wx.getLaunchOptionsSync 在 dev 工具下可读
  try {
    const launch = wx.getLaunchOptionsSync?.();
    const q = launch?.query ?? {};
    return q.DEBUG === '1' || q.debug === '1';
  } catch {
    return false;
  }
}

/** 用 wx.uploadFile 直传对象存储（PUT）。返回是否成功。 */
function putObject(uploadUrl: string, filePath: string, contentType: string): Promise<void> {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: uploadUrl,
      filePath,
      name: 'file',
      header: { 'Content-Type': contentType },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve();
        else reject(new Error(`object PUT HTTP ${res.statusCode}`));
      },
      fail: (err) => reject(new Error(err.errMsg ?? 'object PUT fail')),
    });
  });
}

/**
 * 给一张图片请求 presign + 上传；失败返回 mock object_key（除非 DEBUG=1）。
 */
export async function presignAndUploadOne(
  picked: PickedImage,
  bodyPart: BodyPart,
): Promise<UploadedPhoto> {
  const debug = isDebugMode();
  const contentType = 'image/jpeg';

  try {
    const presign = await post<PresignResp>('/uploads/presign', {
      contentType,
      purpose: 'diagnosis',
    });
    if (presign?.uploadUrl && presign?.objectKey) {
      await putObject(presign.uploadUrl, picked.path, contentType);
      return {
        objectKey: presign.objectKey,
        bodyPart,
        format: 'jpg',
        sizeBytes: picked.compressedSize,
      };
    }
    throw new Error('presign missing uploadUrl/objectKey');
  } catch (e) {
    if (debug) throw e;
    console.warn('[upload-helper] presign/upload fail, fallback mock', e);
    return {
      objectKey: `mock/diagnosis-${Date.now()}-${Math.random().toString(36).slice(2, 8)}.jpg`,
      bodyPart,
      format: 'jpg',
      sizeBytes: picked.compressedSize,
    };
  }
}

/**
 * 把若干本地 PickedImage + 已选 body_part 上传到对象存储，
 * 然后 POST /diagnosis 创建任务，拿到 report_id 跳 loading 页。
 *
 * photos 数组长度必须 ∈ [1, 3]；调用方负责校验（见 diagnosis-upload page）。
 */
export async function createDiagnosis(
  items: ReadonlyArray<DiagnosisImageItem>,
  complaint: string,
): Promise<DiagnosisCreateResult> {
  if (items.length < 1 || items.length > 3) {
    throw new Error(`photos count must be 1-3, got ${items.length}`);
  }

  const debug = isDebugMode();
  const photos: PhotoInput[] = items.map((it) => ({
    object_key: it.objectKey,
    body_part: it.bodyPart,
    format: 'jpg',
    size_bytes: it.sizeBytes,
  }));
  const payload: CreateDiagnosisReq = {
    photos,
    complaint: complaint.trim() || undefined,
  };

  try {
    const resp = await post<DiagnosisReport>('/diagnosis', payload);
    return { report: resp, isMock: false };
  } catch (e) {
    if (debug) throw e;
    console.warn('[upload-helper] createDiagnosis fail, fallback mock', e);
    return {
      report: {
        report_id: 'mock_' + Date.now(),
        summary:
          '我们暂时没能完整分析你的照片，你可以稍后在「回忆」页再看一次，或再上传一次。',
        directions: [
          {
            title: '深呼吸 3 分钟',
            description: '用鼻吸 4 秒，屏 4 秒，嘴呼 6 秒，重复 5 轮。',
          },
          {
            title: '肩颈缓慢画圈',
            description: '双肩向后→向上→向前→向下，各 8 次。',
          },
          {
            title: '写下今天的小事',
            description: '一句即可，重在把感受落到纸上。',
          },
        ],
        tags: ['平静', '自我观察', '呼吸', '放松', '可持续'],
      },
      isMock: true,
    };
  }
}

/**
 * PR-A4：批量上传 1-3 张照片（按 bodyPartSelector 给每张分配 body_part）。
 *
 * 与 ``presignAndUploadOne`` 的关系：本函数对每张图调一次 one（Promise.all 并发），
 * 输出数组顺序与 picked 输入顺序一致（便于调用方按槽位渲染）。
 *
 * ``可跳过部分`` 语义：如果 ``picked`` 为空数组，直接返回 ``[]``，由调用方决定是否允许 0 张提交。
 * 当前 04a 设计稿在「开始分析」按钮处要求至少 1 张 face；本函数不强制，由 caller 的 validatePhotoCount 兜底。
 *
 * @param picked            来自 wx.chooseMedia 的 PickedImage[]
 * @param bodyPartSelector  (idx) => BodyPart，caller 决定每张图的 body_part
 */
export async function presignAndUploadPhotos(
  picked: ReadonlyArray<PickedImage>,
  bodyPartSelector: (idx: number) => BodyPart,
): Promise<UploadedPhoto[]> {
  if (picked.length === 0) return [];
  const tasks = picked.map((p, idx) => presignAndUploadOne(p, bodyPartSelector(idx)));
  // Promise.all 顺序保持与输入 picked 一致；任一异常由 presignAndUploadOne 内部 mock 兜底
  return await Promise.all(tasks);
}

/** photos 数校验（按 SPEC-M2 §2.1：1-3 张） */
export function validatePhotoCount(items: ReadonlyArray<unknown>): {
  ok: boolean;
  message?: string;
} {
  const n = items.length;
  if (n < 1) return { ok: false, message: '请至少上传一张照片' };
  if (n > 3) return { ok: false, message: '最多上传 3 张照片' };
  return { ok: true };
}