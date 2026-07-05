/**
 * IA-REF: docs/design/ia-and-wireframe.md §4.3 P09 对比回顾
 * 设计稿: docs/design/figma-pixso-spec/pages/09-butler-compare.html
 * 后端端点: openapi.yaml tag=butler operationId=listRecallHistory / getRecallMessages
 *
 * 占位：纵向滚动 3 张快照（day 7 / 14 / 21）对比。
 */
interface Snapshot {
  day: 7 | 14 | 21;
  highlights: string[];
}

Page({
  data: {
    snapshots: [
      {
        day: 7,
        highlights: ['冥想频率提升', '睡眠时长稳定 7.5h', '情绪波动减小'],
      },
      {
        day: 14,
        highlights: ['肩颈放松视频完播率 80%', '呼吸节律更稳', '记录日记成为习惯'],
      },
      {
        day: 21,
        highlights: ['整体状态自评提升', '与人沟通更温和', '坚持 21 天仪式达成'],
      },
    ] as Snapshot[],
  },

  onLoad() {},
});