import 'package:flutter/material.dart';

import '../core/api/exceptions.dart';
import '../core/theme/color_tokens.dart';
import '../core/theme/spacing.dart';

/// Visual severity mapper. Per §17 spirit + §13 backend ErrorSeverity
/// contract: drive UX from a single field, not from string parsing.
///
/// Mappings:
/// - `degraded`    → grey non-blocking snackbar
/// - `userError`   → yellow toast (input mistakes)
/// - `transient`   → orange toast + retry CTA (5xx / 429)
/// - `permanent`   → blocking modal (forbidden / compliance)
class ErrorToast {
  ErrorToast._();

  static void show(BuildContext context, ApiException error) {
    switch (error.severity) {
      case ErrorSeverity.degraded:
        _showBanner(context, error);
        break;
      case ErrorSeverity.userError:
        _showToast(
          context,
          message: error.message,
          background: AppColors.severityUserError,
        );
        break;
      case ErrorSeverity.transient:
        _showToast(
          context,
          message: error.message,
          background: AppColors.severityTransient,
          action: SnackBarAction(
            label: '重试',
            textColor: Colors.white,
            onPressed: () {},
          ),
        );
        break;
      case ErrorSeverity.permanent:
        _showModal(context, error);
        break;
    }
  }

  static void _showBanner(BuildContext context, ApiException error) {
    ScaffoldMessenger.of(context).showMaterialBanner(
      MaterialBanner(
        backgroundColor: AppColors.severityDegraded,
        content: Text(
          error.message,
          style: const TextStyle(color: AppColors.neutral900),
        ),
        actions: <Widget>[
          TextButton(
            onPressed: () => ScaffoldMessenger.of(context).hideCurrentMaterialBanner(),
            child: const Text('知道了'),
          ),
        ],
      ),
    );
  }

  static void _showToast(
    BuildContext context, {
    required String message,
    required Color background,
    SnackBarAction? action,
  }) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: background,
        content: Text(message, style: const TextStyle(color: Colors.white)),
        action: action,
        behavior: SnackBarBehavior.floating,
        shape: const RoundedRectangleBorder(borderRadius: AppRadius.rSm),
      ),
    );
  }

  static void _showModal(BuildContext context, ApiException error) {
    showDialog<void>(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext _) => AlertDialog(
        backgroundColor: AppColors.bgCard,
        title: Text(error.code, style: const TextStyle(fontSize: 14)),
        content: Text(error.message),
        actions: <Widget>[
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('关闭'),
          ),
        ],
      ),
    );
  }
}