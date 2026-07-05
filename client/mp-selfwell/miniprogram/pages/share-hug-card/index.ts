/**
 * IA-REF: docs/design/ia-and-wireframe.md §13 M10 抱抱卡
 * 设计稿:
 *   - docs/design/figma-pixso-spec/pages/12-hug-card-day7.html
 *   - docs/design/figma-pixso-spec/pages/13-hug-card-day14.html
 *   - docs/design/figma-pixso-spec/pages/14-hug-card-day21.html
 * 后端端点: openapi.yaml tag=share operationId=generateSharePoster
 *
 * 占位：3 张共用 ?day=7|14|21，按 day 参数渲染对应文案。
 */
type Day = 7 | 14 | 21;

const CARDS: Record<
  Day,
  { title: string; subtitle: string; badge: string }
> = {
  7: {
    title: '第一周，慢慢来',
    subtitle: '你已经在这里了',
    badge: 'Day 7',
  },
  14: {
    title: '两周，节奏稳了',
    subtitle: '你比自己想象的更稳',
    badge: 'Day 14',
  },
  21: {
    title: '21 天，仪式达成',
    subtitle: '成为更温柔的自己',
    badge: 'Day 21',
  },
};

Page({
  data: {
    day: 7 as Day,
    card: CARDS[7],
  },

  onLoad(query: Record<string, string | undefined>) {
    const raw = Number(query?.day ?? 7);
    const day = (raw === 14 ? 14 : raw === 21 ? 21 : 7) as Day;
    this.setData({ day, card: CARDS[day] });
  },

  onShareAppMessage() {
    return {
      title: this.data.card.title,
      path: `/miniprogram/pages/share-hug-card/index?day=${this.data.day}`,
    };
  },
});