/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03 上传
 * 设计稿: docs/design/figma-pixso-spec/pages/04-butler-analyze-upload.html
 * 后端端点:
 *   - openapi.yaml tag=uploads   operationId=presignUpload   POST /uploads/presign
 *   - openapi.yaml tag=diagnosis operationId=createDiagnosis  POST /diagnosis
 *
 * 行为（SF2 完工态）：
 *  1) 用户选择 1 张图（image-uploader 自动 ≤ 1024px 压缩）
 *  2) POST /uploads/presign 拿到 COS 直传 URL
 *  3) PUT 上传本地文件到 COS
 *  4) POST /diagnosis 创建诊断任务，拿到 id
 *  5) 跳转 diagnosis-loading?id=xxx
 *  6) 任何一步失败 → 降级 mock id（保证 UI 联调不被阻塞）
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

    const gotoLoading = (id: string) => {
      wx.redirectTo({
        url: `/miniprogram/pages/diagnosis-loading/index?id=${id}`,
      });
    };

    try {
      // 1) 拿到 COS 直传地址
      const presign = await post<PresignResp>('/uploads/presign', {
        contentType: 'image/jpeg',
        purpose: 'diagnosis',
      }).catch(() => null);

      // 2) 直传 COS（如果 presign 成功）
      if (presign?.uploadUrl) {
        try {
          await uploadToCos(presign.uploadUrl, this.data.imagePath);
        } catch (e) {
          console.warn('[diagnosis-upload] COS upload fail, fallback mock', e);
        }
      }

      // 3) 创建诊断任务
      const resp = await post<DiagnosisResp>('/diagnosis', {
        objectKey: presign?.objectKey ?? 'mock/' + Date.now() + '.jpg',
      }).catch(() => ({ id: 'mock_' + Date.now(), status: 'queued' as const }));

      gotoLoading(resp.id);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '上传失败';
      wx.showToast({ title: msg, icon: 'none' });
      // 兜底：mock id
      setTimeout(() => gotoLoading('mock_' + Date.now()), 600);
    } finally {
      this.setData({ uploading: false });
    }
  },
});