/**
 * upload-card 组件（智能分析上传卡）
 * ────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/04a-smart-analyze-dialog.html
 * 用途：在 persona-bubble 的 slot="upload-card" 中渲染 3 槽位 + 4 chips + 提交按钮。
 *
 * Props（与 assistant-home 的 ChatTurn.attachment.kind === 'upload_card' 1:1 对齐）：
 *  - title:        顶部标题
 *  - slots:        [{label, filled}]  3 个虚线占位槽
 *  - ageRanges:    [{value, label, selected}]  4 个年龄段 chip
 *  - submitText:   提交按钮文案（可选，默认"上传，开始分析"）
 *
 * Events（冒号命名，父组件直接 bind）：
 *  - slotTap    { index }     点击某个虚线槽
 *  - ageChipTap { age }       选中某个年龄段
 *  - startTap                 点击"上传，开始分析"
 *
 * 注意：所有写操作（更新 slots.filled / ageRanges.selected）由父组件
 * （assistant-home）负责，组件只负责 dispatch 事件 + 渲染。
 */

interface UploadSlot {
  label: string;
  filled: boolean;
  /** filled=true 时槽位要显示的本地图片 URL（来自 wx.chooseMedia tempFilePath） */
  filledUrl?: string;
}

interface AgeRange {
  value: string;
  label: string;
  selected: boolean;
}

Component({
  options: {
    styleIsolation: 'apply-shared',
    multipleSlots: false,
  },

  properties: {
    title: {
      type: String,
      value: '上传照片生成你的画像',
    },
    slots: {
      type: Array,
      value: [] as UploadSlot[],
    },
    ageRanges: {
      type: Array,
      value: [] as AgeRange[],
    },
    submitText: {
      type: String,
      value: '',
    },
  },

  data: {},

  methods: {
    onSlotTap(e: WechatMiniprogram.BaseEvent) {
      const idx = Number((e.currentTarget.dataset as { idx: number }).idx);
      // 业务交互：点击槽位 → 弹文件选择器 → 选完图后回传 tempFilePath
      // 父组件负责"标 filled=true"，组件只做"dispatch 选图事件 + 选图调用"
      // 这里直接调 wx.chooseMedia 是为了"点一下就弹窗"——满足"整张上传卡点了没反应"修复
      const triggerFilled = (tempFilePath?: string) => {
        this.triggerEvent('slotTap', { index: idx, tempFilePath }, { bubbles: true, composed: true });
      };
      // 兼容旧调用方：如果全局 wx.chooseMedia 不可用（基础库 < 2.10.0），降级 chooseImage
      const choose = (wx as WechatMiniprogram.Wx & { chooseMedia?: typeof wx.chooseImage }).chooseMedia
        ? (wx as WechatMiniprogram.Wx & { chooseMedia: (opts: WechatMiniprogram.ChooseMediaOption) => void }).chooseMedia({
            count: 1,
            mediaType: ['image'],
            sourceType: ['album', 'camera'],
            sizeType: ['compressed'],
            success: (res: WechatMiniprogram.ChooseMediaSuccessCallbackResult) => {
              const p = res.tempFiles?.[0]?.tempFilePath;
              triggerFilled(p);
            },
            fail: () => {
              // 用户取消选择器时：静默忽略，不触发 slotTap 事件
              // 这样 assistant-home 就不会把槽位错误地标记为 filled=true
            },
          })
        : wx.chooseImage({
            count: 1,
            sizeType: ['compressed'],
            sourceType: ['album', 'camera'],
            success: (res: WechatMiniprogram.ChooseImageSuccessCallbackResult) => {
              const p = res.tempFilePaths?.[0];
              triggerFilled(p);
            },
            fail: () => {
              // 用户取消选择器时：静默忽略，不触发 slotTap 事件
            },
          });
      void choose;
    },

    onAgeChipTap(e: WechatMiniprogram.BaseEvent) {
      const age = (e.currentTarget.dataset as { value: string }).value;
      this.triggerEvent('ageChipTap', { age }, { bubbles: true, composed: true });
    },

    onStartTap() {
      this.triggerEvent('startTap', {}, { bubbles: true, composed: true });
    },
  },
});