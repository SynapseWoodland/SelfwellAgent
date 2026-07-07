/**
 * 今日小动作卡片（首页 P02 列表项）
 * ────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/03-home.html（task-card / task-item）
 * Token：color/primary/mint=#A8C5B5
 *
 * 事件：
 *  - bind:toggle  勾选状态变更（detail.done = boolean）
 */
Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 任务 ID */
    id: {
      type: String,
      value: '',
    },
    /** 任务名称 */
    title: {
      type: String,
      value: '',
    },
    /** 副标题 / 描述 / 视频时长 */
    subtitle: {
      type: String,
      value: '',
    },
    /** 是否已完成 */
    done: {
      type: Boolean,
      value: false,
    },
    /** 是否禁用（运营灰态） */
    disabled: {
      type: Boolean,
      value: false,
    },
  },

  data: {},

  methods: {
    onTap() {
      if (this.data.disabled) return;
      const next = !this.data.done;
      this.setData({ done: next });
      this.triggerEvent('toggle', { id: this.data.id, done: next });
    },
  },
});