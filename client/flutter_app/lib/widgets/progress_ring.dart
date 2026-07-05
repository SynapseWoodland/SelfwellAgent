import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../core/theme/color_tokens.dart';

/// Apple-Watch-style progress ring. Used on home (§4.2) and profile (§4.6).
///
/// Painted with [CustomPainter] — no external SVG dep so the SF0 bundle
/// stays slim. Sizes 48 / 80 / 120 from `ia-and-wireframe.md` §2.5.
class ProgressRing extends StatelessWidget {
  const ProgressRing({
    required this.progress,
    super.key,
    this.size = 120,
    this.strokeWidth = 12,
    this.color = AppColors.primaryMint,
    this.trackColor = AppColors.neutral100,
    this.centerLabel,
    this.centerSubLabel,
  }) : assert(progress >= 0 && progress <= 1,
            'progress must be in [0,1]');

  /// Value in `[0, 1]`.
  final double progress;

  /// Outer diameter in logical pixels.
  final double size;

  /// Ring thickness.
  final double strokeWidth;

  /// Active arc color.
  final Color color;

  /// Track color (background ring).
  final Color trackColor;

  /// Big number in the middle (e.g. "7/21").
  final String? centerLabel;

  /// Smaller label under [centerLabel].
  final String? centerSubLabel;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(
        painter: _RingPainter(
          progress: progress,
          strokeWidth: strokeWidth,
          color: color,
          trackColor: trackColor,
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: <Widget>[
              if (centerLabel != null)
                Text(
                  centerLabel!,
                  style: TextStyle(
                    fontSize: math.min(size * 0.18, 28),
                    fontWeight: FontWeight.w600,
                    color: AppColors.neutral900,
                  ),
                ),
              if (centerSubLabel != null)
                Text(
                  centerSubLabel!,
                  style: TextStyle(
                    fontSize: math.min(size * 0.10, 12),
                    color: AppColors.neutral500,
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RingPainter extends CustomPainter {
  _RingPainter({
    required this.progress,
    required this.strokeWidth,
    required this.color,
    required this.trackColor,
  });

  final double progress;
  final double strokeWidth;
  final Color color;
  final Color trackColor;

  @override
  void paint(Canvas canvas, Size size) {
    final Offset center = Offset(size.width / 2, size.height / 2);
    final double radius = (math.min(size.width, size.height) - strokeWidth) / 2;

    final Paint trackPaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = trackColor;

    final Paint activePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round
      ..color = color;

    canvas.drawCircle(center, radius, trackPaint);

    if (progress <= 0) return;
    final double sweep = 2 * math.pi * progress.clamp(0.0, 1.0);
    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      -math.pi / 2,
      sweep,
      false,
      activePaint,
    );
  }

  @override
  bool shouldRepaint(_RingPainter old) =>
      old.progress != progress ||
      old.color != color ||
      old.trackColor != trackColor ||
      old.strokeWidth != strokeWidth;
}