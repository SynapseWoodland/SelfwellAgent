import 'package:flutter/material.dart';

import '../core/theme/color_tokens.dart';
import '../core/theme/spacing.dart';

/// One today's small-action card. Used on P02 home (§4.2) and P05 checkin.
class TaskCard extends StatelessWidget {
  const TaskCard({
    required this.title,
    required this.subtitle,
    super.key,
    this.ctaLabel,
    this.onTap,
    this.icon,
    this.completed = false,
  });

  final String title;
  final String subtitle;
  final String? ctaLabel;
  final VoidCallback? onTap;
  final IconData? icon;
  final bool completed;

  @override
  Widget build(BuildContext context) {
    final Color bg = completed ? AppColors.primaryMint : AppColors.bgCard;
    final Color fg = completed ? Colors.white : AppColors.neutral900;

    return InkWell(
      borderRadius: AppRadius.rLg,
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.s4),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: AppRadius.rLg,
          border: Border.all(
            color: completed ? AppColors.primaryMint : AppColors.neutral100,
          ),
        ),
        child: Row(
          children: <Widget>[
            if (icon != null)
              Padding(
                padding: const EdgeInsets.only(right: AppSpacing.s3),
                child: Icon(icon, color: fg, size: 24),
              ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    title,
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w500,
                      color: fg,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.s1),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 12,
                      color: completed ? Colors.white70 : AppColors.neutral500,
                    ),
                  ),
                ],
              ),
            ),
            if (ctaLabel != null)
              Text(
                ctaLabel!,
                style: TextStyle(
                  fontSize: 14,
                  color: completed ? Colors.white : AppColors.primaryMint,
                  fontWeight: FontWeight.w500,
                ),
              ),
          ],
        ),
      ),
    );
  }
}