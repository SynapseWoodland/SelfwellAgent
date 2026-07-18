/**
 * 今日小动作卡片（首页 P02 列表项）
 * ────────────────────────────────
 * 设计稿：docs/design/figma-pixso-spec/pages/03-home.html（task-card / task-item）
 * Token：color/primary/mint=#A8C5B5
 *
 * 事件：
 *  - bind:toggle  勾选状态变更（detail = { id, done }）
 *  - bind:tap     点击查看详情（detail = { id, videoUrl }）
 *
 * v2 重构：打卡与视频解耦
 *  - 勾选框点击 → 触发 toggle 事件（打卡）
 *  - 卡片内容点击 → 触发 tap 事件（跳转视频详情）
 */

Component({
  options: {
    styleIsolation: 'apply-shared',
  },

  properties: {
    /** 任务 ID（用 taskId 避免和 DOM id 属性冲突） */
    taskId: {
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
    /** 视频 URL（用于跳转详情页） */
    videoUrl: {
      type: String,
      value: '',
    },
    /** 右侧操作文字：已完成="回看"，未完成="开始" */
    actionText: {
      type: String,
      value: '',
    },
  },

  data: {},

  methods: {
  /**
   * 勾选框点击 → 触发 toggle 事件（打卡）
   */
  onCheckboxTap() {
    console.log('[task-card] onCheckboxTap called', { id: this.data.taskId, done: this.data.done });
    if (this.data.disabled) return;
    const next = !this.data.done;
    this.setData({ done: next });
    this.triggerEvent('toggle', { id: this.data.taskId, done: next });
  },

  /**
   * 卡片内容点击 → 触发 tap 事件（跳转视频详情）
   */
  onCardTap() {
    console.log('[task-card] onCardTap called', {
      id: this.data.taskId,
      videoUrl: this.data.videoUrl,
      disabled: this.data.disabled,
    });
    if (this.data.disabled) return;
    this.triggerEvent('tap', { id: this.data.taskId, videoUrl: this.data.videoUrl });
  },
  },
});
