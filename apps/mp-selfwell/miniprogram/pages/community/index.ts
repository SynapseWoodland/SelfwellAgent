/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.5 P10 蜕变广场
 * 设计稿: docs/design/figma-pixso-spec/pages/09-plaza.html
 * 后端端点:
 *   - openapi.yaml tag=community operationId=listPosts   GET  /community/posts
 *   - openapi.yaml tag=community operationId=createPost POST /community/posts
 *
 * 行为（SF4 完工态）：
 *  - onLoad 拉 /community/posts（page=1, page_size=20）
 *  - FAB 入口 → 弹输入 modal → POST /community/posts
 *  - 失败 → 降级 mock；提交走 Redis 审核队列回执，乐观更新列表
 */
import { get, post } from '../../utils/request';

interface Post {
  id: string;
  userName: string;
  text: string;
  likes: number;
  liked: boolean;
  createdAt: string;
}

interface PostsListResp {
  items: Post[];
  total: number;
  page: number;
}

Page({
  data: {
    posts: [
      {
        id: 'p1',
        userName: '小绿',
        text: '今天第 7 天，给自己一个小小的赞。',
        likes: 12,
        liked: false,
        createdAt: new Date().toISOString(),
      },
      {
        id: 'p2',
        userName: '阿月',
        text: '昨晚睡得很稳，冥想真的有用。',
        likes: 8,
        liked: false,
        createdAt: new Date().toISOString(),
      },
      {
        id: 'p3',
        userName: '阿岩',
        text: '完成 21 天，给自己发一张抱抱卡。',
        likes: 21,
        liked: false,
        createdAt: new Date().toISOString(),
      },
    ] as Post[],
    publishing: false,
  },

  onLoad() {
    this.fetchPosts();
  },

  onShow() {
    this.fetchPosts();
  },

  async fetchPosts() {
    try {
      const resp = await get<PostsListResp>('/community/posts?page=1&page_size=20');
      if (resp?.items?.length) this.setData({ posts: resp.items });
    } catch {
      /* 保持 mock 兜底 */
    }
  },

  async onTapPublish() {
    if (this.data.publishing) return;
    // 用 wx.showModal 简化输入；正式版可换半屏 sheet
    const res = await new Promise<WechatMiniprogram.ShowModalRes>((resolve) => {
      wx.showModal({
        title: '说点什么',
        editable: true,
        placeholderText: '今天一个小小的变化…',
        success: (r) => resolve(r),
        fail: () => resolve({ confirm: false, content: '' } as WechatMiniprogram.ShowModalRes),
      });
    });
    if (!res.confirm || !res.content?.trim()) return;
    this.setData({ publishing: true });
    try {
      const created = await post<Post>('/community/posts', { content: res.content.trim() });
      const newPost: Post = created ?? {
        id: 'p_' + Date.now(),
        userName: '我',
        text: res.content.trim(),
        likes: 0,
        liked: false,
        createdAt: new Date().toISOString(),
      };
      this.setData({ posts: [newPost, ...this.data.posts] });
      wx.showToast({ title: '已发布，审核中', icon: 'success' });
    } catch (e) {
      wx.showToast({ title: '发布失败，请稍后再试', icon: 'none' });
    } finally {
      this.setData({ publishing: false });
    }
  },
});