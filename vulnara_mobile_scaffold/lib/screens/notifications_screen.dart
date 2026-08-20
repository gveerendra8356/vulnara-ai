// screens/notifications_screen.dart
//
// Alerts Hub tab — now backed by real backend data via notificationsProvider.
//
// The feed is synthesised client-side from:
//   • GET /scans        → completed/failed scan events, critical vuln alerts
//   • GET /remediations → pending / approved / executed remediation events
//
// UI matches the original design: ALL / CRITICAL filter toggle + accent-
// striped alert rows (icon, title, relative timestamp, truncated body).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/app_notification.dart';
import '../providers/notification_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/vulnara_app_bar.dart';
import '../widgets/vulnara_bottom_nav.dart';

// ── Icon / colour metadata ────────────────────────────────────────────────────

(IconData, Color) _meta(AppNotificationKind kind) => switch (kind) {
      AppNotificationKind.criticalVuln =>
        (Icons.auto_awesome, VulnaraColors.error),
      AppNotificationKind.scanCompleted =>
        (Icons.check_circle_outline, VulnaraColors.secondaryFixedDim),
      AppNotificationKind.scanFailed =>
        (Icons.error_outline, VulnaraColors.error),
      AppNotificationKind.remediationApproved =>
        (Icons.verified_outlined, VulnaraColors.primary),
      AppNotificationKind.remediationPending =>
        (Icons.hourglass_top_outlined, VulnaraColors.onSurfaceVariant),
      AppNotificationKind.remediationExecuted =>
        (Icons.rocket_launch_outlined, VulnaraColors.secondaryFixedDim),
    };

// ── Relative timestamp helper ─────────────────────────────────────────────────

String _relativeTime(DateTime ts) {
  final diff = DateTime.now().difference(ts);
  if (diff.inSeconds < 60) return 'JUST NOW';
  if (diff.inMinutes < 60) return '${diff.inMinutes}M AGO';
  if (diff.inHours < 24) return '${diff.inHours}H AGO';
  if (diff.inDays < 7) return '${diff.inDays}D AGO';
  return '${(diff.inDays / 7).floor()}W AGO';
}

// ── Screen ────────────────────────────────────────────────────────────────────

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  bool _criticalOnly = false;

  @override
  Widget build(BuildContext context) {
    final notificationsAsync = ref.watch(notificationsProvider);

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: VulnaraAppBar(
        actions: [VulnaraAvatar(onTap: () => context.go('/profile'))],
      ),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.alerts),
      body: Padding(
        padding: EdgeInsets.fromLTRB(
          VulnaraSpacing.containerPadding,
          MediaQuery.of(context).padding.top + 64 + 16,
          VulnaraSpacing.containerPadding,
          0,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Header + filter pills ──────────────────────────────────────
            Row(
              children: [
                Text('Alerts Hub', style: VulnaraFonts.headlineMd()),
                const Spacer(),
                _FilterPill(
                  label: 'ALL',
                  selected: !_criticalOnly,
                  onTap: () => setState(() => _criticalOnly = false),
                ),
                const SizedBox(width: 8),
                _FilterPill(
                  label: 'CRITICAL',
                  selected: _criticalOnly,
                  onTap: () => setState(() => _criticalOnly = true),
                ),
              ],
            ),
            const SizedBox(height: VulnaraSpacing.stackLg),

            // ── Body: loading / error / list ───────────────────────────────
            Expanded(
              child: notificationsAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (err, _) => _ErrorView(
                  message: err.toString(),
                  onRetry: () => ref.invalidate(notificationsProvider),
                ),
                data: (items) {
                  final filtered = _criticalOnly
                      ? items.where((n) => n.isCritical).toList()
                      : items;

                  if (filtered.isEmpty) {
                    return Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _criticalOnly
                                ? Icons.shield_outlined
                                : Icons.notifications_none_outlined,
                            size: 48,
                            color: VulnaraColors.onSurfaceVariant,
                          ),
                          const SizedBox(height: 12),
                          Text(
                            _criticalOnly
                                ? 'No critical alerts.'
                                : 'No alerts yet.',
                            style: VulnaraFonts.codeSm(
                                color: VulnaraColors.onSurfaceVariant),
                          ),
                        ],
                      ),
                    );
                  }

                  return RefreshIndicator(
                    onRefresh: () async =>
                        ref.invalidate(notificationsProvider),
                    child: Container(
                      decoration: BoxDecoration(
                        color:
                            VulnaraColors.surface.withValues(alpha: 0.4),
                        borderRadius:
                            BorderRadius.circular(VulnaraRadius.xl),
                        border: Border.all(
                            color: Colors.white.withValues(alpha: 0.08)),
                      ),
                      child: ListView.separated(
                        padding: EdgeInsets.zero,
                        itemCount: filtered.length,
                        separatorBuilder: (_, __) =>
                            const Divider(height: 1),
                        itemBuilder: (context, index) {
                          final n = filtered[index];
                          final (icon, color) = _meta(n.kind);
                          return _AlertRow(
                            notification: n,
                            icon: icon,
                            color: color,
                          );
                        },
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Alert row ────────────────────────────────────────────────────────────────

class _AlertRow extends StatelessWidget {
  const _AlertRow({
    required this.notification,
    required this.icon,
    required this.color,
  });

  final AppNotification notification;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final n = notification;
    return Container(
      padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
      decoration: n.isCritical
          ? BoxDecoration(
              border: Border(left: BorderSide(color: color, width: 3)))
          : null,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        n.title,
                        style:
                            VulnaraFonts.bodyBase(fontWeight: FontWeight.w700),
                      ),
                    ),
                    Text(
                      _relativeTime(n.timestamp),
                      style: VulnaraFonts.labelCaps(
                          color: n.isCritical
                              ? color
                              : VulnaraColors.onSurfaceVariant),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  n.body,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: VulnaraFonts.codeSm(
                      color: VulnaraColors.onSurfaceVariant),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Error view ────────────────────────────────────────────────────────────────

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined,
                size: 48, color: VulnaraColors.error),
            const SizedBox(height: 12),
            Text(
              'Failed to load alerts',
              style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 6),
            Text(
              message,
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style:
                  VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }
}

// ── Filter pill ───────────────────────────────────────────────────────────────

class _FilterPill extends StatelessWidget {
  const _FilterPill({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(VulnaraRadius.full),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        decoration: BoxDecoration(
          color: selected
              ? VulnaraColors.surfaceContainerHighest
              : Colors.transparent,
          borderRadius: BorderRadius.circular(VulnaraRadius.full),
          border: Border.all(color: VulnaraColors.outlineVariant),
        ),
        child: Text(
          label,
          style: VulnaraFonts.labelCaps(
              color: selected
                  ? VulnaraColors.onSurface
                  : VulnaraColors.onSurfaceVariant),
        ),
      ),
    );
  }
}
