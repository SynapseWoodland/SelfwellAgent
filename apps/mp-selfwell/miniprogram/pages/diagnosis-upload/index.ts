/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03 上传
 * 设计稿: docs/design/figma-pixso-spec/pages/04-butler-analyze-upload.html
 * 后端端点:
 *   - openapi.yaml tag=uploads   operationId=presignUpload   POST /uploads/presign
 *   - openapi.yaml tag=diagnosis operationId=createDiagnosis  POST /diagnosis?async=true
 *
 * 行为（PR-A2 + ADR-0004 异步 SSE 真链路）：
 *  1) 用户选择 1 张图（image-uploader 自动 ≤ 1024px 压缩）
 *  2) POST /uploads/presign 拿到 COS 直传 URL
 *  3) PUT 上传本地文件到 COS
 *  4) POST /diagnosis?async=true 创建异步诊断任务，立即拿到 { job_id, stream_url }
 *  5) 跳转 diagnosis-loading?id={job_id}&stream_url={...}，由 loading 页订阅 SSE
 *  6) 任何一步失败 → 降级 mock job_id（保证 UI 联调不被阻塞）
 *
 * 注：异步 SSE 是生产主路径；同步路径 POST /diagnosis 保留为 SDK / 老客户端降级，
 *     前端不再主动调用。详见 ADR-0004。
 */
import { PickedImage } from '../../utils/picker';
import { post } from '../../utils/request';

interface PresignResp {
  uploadUrl: string;
  objectKey: string;
  expiresIn: number;
}

interface DiagnosisResp {
  id: string;
  status: 'queued' | 'analyzing' | 'done' | 'failed';
}

/** 异步诊断任务响应（POST /diagnosis?async=true → HTTP 202） */
interface AsyncDiagnosisResp {
  job_id: string;
  status: 'queued' | 'analyzing' | 'done' | 'failed';
  stream_url: string;
}

function uploadToCos(uploadUrl: string, filePath: string): Promise<void> {
  return new Promise((resolve, reject) => {
    wx.uploadFile({
      url: uploadUrl,
      filePath,
      name: 'file',
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) resolve();
        else reject(new Error(`COS upload HTTP ${res.statusCode}`));
      },
      fail: (err) => reject(new Error(err.errMsg ?? 'cos upload fail')),
    });
  });
}

Page({
  data: {
    imagePath: '',
    uploading: false,
  },

  onLoad() {},

  onSelectImage(e: WechatMiniprogram.CustomEvent<{ picked: PickedImage }>) {
    this.setData({ imagePath: e.detail.picked.path });
  },

  async onStartAnalyze() {
    if (!this.data.imagePath) {
      wx.showToast({ title: '请先选择一张照片', icon: 'none' });
      return;
    }
    if (this.data.uploading) return;
    this.setData({ uploading: true });

    const gotoLoading = (jobId: string, streamUrl: string) => {
      const url =
        streamUrl.length > 0
          ? `pages/diagnosis-loading/index?id=${jobId}&stream_url=${encodeURIComponent(streamUrl)}`
          : `pages/diagnosis-loading/index?id=${jobId}&stream_url=${encodeURIComponent('/diagnosis/jobs/' + jobId + '/stream')}`;
      wx.redirectTo({ url });
    };

    try {
      // 1) 拿到 COS 直传地址
      const presign = await post<PresignResp>('/uploads/presign', {
        contentType: 'image/jpeg',
        purpose: 'diagnosis',
      }).catch(() => null);

      // 2) 直传 COS（如果 presign 成功）
      if (presign?.uploadUrl) {
        console.log('[diagnosis-upload] presign.objectKey =', presign.objectKey);
        console.log('[diagnosis-upload] presign.uploadUrl  =', presign.uploadUrl);
        try {
          await uploadToCos(presign.uploadUrl, this.data.imagePath);
          console.log('[diagnosis-upload] COS PUT ok, key =', presign.objectKey);
        } catch (e) {
          console.warn('[diagnosis-upload] COS upload fail, fallback mock', e);
        }
      } else {
        console.log('[diagnosis-upload] presign missing → fall through to mock objectKey');
      }

      // 3) 创建异步诊断任务（PR-A2 + ADR-0004：HTTP 202 + job_id + stream_url）
      const resp = await post<AsyncDiagnosisResp>('/diagnosis?async=true', {
        objectKey: presign?.objectKey ?? 'mock/' + Date.now() + '.jpg',
      }).catch(() => ({
        job_id: 'mock_' + Date.now(),
        status: 'queued' as const,
        stream_url: '',
      }));

      gotoLoading(resp.job_id, resp.stream_url);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '上传失败';
      wx.showToast({ title: msg, icon: 'none' });
      // 兜底：mock job_id + 默认 stream_url（前端永远不阻塞）
      setTimeout(
        () => gotoLoading('mock_' + Date.now(), '/diagnosis/jobs/mock_' + Date.now() + '/stream'),
        600,
      );
    } finally {
      this.setData({ uploading: false });
    }
  },
});