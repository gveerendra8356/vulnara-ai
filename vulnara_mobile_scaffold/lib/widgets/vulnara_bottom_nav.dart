// widgets/vulnara_bottom_nav.dart -- the 4-tab bottom nav shown on the
// app's primary destinations: Dashboard, Scans (radar), Alerts, Profile.
// Matches the BottomNavBar block repeated across the Stitch screens.

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/vulnara_theme.dart';

enum VulnaraTab { dashboard, scans, alerts, profile }

class VulnaraBottomNav extends StatelessWidget {
  const VulnaraBottomNav({super.key, required this.current});

  final VulnaraTab current;

  static const _routes = {
    VulnaraTab.dashboard: '/dashboard',
    VulnaraTab.scans: '/scans',
    VulnaraTab.alerts: '/notifications',
    VulnaraTab.profile: '/profile',
  };

  static const _icons = {
    VulnaraTab.dashboard: Icons.dashboard_outlined,
    VulnaraTab.scans: Icons.radar,
    VulnaraTab.alerts: Icons.notifications_active_outlined,
    VulnaraTab.profile: Icons.person_outline,
  };

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 24, sigmaY: 24),
        child: Container(
          height: 64,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(
            color: VulnaraColors.surfaceContainer.withValues(alpha: 0.6),
            border: const Border(top: BorderSide(color: Colors.white10)),
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceAround,
            children: VulnaraTab.values.map((tab) => _NavItem(
                  tab: tab,
                  active: tab == current,
                  icon: _icons[tab]!,
                  onTap: () {
                    if (tab != current) context.go(_routes[tab]!);
                  },
                )).toList(),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({required this.tab, required this.active, required this.icon, required this.onTap});

  final VulnaraTab tab;
  final bool active;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = active ? VulnaraColors.primary : VulnaraColors.onSurfaceVariant;
    return Expanded(
      child: InkWell(
        onTap: onTap,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 24, color: color),
            const SizedBox(height: 4),
            if (active)
              Container(width: 4, height: 4, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          ],
        ),
      ),
    );
  }
}
