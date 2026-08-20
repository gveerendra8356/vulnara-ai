// widgets/vulnara_bottom_nav.dart -- the bottom nav bar shown on the
// app's primary destinations. Tab set is role-aware:
//
//   admin / analyst  →  Dashboard · Scans · Alerts · Profile  (4 tabs)
//   client           →  Scans · Alerts · Profile               (3 tabs)
//
// Clients are not shown the Dashboard because it displays org-wide
// analytics (all users' scans + global vulnerability totals) that they
// should not have visibility into.

import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../theme/vulnara_theme.dart';

enum VulnaraTab { dashboard, scans, alerts, profile }

class VulnaraBottomNav extends ConsumerWidget {
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

  static const _labels = {
    VulnaraTab.dashboard: 'Dashboard',
    VulnaraTab.scans: 'Scans',
    VulnaraTab.alerts: 'Alerts',
    VulnaraTab.profile: 'Profile',
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final role =
        authState is AuthLoggedIn ? authState.user.role : 'client';

    // Clients don't get the Dashboard tab — it shows org-wide analytics.
    final tabs = role == 'client'
        ? [VulnaraTab.scans, VulnaraTab.alerts, VulnaraTab.profile]
        : VulnaraTab.values;

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
            children: tabs
                .map((tab) => _NavItem(
                      tab: tab,
                      label: _labels[tab]!,
                      active: tab == current,
                      icon: _icons[tab]!,
                      onTap: () {
                        if (tab != current) context.go(_routes[tab]!);
                      },
                    ))
                .toList(),
          ),
        ),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem(
      {required this.tab,
      required this.label,
      required this.active,
      required this.icon,
      required this.onTap});

  final VulnaraTab tab;
  final String label;
  final bool active;
  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color =
        active ? VulnaraColors.primary : VulnaraColors.onSurfaceVariant;
    return Expanded(
      child: Tooltip(
        message: label,
        child: InkWell(
          onTap: onTap,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, size: 24, color: color, semanticLabel: label),
              const SizedBox(height: 4),
              if (active)
                Container(
                    width: 4,
                    height: 4,
                    decoration:
                        BoxDecoration(color: color, shape: BoxShape.circle)),
            ],
          ),
        ),
      ),
    );
  }
}
