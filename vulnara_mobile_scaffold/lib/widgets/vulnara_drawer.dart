// widgets/vulnara_drawer.dart -- the side navigation drawer, the mobile
// counterpart of the web dashboard's left sidebar. It exposes every
// destination (not just the four bottom-nav tabs), scoped by role:
//
//   everyone : Dashboard · Scans · Network Activity · Scheduled Scans ·
//              Alerts · Profile
//   admin    : + Departments · User Management · Audit Log
//
// Open it from the hamburger button in VulnaraAppBar (showMenuButton:true),
// or with an edge-swipe. Tapping an entry closes the drawer and navigates.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../theme/vulnara_theme.dart';

class VulnaraDrawer extends ConsumerWidget {
  const VulnaraDrawer({super.key, this.current});

  /// The go_router path of the screen currently shown, used to highlight
  /// the matching entry. Null = nothing highlighted.
  final String? current;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState is AuthLoggedIn ? authState.user : null;
    final isAdmin = user?.role == 'admin';
    final roleColor = switch (user?.role ?? 'analyst') {
      'admin' => VulnaraColors.error,
      'analyst' => VulnaraColors.primary,
      _ => VulnaraColors.secondaryFixedDim,
    };
    final initial = (user?.fullName ?? '?').trim().isNotEmpty
        ? user!.fullName.trim().substring(0, 1).toUpperCase()
        : '?';

    return Drawer(
      backgroundColor: VulnaraColors.surface,
      width: 300,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ── Account header ───────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(colors: [
                        roleColor.withValues(alpha: 0.3),
                        roleColor.withValues(alpha: 0.05),
                      ]),
                      border: Border.all(color: roleColor.withValues(alpha: 0.4), width: 2),
                    ),
                    child: Text(initial,
                        style: VulnaraFonts.headlineMd(color: roleColor).copyWith(fontSize: 20)),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(user?.fullName ?? 'Vulnara',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700)),
                        const SizedBox(height: 2),
                        Text((user?.role ?? 'analyst').toUpperCase(),
                            style: VulnaraFonts.labelCaps(color: roleColor)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),

            // ── Destinations ─────────────────────────────────────────────
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(vertical: 8),
                children: [
                  _DrawerItem(
                    icon: Icons.dashboard_outlined,
                    label: 'Global Analytics',
                    path: '/dashboard',
                    current: current,
                    primaryTab: true,
                  ),
                  _DrawerItem(
                    icon: Icons.radar,
                    label: 'Scans',
                    path: '/scans',
                    current: current,
                    primaryTab: true,
                  ),
                  _DrawerItem(
                    icon: Icons.lan_outlined,
                    label: 'Network Activity',
                    path: '/overview',
                    current: current,
                  ),
                  _DrawerItem(
                    icon: Icons.schedule_outlined,
                    label: 'Scheduled Scans',
                    path: '/schedules',
                    current: current,
                  ),
                  _DrawerItem(
                    icon: Icons.notifications_active_outlined,
                    label: 'Alerts',
                    path: '/notifications',
                    current: current,
                    primaryTab: true,
                  ),
                  if (isAdmin) ...[
                    const _DrawerSectionLabel('ADMIN'),
                    _DrawerItem(
                      icon: Icons.groups_outlined,
                      label: 'Departments',
                      path: '/admin/departments',
                      current: current,
                    ),
                    _DrawerItem(
                      icon: Icons.group_outlined,
                      label: 'User Management',
                      path: '/admin/users',
                      current: current,
                    ),
                    _DrawerItem(
                      icon: Icons.history,
                      label: 'Audit Log',
                      path: '/audit-log',
                      current: current,
                    ),
                  ],
                  const _DrawerSectionLabel('ACCOUNT'),
                  _DrawerItem(
                    icon: Icons.person_outline,
                    label: 'Profile',
                    path: '/profile',
                    current: current,
                    primaryTab: true,
                  ),
                ],
              ),
            ),

            const Divider(height: 1),
            // ── Log out ──────────────────────────────────────────────────
            Padding(
              padding: const EdgeInsets.all(16),
              child: OutlinedButton.icon(
                onPressed: () {
                  Navigator.of(context).pop(); // close the drawer first
                  ref.read(authProvider.notifier).logout();
                },
                style: OutlinedButton.styleFrom(
                  foregroundColor: VulnaraColors.error,
                  side: const BorderSide(color: VulnaraColors.error),
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                ),
                icon: const Icon(Icons.logout, size: 16),
                label: Text('LOG OUT',
                    style: VulnaraFonts.labelCaps(color: VulnaraColors.error)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _DrawerItem extends StatelessWidget {
  const _DrawerItem({
    required this.icon,
    required this.label,
    required this.path,
    required this.current,
    this.primaryTab = false,
  });

  final IconData icon;
  final String label;
  final String path;
  final String? current;

  /// Primary tabs (Dashboard/Scans/Alerts/Profile) are bottom-nav roots:
  /// navigate with `go` so we don't stack duplicates. Secondary screens
  /// use `push` so the back arrow returns to where the user came from.
  final bool primaryTab;

  @override
  Widget build(BuildContext context) {
    final active = current == path;
    final color = active ? VulnaraColors.primary : VulnaraColors.onSurfaceVariant;
    return Material(
      color: active
          ? VulnaraColors.primary.withValues(alpha: 0.10)
          : Colors.transparent,
      child: InkWell(
        onTap: () {
          Navigator.of(context).pop(); // close the drawer
          if (active) return;
          if (primaryTab) {
            context.go(path);
          } else {
            context.push(path);
          }
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          decoration: active
              ? const BoxDecoration(
                  border: Border(
                      left: BorderSide(color: VulnaraColors.primary, width: 3)))
              : null,
          child: Row(
            children: [
              Icon(icon, size: 20, color: color),
              const SizedBox(width: 16),
              Text(label,
                  style: VulnaraFonts.bodyBase(
                    color: active ? VulnaraColors.onSurface : VulnaraColors.onSurfaceVariant,
                    fontWeight: active ? FontWeight.w700 : FontWeight.w400,
                  )),
            ],
          ),
        ),
      ),
    );
  }
}

class _DrawerSectionLabel extends StatelessWidget {
  const _DrawerSectionLabel(this.label);
  final String label;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 6),
      child: Text(label, style: VulnaraFonts.labelCaps()),
    );
  }
}
