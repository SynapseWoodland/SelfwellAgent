/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.5 P10 蜕变广场
 * 设计稿: docs/design/figma-pixso-spec/pages/09-plaza.html
 * 后端端点: openapi.yaml tag=community operationId=getCommunityPosts / createPost
 *
 * 占位：动态卡片列表 + 发布入口。
 */
interface Post {
  id: string;
  userName: string;
  text: string;
  likes: number;
}

Page({
  data: {
    posts: [
      {
        id: 'p1',
        userName: '小绿',
        text: '今天第 7 天，给自己一个小小的赞。',
        likes: 12,
      },
      {
        id: 'p2',
        userName: '阿月',
        text: '昨晚睡得很稳，冥想真的有用。',
        likes: 8,
      },
      {
        id: 'p3',
        userName: '阿岩',
        text: '完成 21 天，给自己发一张抱抱卡。',
        likes: 21,
      },
    ] as Post[],
  },

  onLoad() {
    // SF1 接入 getCommunityPosts
  },

  onTapPublish() {
    wx.navigateTo({ url: '/miniprogram/pages/share-hug-card/index' });
  },
});