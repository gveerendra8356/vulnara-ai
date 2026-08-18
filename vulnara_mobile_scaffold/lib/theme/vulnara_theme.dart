// theme/vulnara_theme.dart -- the Vulnara "tactical intelligence" design
// system: a dark, high-contrast, terminal-inspired Material 3 palette.
// Colors and type ramp are copied 1:1 from the Stitch design tokens
// (vulnara_tactical_intelligence/DESIGN.md and every screen's Tailwind
// config) so the Flutter app renders pixel-for-pixel the same UI.

import 'package:flutter/material.dart';

/// Raw design-token colors, named exactly as in the Stitch color system
/// so it's easy to cross-reference against the original HTML/Tailwind.
class VulnaraColors {
  VulnaraColors._();

  static const onSurface = Color(0xFFE5E2E1);
  static const onTertiary = Color(0xFF68000E);
  static const surfaceVariant = Color(0xFF353534);
  static const onError = Color(0xFF690005);
  static const surfaceContainerLowest = Color(0xFF0E0E0E);
  static const outline = Color(0xFF8B90A0);
  static const surface = Color(0xFF131313);
  static const onSurfaceVariant = Color(0xFFC1C6D7);
  static const errorContainer = Color(0xFF93000A);
  static const error = Color(0xFFFFB4AB);
  static const inverseSurface = Color(0xFFE5E2E1);
  static const onPrimaryContainer = Color(0xFF00285B);
  static const outlineVariant = Color(0xFF414754);
  static const surfaceContainerHighest = Color(0xFF353534);
  static const inversePrimary = Color(0xFF005BC0);
  static const surfaceContainerHigh = Color(0xFF2A2A2A);
  static const surfaceContainerLow = Color(0xFF1C1B1B);
  static const surfaceDim = Color(0xFF131313);
  static const primaryContainer = Color(0xFF4A8EFF);
  static const surfaceContainer = Color(0xFF201F1F);
  static const secondary = Color(0xFFD7FFC5);
  static const onBackground = Color(0xFFE5E2E1);
  static const primaryFixedDim = Color(0xFFADC7FF);
  static const background = Color(0xFF131313);
  static const onPrimary = Color(0xFF002E68);
  static const secondaryContainer = Color(0xFF2FF801);
  static const onSecondary = Color(0xFF053900);
  static const secondaryFixedDim = Color(0xFF2AE500);
  static const onSecondaryContainer = Color(0xFF0F6D00);
  static const tertiary = Color(0xFFFFB3AF);
  static const primary = Color(0xFFADC7FF);
  static const tertiaryContainer = Color(0xFFFF5357);
  static const surfaceBright = Color(0xFF393939);

  /// Deep near-black used for the page `<body>` background (distinct
  /// from `surface`/`background`, which are one shade lighter) and for
  /// input field fills.
  static const pageBackground = Color(0xFF0A0A0A);
  static const inputFill = Color(0xFF050505);

  // Status colors used across scan / vuln severity chips.
  static const statusSuccess = secondaryFixedDim; // green accents / COMPLETED
  static const statusWarn = Color(0xFFFFB74D);
}

/// Font families, matching the Tailwind `fontFamily` design tokens:
/// headline-md/display-lg -> Outfit, body-base -> Inter,
/// label-caps/code-sm -> JetBrains Mono.
class VulnaraFonts {
  VulnaraFonts._();

  static TextStyle outfit({
    required double fontSize,
    required FontWeight fontWeight,
    double? height,
    double? letterSpacing,
    Color? color,
  }) =>
      TextStyle(
        fontFamily: 'Outfit',
        fontSize: fontSize,
        fontWeight: fontWeight,
        height: height,
        letterSpacing: letterSpacing,
        color: color,
      );

  static TextStyle inter({
    required double fontSize,
    FontWeight fontWeight = FontWeight.w400,
    double? height,
    double? letterSpacing,
    Color? color,
  }) =>
      TextStyle(
        fontFamily: 'Inter',
        fontSize: fontSize,
        fontWeight: fontWeight,
        height: height,
        letterSpacing: letterSpacing,
        color: color,
      );

  static TextStyle mono({
    required double fontSize,
    FontWeight fontWeight = FontWeight.w400,
    double? height,
    double? letterSpacing,
    Color? color,
  }) =>
      TextStyle(
        fontFamily: 'JetBrainsMono',
        fontSize: fontSize,
        fontWeight: fontWeight,
        height: height,
        letterSpacing: letterSpacing,
        color: color,
      );

