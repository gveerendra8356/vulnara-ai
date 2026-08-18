// widgets/vulnara_app_bar.dart -- the translucent, blurred top bar used
// on every primary screen: either the VULNARA wordmark + shield glyph,
// or a "back" affordance for detail screens, plus a trailing avatar.

import 'dart:ui';

import 'package:flutter/material.dart';

import '../theme/vulnara_theme.dart';

class VulnaraAppBar extends StatelessWidget implements PreferredSizeWidget {
  const VulnaraAppBar({
    super.key,
    this.showWordmark = true,
    this.leading,
    this.actions,
  });

  final bool showWordmark;
  final Widget? leading;
  final List<Widget>? actions;

  static const double _barHeight = 64;

  @override
  Size get preferredSize {
    final view = WidgetsBinding.instance.platformDispatcher.views.first;
    final statusBarHeight = view.padding.top / view.devicePixelRatio;
    return Size.fromHeight(_barHeight + statusBarHeight);
  }

  @override
  Widget build(BuildContext context) {
    final topPadding = MediaQuery.of(context).padding.top;
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: Container(
          height: _barHeight + topPadding,
          padding: EdgeInsets.only(
            top: topPadding,
            left: VulnaraSpacing.containerPadding,
            right: VulnaraSpacing.containerPadding,
          ),
          decoration: BoxDecoration(
            color: VulnaraColors.surface.withValues(alpha: 0.8),
            border: const Border(bottom: BorderSide(color: Colors.white10)),
          ),
          child: SizedBox(
            height: _barHeight,
            child: Row(
              children: [
                if (leading != null) leading!,
                if (showWordmark)
                  Image.asset('assets/logo.png', height: 32, fit: BoxFit.contain),
                const Spacer(),
                if (actions != null) ...actions!,
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Small circular avatar used at the trailing edge of [VulnaraAppBar].
class VulnaraAvatar extends StatelessWidget {
  const VulnaraAvatar({super.key, this.onTap, this.icon = Icons.person});

  final VoidCallback? onTap;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 34,
        height: 34,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: VulnaraColors.surfaceContainerHigh,
          border: Border.all(color: VulnaraColors.outlineVariant),
        ),
        child: Icon(icon, size: 18, color: VulnaraColors.onSurfaceVariant),
      ),
    );
  }
}
