import 'package:flutter/material.dart';

import 'color_tokens.dart';
import 'spacing.dart';
import 'text_styles.dart';

/// Builds the global [ThemeData] from design tokens.
///
/// Source-of-truth: `docs/design/figma-pixso-spec/dist/tokens-flat.json`.
class AppTheme {
  AppTheme._();

  static ThemeData light() {
    const ColorScheme colorScheme = ColorScheme.light(
      primary: AppColors.primaryMint,
      onPrimary: Colors.white,
      secondary: AppColors.primaryPeach,
      onSecondary: AppColors.neutral900,
      surface: AppColors.bgCard,
      onSurface: AppColors.neutral900,
      error: AppColors.neutral900, // NEVER red — see §17 #11
      onError: Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: AppColors.bgPage,
      canvasColor: AppColors.bgPage,
      cardColor: AppColors.bgCard,
      dividerColor: AppColors.neutral100,
      splashColor: AppColors.primaryMint,
      highlightColor: AppColors.primaryMint,

      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.bgPage,
        foregroundColor: AppColors.neutral900,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: AppTextStyles.titleLarge,
      ),

      cardTheme: const CardThemeData(
        color: AppColors.bgCard,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(borderRadius: AppRadius.rLg),
      ),

      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primaryMint,
          foregroundColor: Colors.white,
          minimumSize: const Size(double.infinity, 48),
          shape: const RoundedRectangleBorder(borderRadius: AppRadius.rXl),
          textStyle: AppTextStyles.bodyLarge.copyWith(
            fontWeight: AppTextStyles.semibold,
            color: Colors.white,
          ),
          elevation: 0,
        ),
      ),

      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primaryMint,
          minimumSize: const Size(double.infinity, 48),
          side: const BorderSide(color: AppColors.primaryMint, width: 1),
          shape: const RoundedRectangleBorder(borderRadius: AppRadius.rXl),
          textStyle: AppTextStyles.bodyLarge.copyWith(
            color: AppColors.primaryMint,
          ),
        ),
      ),

      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primaryMint,
          textStyle: AppTextStyles.bodyMedium.copyWith(
            color: AppColors.primaryMint,
          ),
        ),
      ),

      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: AppColors.bgCard,
        contentPadding: EdgeInsets.symmetric(
          horizontal: AppSpacing.s4,
          vertical: AppSpacing.s3,
        ),
        border: OutlineInputBorder(
          borderRadius: AppRadius.rMd,
          borderSide: BorderSide(color: AppColors.neutral100),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: AppRadius.rMd,
          borderSide: BorderSide(color: AppColors.neutral100),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: AppRadius.rMd,
          borderSide: BorderSide(color: AppColors.primaryMint, width: 1.5),
        ),
        hintStyle: TextStyle(color: AppColors.neutral300),
      ),

      textTheme: TextTheme(
        displayLarge: AppTextStyles.displayLarge,
        headlineLarge: AppTextStyles.headingLarge,
        titleLarge: AppTextStyles.titleLarge,
        titleMedium: AppTextStyles.titleSmall,
        bodyLarge: AppTextStyles.bodyLarge,
        bodyMedium: AppTextStyles.bodyMedium,
        bodySmall: AppTextStyles.caption,
        labelSmall: AppTextStyles.label,
      ),

      iconTheme: const IconThemeData(color: AppColors.neutral700, size: 24),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: AppColors.primaryMint,
        linearTrackColor: AppColors.neutral100,
        circularTrackColor: AppColors.neutral100,
      ),
    );
  }
}