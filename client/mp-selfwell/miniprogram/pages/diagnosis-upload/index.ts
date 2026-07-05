/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P03 上传
 * 设计稿: docs/design/figma-pixso-spec/pages/04-butler-analyze-upload.html
 * 后端端点:
 *   - openapi.yaml tag=uploads operationId=presignUpload（SF2 接入）
 *   - openapi.yaml tag=diagnosis operationId=createDiagnosis
 *
 * 行为：上传 1 张照片（image-uploader 组件），点击开始分析 → 跳转 loading 页。
 */
import { PickedImage } from '../../utils/picker';

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

    try {
      // SF2 接入：先 /uploads/presign 拿到 COS URL → PUT 上传 → /diagnosis 创建
      // 本 Sprint 仅占位：直接跳 loading
      const diagnosisId = 'mock_' + Date.now();
      setTimeout(() => {
        wx.redirectTo({
          url: `/miniprogram/pages/diagnosis-loading/index?id=${diagnosisId}`,
        });
      }, 400);
    } catch (e) {
      const msg = e instanceof Error ? e.message : '上传失败';
      wx.showToast({ title: msg, icon: 'none' });
    } finally {
      this.setData({ uploading: false });
    }
  },
});