  /// display-lg: 32px/40px, -0.02em, 700 -- the "VULNARA" wordmark.
  static TextStyle displayLg({Color? color, double? letterSpacing}) => outfit(
        fontSize: 32,
        fontWeight: FontWeight.w700,
        height: 40 / 32,
        letterSpacing: letterSpacing ?? -0.02 * 32,
        color: color ?? VulnaraColors.primary,
      );

  /// headline-md: 24px/32px, 600 -- screen titles.
  static TextStyle headlineMd({Color? color}) => outfit(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        height: 32 / 24,
        color: color ?? VulnaraColors.onSurface,
      );

  /// body-base: 16px/24px, 400.
  static TextStyle bodyBase({Color? color, FontWeight? fontWeight, double? fontSize}) => inter(
        fontSize: fontSize ?? 16,
        fontWeight: fontWeight ?? FontWeight.w400,
        height: 24 / 16,
        color: color ?? VulnaraColors.onSurface,
      );

  /// label-caps: 11px/16px, 0.08em, 700 -- all-caps mono labels/badges.
  static TextStyle labelCaps({Color? color, double? letterSpacing, double? fontSize}) => mono(
        fontSize: fontSize ?? 11,
        fontWeight: FontWeight.w700,
        height: 16 / 11,
        letterSpacing: letterSpacing ?? 0.08 * 11,
        color: color ?? VulnaraColors.onSurfaceVariant,
      );

  /// code-sm: 13px/20px, 400 -- monospace body text (timestamps, hosts).
  static TextStyle codeSm({Color? color, FontWeight? fontWeight, double? fontSize}) => mono(
        fontSize: fontSize ?? 13,
        fontWeight: fontWeight ?? FontWeight.w400,
        height: 20 / 13,
        color: color ?? VulnaraColors.onSurface,
      );
}

/// Spacing tokens (Tailwind `spacing` extend block).
class VulnaraSpacing {
  VulnaraSpacing._();
  static const unit = 4.0;
  static const gutter = 12.0;
  static const containerPadding = 16.0;
  static const stackSm = 8.0;
  static const stackMd = 16.0;
  static const stackLg = 24.0;
}

class VulnaraRadius {
  VulnaraRadius._();
  static const sm = 4.0;
  static const lg = 8.0;
  static const xl = 12.0;
  static const full = 999.0;
}

ThemeData buildVulnaraTheme() {
  final base = ThemeData(
    useMaterial3: true,
    brightness: Brightness.dark,
    scaffoldBackgroundColor: VulnaraColors.pageBackground,
    colorScheme: const ColorScheme.dark(
      surface: VulnaraColors.surface,
      onSurface: VulnaraColors.onSurface,
      onSurfaceVariant: VulnaraColors.onSurfaceVariant,
      primary: VulnaraColors.primary,
      onPrimary: VulnaraColors.onPrimary,
      primaryContainer: VulnaraColors.primaryContainer,
      onPrimaryContainer: VulnaraColors.onPrimaryContainer,
      secondary: VulnaraColors.secondary,
      onSecondary: VulnaraColors.onSecondary,
      error: VulnaraColors.error,
      onError: VulnaraColors.onError,
      errorContainer: VulnaraColors.errorContainer,
      onErrorContainer: VulnaraColors.error,
      outline: VulnaraColors.outline,
      outlineVariant: VulnaraColors.outlineVariant,
      surfaceContainerLowest: VulnaraColors.surfaceContainerLowest,
      surfaceContainerLow: VulnaraColors.surfaceContainerLow,
      surfaceContainer: VulnaraColors.surfaceContainer,
      surfaceContainerHigh: VulnaraColors.surfaceContainerHigh,
      surfaceContainerHighest: VulnaraColors.surfaceContainerHighest,
    ),
  );

  return base.copyWith(
    textTheme: base.textTheme.apply(
      bodyColor: VulnaraColors.onSurface,
      displayColor: VulnaraColors.onSurface,
    ),
    splashFactory: InkRipple.splashFactory,
    dividerTheme: const DividerThemeData(color: Colors.white10, thickness: 1, space: 1),
    progressIndicatorTheme: const ProgressIndicatorThemeData(
      color: VulnaraColors.primary,
      linearTrackColor: VulnaraColors.surfaceContainerHighest,
    ),
  );
}
