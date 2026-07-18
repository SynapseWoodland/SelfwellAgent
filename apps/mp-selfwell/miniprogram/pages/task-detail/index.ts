/**
 * 视频详情页（v1.1）
 * ────────────────────────────────────────────────────────────────
 * 真源：docs/plan/视频外链跳转浏览器方案-v1.1.md
 *
 * 视频渲染策略（v1.1）：
 *   - playable : 直链 / 白名单 CDN → <video> 组件直接播放
 *   - external : xhslink / bilibili / 小红书 等 → 渲染「复制到浏览器」引导卡片
 *   - empty    : 空链接 → 仅占位
 *
 * 打卡与视频解耦：用户可以先看视频再打卡，也可以跳过视频直接打卡。
 * 视频是激励型软内容，不追踪"是否已观看"（详见方案 §十一）。
 */

import { post, get } from '../../utils/request';
import type { CreateCheckinResp, CheckinToday, UserMe } from '../../types/api';
import { classifyVideoUrl, extractHost } from '../../utils/video-url';

interface TaskDetailData {
  taskId: string;
  title: string;
  subtitle: string;
  videoUrl: string;
  coverUrl: string;
  duration: string;
  bodyPartTags: string[];
  isCheckedIn: boolean;
  streakDays: number;
  /** v1.1 新增：视频 URL 分类结果 */
  isPlayable: boolean;
  isExternal: boolean;
  isEmpty: boolean;
  /** v1.1 新增：视频外链主机名（埋点 / 展示用） */
  videoHost: string;
}

Page({
  data: {
    taskId: '',
    title: '',
    subtitle: '',
    videoUrl: '',
    coverUrl: '',
    duration: '',
    bodyPartTags: [] as string[],
    isCheckedIn: false,
    streakDays: 0,
    isPlayable: false,
    isExternal: false,
    isEmpty: true,
    videoHost: '',
  } as TaskDetailData,

  onLoad(options: { taskId: string; title?: string; subtitle?: string; videoUrl?: string; coverUrl?: string; duration?: string; tags?: string }) {
    const { taskId, title = '', subtitle = '', videoUrl = '', coverUrl = '', duration = '', tags = '' } = options;

    const bodyPartTags = tags ? tags.split(',').filter(Boolean) : [];

    const decodedUrl = decodeURIComponent(videoUrl);
    const urlType = classifyVideoUrl(decodedUrl);

    this.setData({
      taskId,
      title: decodeURIComponent(title),
      subtitle: decodeURIComponent(subtitle),
      videoUrl: decodedUrl,
      coverUrl: decodeURIComponent(coverUrl),
      duration: decodeURIComponent(duration),
      bodyPartTags,
      isPlayable: urlType === 'playable',
      isExternal: urlType === 'external',
      isEmpty: urlType === 'empty',
      videoHost: extractHost(decodedUrl),
    });

    // 外链卡片曝光埋点（仅 external 触发）
    if (urlType === 'external') {
      this.reportExternalCardView();
    }

    this.checkTodayStatus();
  },

  /**
   * 检查今日打卡状态
   */
  async checkTodayStatus() {
    try {
      // 并发获取用户信息和打卡状态
      const [userMe, today] = await Promise.all([
        get<UserMe>('/users/me'),
        get<CheckinToday>('/checkins/today'),
      ]);
      const isCheckedIn = today.done_task_ids.includes(this.data.taskId);
      this.setData({
        isCheckedIn,
        streakDays: userMe?.current_streak_days || 0,
      });
    } catch (err) {
      console.warn('[task-detail] check today status fail', err);
    }
  },

  /**
   * 切换打卡状态
   * 注意：打卡与看视频是解耦的，用户可以看完再打卡，也可以打完卡再看
   */
  async onToggleCheckin() {
    if (this.data.isCheckedIn) return;

    try {
      const resp = await post<CreateCheckinResp>('/checkins', {
        date: new Date().toISOString().slice(0, 10),
        task_ids: [this.data.taskId],
      });

      this.setData({
        isCheckedIn: true,
        streakDays: resp.new_streak || this.data.streakDays,
      });

      wx.showToast({
        title: resp.ack_text || '打卡成功',
        icon: 'none',
        duration: 2500,
      });
    } catch (err: any) {
      console.error('[task-detail] checkin fail', err);
      const message = err?.message || '打卡失败，请重试';
      wx.showToast({
        title: message,
        icon: 'none',
      });
    }
  },

  /**
   * v1.1 新增：外链卡片曝光埋点。
   */
  reportExternalCardView() {
    try {
      // wx.reportAnalytics 在低版本基础库不可用，安全包 try
      if (typeof (wx as any).reportAnalytics === 'function') {
        (wx as any).reportAnalytics('external_video_card_view', {
          task_id: this.data.taskId,
          video_host: this.data.videoHost,
        });
      }
    } catch {
      /* 埋点失败不影响主流程 */
    }
  },

  /**
   * v1.1 新增：「复制到浏览器」主按钮。
   *
   * 设计要点：
   *   - 用 wx.setClipboardData + showModal（强制阅读）
   *   - 复制成功埋点 copy_link_click
   *   - 极端兜底：fail 回调降级为「请长按链接复制」toast
   */
  onCopyToBrowser() {
    const url = this.data.videoUrl;
    if (!url) return;

    wx.setClipboardData({
      data: url,
      success: () => {
        // 埋点：复制点击
        try {
          if (typeof (wx as any).reportAnalytics === 'function') {
            (wx as any).reportAnalytics('copy_link_click', {
              task_id: this.data.taskId,
              video_host: this.data.videoHost,
            });
          }
        } catch {
          /* 埋点失败不影响 */
        }

        wx.showModal({
          title: '链接已复制',
          content: `请打开手机浏览器（Safari / Chrome），粘贴链接观看视频：\n\n${url}\n\n💡 看完记得回来打卡哦～`,
          confirmText: '我知道了',
          showCancel: false,
        });
      },
      fail: () => {
        // 极端兜底（基础库 1.1.0 以下 / 剪贴板权限被禁用）
        wx.showToast({
          title: '请长按链接复制',
          icon: 'none',
          duration: 3000,
        });
      },
    });
  },

  /**
   * 页面分享
   */
  onShareAppMessage() {
    return {
      title: `${this.data.title} - Selfwell 自愈`,
      path: `/pages/task-detail/index?taskId=${this.data.taskId}&title=${encodeURIComponent(this.data.title)}`,
    };
  },
});