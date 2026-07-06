/// IA-REF: docs/design/ia-and-wireframe.md §4.4 P04 方案页
/// 设计稿: docs/design/figma-pixso-spec/pages/07-plan.html
/// 后端端点:
///   - openapi.yaml tag=[plans]  operationId=getActivePlan GET /plans/active
///   - openapi.yaml tag=[videos] operationId=searchVideos  GET /videos/search
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../login/login_page.dart' show apiServiceProvider;

class PlanPage extends ConsumerWidget {
  const PlanPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final Future<ActivePlan?> future =
        ref.watch(apiServiceProvider).getActivePlanOrNull();
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('21 天方案'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: FutureBuilder<ActivePlan?>(
        future: future,
        builder: (BuildContext context, AsyncSnapshot<ActivePlan?> snap) {
          if (snap.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (!snap.hasData) {
            return const _EmptyState();
          }
          return _PlanBody(plan: snap.data!);
        },
      ),
    );
  }
}

class _PlanBody extends StatefulWidget {
  const _PlanBody({required this.plan});
  final ActivePlan plan;

  @override
  State<_PlanBody> createState() => _PlanBodyState();
}

class _PlanBodyState extends State<_PlanBody> {
  int? _selectedDay;

  @override
  Widget build(BuildContext context) {
    final ActivePlan plan = widget.plan;
    final List<PlanDay> days = plan.days;
    final PlanDay? selected = _selectedDay == null
        ? (days.isEmpty
            ? null
            : days.firstWhere(
                (PlanDay d) => !d.completed,
                orElse: () => days.first,
              ))
        : days.firstWhere(
            (PlanDay d) => d.day == _selectedDay,
            orElse: () => days.first,
          );
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.s4),
      children: <Widget>[
        const Text(
          '你的专属养护方案',
          style: TextStyle(fontSize: 28, color: AppColors.neutral900),
        ),
        const SizedBox(height: 4),
        Text(
          plan.phaseLabel ?? '第 1-7 天 · 习惯启动',
          style: const TextStyle(fontSize: 14, color: AppColors.neutral500),
        ),
        const SizedBox(height: AppSpacing.s4),
        _WeekRow(week: 1, days: days, selected: _selectedDay, onSelect: _select),
        const SizedBox(height: AppSpacing.s3),
        _WeekRow(week: 2, days: days, selected: _selectedDay, onSelect: _select),
        const SizedBox(height: AppSpacing.s3),
        _WeekRow(week: 3, days: days, selected: _selectedDay, onSelect: _select),
        const SizedBox(height: AppSpacing.s4),
        if (selected != null) _DayDetail(day: selected),
      ],
    );
  }

  void _select(int day) {
    setState(() => _selectedDay = day);
  }
}

class _WeekRow extends StatelessWidget {
  const _WeekRow({
    required this.week,
    required this.days,
    required this.selected,
    required this.onSelect,
  });
  final int week;
  final List<PlanDay> days;
  final int? selected;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) {
    final List<PlanDay> slice = days.where((PlanDay d) {
      return d.day >= (week - 1) * 7 + 1 && d.day <= week * 7;
    }).toList();
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s3),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: AppRadius.rLg,
      ),
      child: Row(
        children: <Widget>[
          SizedBox(
            width: 36,
            child: Text(
              'W$week',
              style: const TextStyle(
                fontSize: 14,
                color: AppColors.neutral500,
                fontWeight: FontWeight.w500,
              ),
            ),
          ),
          for (final PlanDay d in slice) ...<Widget>[
            const SizedBox(width: 4),
            _DayCell(
              day: d,
              isSelected: d.day == selected,
              onTap: () => onSelect(d.day),
            ),
          ],
        ],
      ),
    );
  }
}

class _DayCell extends StatelessWidget {
  const _DayCell({
    required this.day,
    required this.isSelected,
    required this.onTap,
  });
  final PlanDay day;
  final bool isSelected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final Color color = day.completed
        ? AppColors.statusSuccess
        : (isSelected ? AppColors.primaryMint : AppColors.neutral100);
    final Color fg =
        (day.completed || isSelected) ? Colors.white : AppColors.neutral900;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 36,
        height: 36,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: color,
          borderRadius: AppRadius.rSm,
        ),
        child: Text(
          '${day.day}',
          style: TextStyle(
            fontSize: 12,
            color: fg,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }
}

class _DayDetail extends StatelessWidget {
  const _DayDetail({required this.day});
  final PlanDay day;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.primaryCream,
        borderRadius: AppRadius.rLg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '第 ${day.day} 天 · ${day.title}',
            style: const TextStyle(fontSize: 18, color: AppColors.neutral900),
          ),
          const SizedBox(height: 8),
          Text(
            '${day.minutes} 分钟',
            style: const TextStyle(fontSize: 14, color: AppColors.neutral700),
          ),
          const SizedBox(height: 12),
          OutlinedButton(
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('查看视频在 SF5 视频流对接时联调')),
              );
            },
            child: const Text('查看视频'),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.s6),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          const Icon(Icons.spa_outlined, size: 48, color: AppColors.neutral500),
          const SizedBox(height: 12),
          const Text('还没有方案'),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () => context.push('/diagnosis/upload'),
            child: const Text('去智能分析'),
          ),
        ],
      ),
    );
  }
}
