// widgets/glass_panel.dart -- the translucent bordered card used
// throughout the design (`.glass-panel` / `bg-surface-container`
// blocks in the Stitch HTML).

import 'package:flutter/material.dart';

import '../theme/vulnara_theme.dart';

class GlassPanel extends StatelessWidget {
  const GlassPanel({
    super.key,
    required this.child,
    this.padding = const EdgeInsets.all(VulnaraSpacing.containerPadding),
    this.borderColor,
    this.color,
    this.borderRadius = VulnaraRadius.xl,
    this.borderWidth = 1,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Color? borderColor;
  final Color? color;
  final double borderRadius;
  final double borderWidth;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: color ?? VulnaraColors.surface.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(borderRadius),
        border: Border.all(color: borderColor ?? Colors.white.withValues(alpha: 0.08), width: borderWidth),
      ),
      child: child,
    );
  }
}

/// Small pill-shaped status/severity badge, e.g. "IN PROGRESS", "CRITICAL".
class VulnaraChip extends StatelessWidget {
  const VulnaraChip({
    super.key,
    required this.label,
    required this.color,
    this.filled = false,
    this.dot = false,
    this.icon,
  });

  final String label;
  final Color color;
  final bool filled;
  final bool dot;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: filled ? color : color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(VulnaraRadius.full),
        border: Border.all(color: color.withValues(alpha: filled ? 0 : 0.35)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (dot) ...[
            Container(width: 6, height: 6, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
            const SizedBox(width: 6),
          ],
          if (icon != null) ...[
            Icon(icon, size: 13, color: filled ? VulnaraColors.onPrimary : color),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: VulnaraFonts.labelCaps(color: filled ? VulnaraColors.onPrimary : color),
          ),
        ],
      ),
    );
  }
}
