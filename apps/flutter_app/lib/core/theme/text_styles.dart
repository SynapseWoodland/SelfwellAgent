import 'package:flutter/material.dart';

import 'color_tokens.dart';

/// Type scale aligned with `ia-and-wireframe.md` §2.2.
/// Font families: PingFang SC (iOS) → Noto Sans SC (Android) fallback chain.
class AppTextStyles {
  AppTextStyles._();

  static const String fontFamilyIOS = 'PingFang SC';

  static const String fontFamilyAndroid = 'NotoSansSC';

  static const List<String> fontFamilyFallback = <String>[
    fontFamilyIOS,
    fontFamilyAndroid,
    'Roboto',
  ];

  // --- Sizes (spec) ---
  static const double sizeBody = 14;
  static const double sizeBodyLg = 16;
  static const double sizeTitleSm = 17;
  static const double sizeTitleLg = 22;
  static const double sizeHeading = 28;
  static const double sizeDisplay = 36;
  static const double sizeCaption = 12;
  static const double sizeLabel = 10;

  // --- Weights ---
  static const FontWeight regular = FontWeight.w400;
  static const FontWeight medium = FontWeight.w500;
  static const FontWeight semibold = FontWeight.w600;

  static TextStyle _base({
    required double size,
    required FontWeight weight,
    required double height,
    required Color color,
  }) {
    return TextStyle(
      fontFamily: fontFamilyIOS,
      fontFamilyFallback: fontFamilyFallback,
      fontSize: size,
      fontWeight: weight,
      height: height,
      color: color,
    );
  }

  static TextStyle get displayLarge => _base(
        size: sizeDisplay,
        weight: semibold,
        height: 1.3,
        color: AppColors.neutral900,
      );

  static TextStyle get headingLarge => _base(
        size: sizeHeading,
        weight: semibold,
        height: 1.4,
        color: AppColors.neutral900,
      );

  static TextStyle get titleLarge => _base(
        size: sizeTitleLg,
        weight: medium,
        height: 1.4,
        color: AppColors.neutral900,
      );

  static TextStyle get titleSmall => _base(
        size: sizeTitleSm,
        weight: medium,
        height: 1.4,
        color: AppColors.neutral900,
      );

  static TextStyle get bodyLarge => _base(
        size: sizeBodyLg,
        weight: regular,
        height: 1.6,
        color: AppColors.neutral700,
      );

  static TextStyle get bodyMedium => _base(
        size: sizeBody,
        weight: regular,
        height: 1.5,
        color: AppColors.neutral700,
      );

  static TextStyle get caption => _base(
        size: sizeCaption,
        weight: regular,
        height: 1.4,
        color: AppColors.neutral500,
      );

  static TextStyle get label => _base(
        size: sizeLabel,
        weight: medium,
        height: 1.2,
        color: AppColors.neutral700,
      );
}