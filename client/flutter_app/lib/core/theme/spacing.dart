/// Numeric spacing tokens aligned with
/// `docs/design/figma-pixso-spec/dist/tokens-flat.json` (spacing block).
class AppSpacing {
  AppSpacing._();

  static const double s1 = 4;
  static const double s2 = 8;
  static const double s3 = 12;
  static const double s4 = 16;
  static const double s6 = 24;
  static const double s8 = 32;
  static const double s12 = 48;

  /// EdgeInsets presets (most-used).
  static const EdgeInsets pageHorizontal = EdgeInsets.symmetric(horizontal: s4);
  static const EdgeInsets cardPadding = EdgeInsets.all(s4);
  static const EdgeInsets sectionGap = EdgeInsets.only(top: s6, bottom: s6);
}

/// Numeric radius tokens aligned with
/// `docs/design/figma-pixso-spec/dist/tokens-flat.json` (radius block).
class AppRadius {
  AppRadius._();

  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double full = 9999;

  static const BorderRadius rSm = BorderRadius.all(Radius.circular(sm));
  static const BorderRadius rMd = BorderRadius.all(Radius.circular(md));
  static const BorderRadius rLg = BorderRadius.all(Radius.circular(lg));
  static const BorderRadius rXl = BorderRadius.all(Radius.circular(xl));
}