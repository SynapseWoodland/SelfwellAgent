/**
 * 图片选择 + 上传组件
 * ──────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/04-butler-analyze-upload.html
 * 后端：openapi.yaml tag=uploads operationId=presignUpload + tag=diagnosis operationId=createDiagnosis
 *
 * 行为：
 *  - 点击触发 chooseSingleImage（自动压缩到 ≤ 1024px）
 *  - 输出 bind:select 事件（detail.picked = PickedImage）
 *  - 上传逻辑留给 page（SF2 接入）
 */
import { chooseSingleImage, PickedImage } from '../utils/picker';

Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 是否禁用 */
    disabled: {
      type: Boolean,
      value: false,
    },
    /** 已选图片预览（受控） */
    value: {
      type: String,
      value: '',
    },
    /** 按钮文字 */
    label: {
      type: String,
      value: '选图',
    },
  },

  data: {
    loading: false,
  },

  methods: {
    async onTap() {
      if (this.data.disabled || this.data.loading) return;
      this.setData({ loading: true });
      try {
        const picked: PickedImage = await chooseSingleImage();
        this.setData({ value: picked.path });
        this.triggerEvent('select', { picked });
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'chooseImage failed';
        wx.showToast({ title: msg, icon: 'none' });
      } finally {
        this.setData({ loading: false });
      }
    },
  },
});