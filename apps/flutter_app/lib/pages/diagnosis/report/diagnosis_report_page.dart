/// IA-REF: docs/design/ia-and-wireframe.md §4.8 P03c 智能分析报告
/// 设计稿: docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
/// 后端端点:
///   - openapi.yaml tag=[diagnosis] operationId=getDiagnosis  GET /diagnosis/{id}
///   - openapi.yaml tag=[plans]     operationId=generatePlan  POST /plans/generate
///
/// M2 spec rules:
///   - 3-5 条改善方向 + 7-14 个参考标签
///   - 文案以 "养护方向" 形式呈现 (禁止 "治疗/治愈")
///   - 颜色: 禁用 红 / 深红 / 医疗蓝 三个色值 (见 §17 #11)
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../login/login_page.dart' show apiServiceProvider;

class DiagnosisReportPage extends ConsumerWidget {
  const DiagnosisReportPage({super.key, required this.diagnosisId});
  final String diagnosisId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ApiService api = ref.watch(apiServiceProvider);
    final Future<DiagnosisReport> future = api.getDiagnosis(diagnosisId);
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('你的专属养护报告'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.go('/home'),
        ),
      ),
      body: SafeArea(
        child: FutureBuilder<DiagnosisReport>(
          future: future,
          builder: (BuildContext context,
              AsyncSnapshot<DiagnosisReport> snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return _ErrorView(
                onRetry: () => (context as Element).markNeedsBuild(),
              );
            }
            final DiagnosisReport report = snap.data!;
            return _ReportBody(report: report);
          },
        ),
      ),
    );
  }
}

class _ReportBody extends ConsumerWidget {
  const _ReportBody({required this.report});
  final DiagnosisReport report;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final String today = report.createdAt ?? _today();
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.s4),
      children: <Widget>[
        Text(
          '生成于 $today',
          style: const TextStyle(fontSize: 12, color: AppColors.neutral500),
        ),
        const SizedBox(height: AppSpacing.s3),
        for (final ImproveDirection d in report.improveDirections) ...<Widget>[
          _DirectionCard(direction: d),
          const SizedBox(height: AppSpacing.s3),
        ],
        _TagCloud(tags: report.tags),
        const SizedBox(height: AppSpacing.s6),
        ElevatedButton(
          onPressed: () async {
            try {
              await ref.read(apiServiceProvider).generatePlan();
              if (!context.mounted) return;
              context.go('/home');
            } catch (e) {
              if (!context.mounted) return;
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(content: Text('方案生成失败：$e')),
              );
            }
          },
          child: const Text('开始 21 天'),
        ),
      ],
    );
  }

  String _today() {
    final DateTime now = DateTime.now();
    return '${now.year}.${now.month.toString().padLeft(2, '0')}.${now.day.toString().padLeft(2, '0')}';
  }
}

class _DirectionCard extends StatelessWidget {
  const _DirectionCard({required this.direction});
  final ImproveDirection direction;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: AppRadius.rLg,
        border: Border.all(color: AppColors.neutral100),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Row(
            children: <Widget>[
              Expanded(
                child: Text(
                  direction.title,
                  style: const TextStyle(
                    fontSize: 18,
                    color: AppColors.neutral900,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 8,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primaryCream,
                  borderRadius: AppRadius.rSm,
                ),
                child: Text(
                  direction.severity,
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppColors.neutral700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            '建议：${direction.summary}',
            style: const TextStyle(fontSize: 14, color: AppColors.neutral700),
          ),
          const SizedBox(height: 12),
          TextButton(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('视频跳转在 SF5 视频流对接时联调')),
              );
            },
            child: const Text('查看推荐视频'),
          ),
        ],
      ),
    );
  }
}

class _TagCloud extends StatelessWidget {
  const _TagCloud({required this.tags});
  final List<String> tags;

  @override
  Widget build(BuildContext context) {
    if (tags.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.primaryCream,
        borderRadius: AppRadius.rLg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          const Text(
            '参考标签',
            style: TextStyle(fontSize: 14, color: AppColors.neutral700),
          ),
          const SizedBox(height: AppSpacing.s3),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: tags
                .map(
                  (String t) => Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.bgCard,
                      borderRadius: AppRadius.rSm,
                    ),
                    child: Text(
                      t,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.neutral700,
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.onRetry});
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.s6),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          const Icon(Icons.error_outline, size: 48, color: AppColors.neutral500),
          const SizedBox(height: 12),
          const Text('报告加载失败'),
          const SizedBox(height: 16),
          OutlinedButton(onPressed: onRetry, child: const Text('重试')),
        ],
      ),
    );
  }
}
