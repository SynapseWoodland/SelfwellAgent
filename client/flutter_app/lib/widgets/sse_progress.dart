import 'package:flutter/material.dart';

import '../core/theme/color_tokens.dart';
import '../core/theme/spacing.dart';

/// SSE 8-stage progress bar for the diagnosis loading page.
/// The 8 stages come from `docs/api/sse-events.md` (Stage 1..8).
///
/// Per §17 hard-constraint #16: on transport failure the parent must
/// schedule exponential reconnect (1s → 2s → 4s capped at 30s, 5 fails
/// then "网络异常，请稍后查看报告"). The widget itself just renders state.
class SseProgress extends StatelessWidget {
  const SseProgress({
    required this.current,
    required this.total,
    super.key,
    this.label,
  })  : assert(current >= 0),
        assert(total > 0),
        assert(current <= total);

  /// 1-based index of the current stage (clamped by parent).
  final int current;

  /// Total number of stages (8 in V1.3).
  final int total;

  /// Optional human-readable label, e.g. "正在分析肤况…".
  final String? label;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        if (label != null) ...<Widget>[
          Text(
            label!,
            style: const TextStyle(
              fontSize: 14,
              color: AppColors.neutral700,
            ),
          ),
          const SizedBox(height: AppSpacing.s3),
        ],
        ClipRRect(
          borderRadius: AppRadius.rSm,
          child: LinearProgressIndicator(
            minHeight: 8,
            value: current / total,
            backgroundColor: AppColors.neutral100,
            color: AppColors.primaryMint,
          ),
        ),
        const SizedBox(height: AppSpacing.s2),
        Text(
          '$current / $total',
          style: const TextStyle(
            fontSize: 12,
            color: AppColors.neutral500,
          ),
        ),
      ],
    );
  }
}