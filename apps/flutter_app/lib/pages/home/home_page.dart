/// IA-REF: docs/design/ia-and-wireframe.md §4.2 P02 首页
/// 设计稿: docs/design/figma-pixso-spec/pages/03-home.html
/// 后端端点:
///   - openapi.yaml tag=[users]  operationId=getCurrentUser  GET  /users/me
///   - openapi.yaml tag=[checkins] operationId=getCheckinStats  GET /checkins/stats
///   - openapi.yaml tag=[plans]  operationId=getActivePlan    GET  /plans/active
///
/// Token: color/primary/mint=#A8C5B5, color/bg/page=#FAFBFC,
///        color/bg/card=#FFFFFF, color/status/success=#9DB5A0,
///        color/primary/cream=#F5E6D3, radius/lg=16, spacing/4=16
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/progress_ring.dart';
import '../../widgets/task_card.dart';

/// Combined home-page state. Bundling these three avoids each viewer
/// refetching and keeps the loading/error UX coherent. Pages like P03
/// (butler) or P11 (profile) can `ref.watch(homeSnapshotProvider)` too.
@immutable
class HomeSnapshot {
  const HomeSnapshot({
    required this.profile,
    required this.stats,
    this.plan,
  });
  final UserProfile profile;
  final CheckinStats stats;
  final ActivePlan? plan;
}

final FutureProvider<HomeSnapshot> homeSnapshotProvider =
    FutureProvider<HomeSnapshot>((Ref ref) async {
  final ApiService api = ref.watch(apiServiceProvider);
  final UserProfile profile = await api.getMe();
  final CheckinStats stats = await api.getCheckinStats();
  ActivePlan? plan;
  try {
    plan = await api.getActivePlanOrNull();
  } catch (_) {
    plan = null;
  }
  return HomeSnapshot(profile: profile, stats: stats, plan: plan);
});

class HomePage extends ConsumerWidget {
  const HomePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<HomeSnapshot> snap = ref.watch(homeSnapshotProvider);

    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        leading: const Icon(Icons.menu, color: AppColors.neutral700),
        title: const Text('Selfwell'),
        actions: <Widget>[
          IconButton(
            icon: const Icon(Icons.more_horiz, color: AppColors.neutral700),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(homeSnapshotProvider);
        },
        child: snap.when(
          data: (HomeSnapshot s) => _Body(snapshot: s),
          loading: () => const _LoadingBody(),
          error: (Object e, _) => _ErrorBody(
            onRetry: () => ref.invalidate(homeSnapshotProvider),
          ),
        ),
      ),
    );
  }
}

class _LoadingBody extends StatelessWidget {
  const _LoadingBody();
  @override
  Widget build(BuildContext context) =>
      const Center(child: CircularProgressIndicator());
}

class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.onRetry});
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.s6),
      children: <Widget>[
        const SizedBox(height: 64),
        const Center(
          child: Icon(Icons.cloud_off_outlined,
              size: 56, color: AppColors.neutral500),
        ),
        const SizedBox(height: AppSpacing.s3),
        const Center(
          child: Text(
            '加载失败了，明天再试试吧',
            style: TextStyle(fontSize: 16, color: AppColors.neutral700),
          ),
        ),
        const SizedBox(height: AppSpacing.s3),
        Center(
          child: OutlinedButton(onPressed: onRetry, child: const Text('重试')),
        ),
      ],
    );
  }
}

class _Body extends StatelessWidget {
  const _Body({required this.snapshot});
  final HomeSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final String nickName = snapshot.profile.nickName;
    final String greeting = _greetingForNow();
    final int streak = snapshot.stats.streakDays;
    final double progress = (streak / 21.0).clamp(0.0, 1.0);

    return ListView(
      padding: const EdgeInsets.all(AppSpacing.s4),
      children: <Widget>[
        Text(
          '$greeting，$nickName',
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.w500,
            color: AppColors.neutral900,
          ),
        ),
        const SizedBox(height: AppSpacing.s1),
        const Text(
          '今天也是慢慢变好的一天',
          style: TextStyle(color: AppColors.neutral700),
        ),
        const SizedBox(height: AppSpacing.s6),
        _ProgressCard(streak: streak, progress: progress),
        const SizedBox(height: AppSpacing.s4),
        if (snapshot.plan == null)
          const _EmptyPlanCard()
        else
          _TodayTasksCard(plan: snapshot.plan!),
      ],
    );
  }
}

class _EmptyPlanCard extends StatelessWidget {
  const _EmptyPlanCard();

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text(
              '还没有开始哦',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w500,
                color: AppColors.neutral900,
              ),
            ),
            const SizedBox(height: AppSpacing.s2),
            const Text(
              '从智能分析开始，生成你的专属养护参考。',
              style: TextStyle(color: AppColors.neutral700),
            ),
            const SizedBox(height: AppSpacing.s3),
            ElevatedButton(
              onPressed: () => context.push('/assistant/home'),
              child: const Text('去智能分析'),
            ),
          ],
        ),
      ),
    );
  }
}

String _greetingForNow() {
  final int hour = DateTime.now().hour;
  if (hour < 5) return '夜深了';
  if (hour < 11) return '早安';
  if (hour < 14) return '中午好';
  if (hour < 18) return '下午好';
  return '晚上好';
}

class _ProgressCard extends StatelessWidget {
  const _ProgressCard({required this.streak, required this.progress});
  final int streak;
  final double progress;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.bgCardWarm,
        borderRadius: AppRadius.rLg,
      ),
      child: Column(
        children: <Widget>[
          ProgressRing(
            size: 120,
            progress: progress,
            centerLabel: '$streak',
            centerSubLabel: '/ 21 天',
          ),
          const SizedBox(height: AppSpacing.s3),
          Text.rich(
            TextSpan(
              children: <InlineSpan>[
                const TextSpan(text: '已连续走到第 '),
                TextSpan(
                  text: '$streak',
                  style: const TextStyle(
                    color: AppColors.primaryMint,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const TextSpan(text: ' 天，慢慢来'),
              ],
            ),
            style: const TextStyle(color: AppColors.neutral700),
          ),
        ],
      ),
    );
  }
}

class _TodayTasksCard extends StatelessWidget {
  const _TodayTasksCard({required this.plan});
  final ActivePlan plan;

  @override
  Widget build(BuildContext context) {
    final List<PlanDay> tasks = plan.days.take(3).toList();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Row(
              children: <Widget>[
                const Text(
                  '今日小动作',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w500,
                    color: AppColors.neutral900,
                  ),
                ),
                const Spacer(),
                Text(
                  '${tasks.length} 项 · 共 ${tasks.fold<int>(0, (int s, PlanDay d) => s + d.minutes)} 分钟',
                  style: const TextStyle(
                    color: AppColors.neutral500,
                    fontSize: 12,
                  ),
                ),
              ],
            ),
            const SizedBox(height: AppSpacing.s2),
            for (final PlanDay d in tasks) ...<Widget>[
              TaskCard(
                title: d.title,
                subtitle: '${d.minutes} 分钟',
                ctaLabel: '开始',
                icon: Icons.self_improvement,
                onTap: () => context.push('/checkin'),
              ),
              const SizedBox(height: AppSpacing.s2),
            ],
          ],
        ),
      ),
    );
  }
}
