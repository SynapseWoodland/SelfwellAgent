/// IA-REF: docs/design/ia-and-wireframe.md §4.2 P02 首页 / §4.6 P06 我的（同页骨架）
/// 设计稿: docs/design/figma-pixso-spec/pages/03-home.html
/// 后端端点:
///   - openapi.yaml tag=[users]  operationId=getCurrentUser  GET  /users/me
///   - openapi.yaml tag=[checkins] operationId=getCheckinCalendar GET /checkins/calendar
///   - openapi.yaml tag=[plans]  operationId=getActivePlan    GET  /plans/active
///
/// Token: color/primary/mint=#A8C5B5, color/bg/page=#FAFBFC,
///        color/bg/card=#FFFFFF, color/status/success=#9DB5A0,
///        radius/lg=16, spacing/4=16
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'package:flutter/material.dart';

import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/progress_ring.dart';
import '../../widgets/task_card.dart';

/// Home (P02). Skeleton for SF0; SF1 fills data from `getCurrentUser` +
/// `getCheckinCalendar` + `getActivePlan`.
class HomePage extends StatelessWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(title: const Text('今天')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.s4),
        children: <Widget>[
          const Center(
            child: ProgressRing(
              size: 120,
              progress: 0.34,
              centerLabel: '7',
              centerSubLabel: '/ 21 天',
            ),
          ),
          const SizedBox(height: AppSpacing.s6),
          const TaskCard(
            title: '今日小动作：呼吸放松 5 分钟',
            subtitle: '建议时段：晚间',
            ctaLabel: '开始',
            icon: Icons.self_improvement,
          ),
          const SizedBox(height: AppSpacing.s3),
          const TaskCard(
            title: '方案第 7 天 · 跟练',
            subtitle: '已为你挑选 3 个跟练视频',
            ctaLabel: '去看',
            icon: Icons.play_circle_outline,
            completed: true,
          ),
        ],
      ),
    );
  }
}