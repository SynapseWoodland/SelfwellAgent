/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.6 P06 蜕变广场
 * 后端端点:
 *   - GET  /community/posts          — 列表（支持 page/page_size/sort）
 *   - POST /community/posts          — 发帖
 *   - POST /community/posts/:id/like — 点赞 / 取消点赞
 */
import { get, post, ApiException } from '../../utils/request';
import type { CommunityPost, ListPostsResp } from '../../types/api';

interface PageData {
  posts: CommunityPost[];
  page: number;
  pageSize: number;
  total: number;
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  /** 发帖弹窗 */
  showPublish: boolean;
  publishText: string;
  publishing: boolean;
  /** 错误提示 */
  errMsg: string;
}

Page({
  data: {
    posts: [],
    page: 1,
    pageSize: 20,
    total: 0,
    loading: true,
    loadingMore: false,
    hasMore: true,
    showPublish: false,
    publishText: '',
    publishing: false,
    errMsg: '',
  } as PageData,

  onLoad() {
    this._fetchPosts(true);
  },

  onShow() {
    // 保持当前位置，不重新拉列表
  },

  onPullDownRefresh() {
    this._fetchPosts(true).finally(() => wx.stopPullDownRefresh());
  },

  onReachBottom() {
    if (!this.data.loadingMore && this.data.hasMore) {
      this._fetchPosts(false);
    }
  },

  async _fetchPosts(reset: boolean) {
    const { page, pageSize, posts } = this.data;
    const nextPage = reset ? 1 : page + 1;

    if (reset) {
      this.setData({ loading: true, errMsg: '' });
    } else {
      this.setData({ loadingMore: true });
    }

    try {
      const resp = await get<ListPostsResp>(
        `/community/posts?limit=${pageSize}&offset=${(nextPage - 1) * pageSize}`,
      );
      const items: CommunityPost[] = resp?.items ?? [];
      const total: number = resp?.total ?? 0;
      this.setData({
        posts: reset ? items : [...posts, ...items],
        page: nextPage,
        total,
        loading: false,
        loadingMore: false,
        hasMore: (reset ? items.length : posts.length + items.length) < total,
      });
    } catch (e) {
      this.setData({
        loading: false,
        loadingMore: false,
        errMsg: e instanceof ApiException ? e.message : '加载失败',
      });
    }
  },

  onTapPublish() {
    this.setData({ showPublish: true, publishText: '' });
  },

  onPublishInput(e: WechatMiniprogram.Input) {
    this.setData({ publishText: e.detail.value as string });
  },

  async onConfirmPublish() {
    const text = this.data.publishText.trim();
    if (!text) {
      wx.showToast({ title: '内容不能为空', icon: 'none' });
      return;
    }
    this.setData({ publishing: true });
    try {
      await post('/community/posts', { content: text });
      this.setData({ showPublish: false, publishText: '', publishing: false });
      wx.showToast({ title: '发布成功', icon: 'success' });
      this._fetchPosts(true);
    } catch (e) {
      this.setData({ publishing: false });
      wx.showToast({
        title: e instanceof ApiException ? e.message : '发布失败',
        icon: 'none',
      });
    }
  },

  onCancelPublish() {
    this.setData({ showPublish: false, publishText: '' });
  },

  async onTapLike(e: WechatMiniprogram.TapEvent) {
    const { id } = e.currentTarget.dataset as { id: string };
    const { posts } = this.data;
    const idx = posts.findIndex((p) => p.post_id === id);
    if (idx === -1) return;

    const postItem = posts[idx];
    const isLiked = postItem.liked_by_me;
    // 乐观更新
    const updated = {
      liked_by_me: !isLiked,
      like_count: postItem.like_count + (isLiked ? -1 : 1),
    };
    const newPosts = [...posts];
    newPosts[idx] = { ...postItem, ...updated };
    this.setData({ posts: newPosts });

    try {
      await post(`/community/posts/${id}/like`);
    } catch {
      // 回滚
      this.setData({ posts });
    }
  },

  onShareAppMessage() {
    return {
      title: '蜕变广场 · 你的每一步都值得被看见',
      path: '/pages/community/index',
    };
  },
});
