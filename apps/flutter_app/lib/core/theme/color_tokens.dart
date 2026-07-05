import 'package:flutter/material.dart';

/// Design tokens for Selfwell Flutter app.
///
/// Single source of truth: `docs/design/figma-pixso-spec/dist/tokens-flat.json`.
/// This file MUST stay byte-equivalent to the JSON (only adding a typed surface).
///
/// Forbidden colors (§17 hard-constraint #11): the CI grep MUST stay 0-hit.
class AppColors {
  AppColors._();

  // --- Primary palette (5) ---
  static const Color primaryMint = Color(0xFFA8C5B5);
  static const Color primaryCream = Color(0xFFF5E6D3);
  static const Color primaryLavender = Color(0xFFD4C5E2);
  static const Color primaryPeach = Color(0xFFF0D9C4);
  static const Color primarySkyblue = Color(0xFFB8D4E3);

  // --- Neutral ramp (5) ---
  static const Color neutral900 = Color(0xFF2D3436);
  static const Color neutral700 = Color(0xFF4A5568);
  static const Color neutral500 = Color(0xFF718096);
  static const Color neutral300 = Color(0xFFA0AEC0);
  static const Color neutral100 = Color(0xFFE2E8F0);

  // --- Status (2) ---
  static const Color statusWarning = Color(0xFFE8B87A);
  static const Color statusSuccess = Color(0xFF9DB5A0);

  // --- Background ---
  static const Color bgPage = Color(0xFFFAFBFC);
  static const Color bgCard = Color(0xFFFFFFFF);
  static const Color bgCardWarm = Color(0xFFF5E6D3);

  /// Persona FSM states (M5) — mapped to primary palette.
  static const Color personaWarm = primaryMint;
  static const Color personaNeutral = neutral700;
  static const Color personaSlightHug = primaryPeach;
  static const Color personaMedicalGuarded = primaryLavender;

  /// Error severity → color (see `exceptions.dart`).
  static const Color severityDegraded = neutral300; // grey
  static const Color severityUserError = statusWarning; // muted orange
  static const Color severityTransient = statusWarning; // muted orange
  static const Color severityPermanent = neutral900; // dark grey (NOT red)
}