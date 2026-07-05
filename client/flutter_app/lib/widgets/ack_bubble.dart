import 'package:flutter/material.dart';

import '../core/theme/color_tokens.dart';
import '../core/theme/spacing.dart';

/// Renders an ACK (acknowledgement) bubble on the mood-diary / feedback page.
///
/// Per §17 hard-constraint #15: ACK is strictly <= 30 characters of
/// displayable text. Anything longer is truncated with an ellipsis and
/// revealed in full via a [Tooltip] on long-press. This guarantees the
/// bubble height stays uniform and matches the design grid.
class AckBubble extends StatelessWidget {
  const AckBubble({
    required this.text,
    super.key,
    this.maxChars = 30,
  });

  /// Must be sourced from `docs/data/ack-pool.yaml` — never compose at runtime.
  final String text;

  /// Display cap. Defaults to 30 per §17 #15.
  final int maxChars;

  bool get isTruncated => text.length > maxChars;
  String get displayText =>
      isTruncated ? '${text.substring(0, maxChars)}…' : text;

  @override
  Widget build(BuildContext context) {
    final Widget body = Container(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.s4,
        vertical: AppSpacing.s3,
      ),
      decoration: BoxDecoration(
        color: AppColors.primaryCream,
        borderRadius: AppRadius.rLg,
      ),
      child: Text(
        displayText,
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(
          fontSize: 14,
          height: 1.5,
          color: AppColors.neutral900,
        ),
      ),
    );

    if (!isTruncated) return body;

    return Tooltip(
      message: text,
      waitDuration: const Duration(milliseconds: 250),
      preferBelow: false,
      child: body,
    );
  }
}