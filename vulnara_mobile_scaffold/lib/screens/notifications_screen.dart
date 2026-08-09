// screens/notifications_screen.dart -- new screen (no existing route in
// lib_me) added for the "Alerts Hub" tab of the bottom nav.
//
// UI matches the Stitch "notifications_alerts_hub" mock: an ALL/CRITICAL
// filter toggle and a list of accent-striped alert rows (icon, title,
// relative timestamp, truncated body).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../theme/vulnara_theme.dart';
import '../widgets/vulnara_app_bar.dart';
import '../widgets/vulnara_bottom_nav.dart';

enum _AlertKind { critical, approved, completed, heartbeat }

class _AlertItem {
  const _AlertItem(this.kind, this.title, this.body, this.time, {this.critical = false});
  final _AlertKind kind;
  final String title;
  final String body;
  final String time;
  final bool critical;
}

// Placeholder feed -- lib_me doesn't yet expose an alerts/notifications
// API, so this renders the same visual structure as the design with
// representative data until that endpoint exists.
const _alerts = [
  _AlertItem(_AlertKind.critical, 'New Critical Vuln Detected',
      'A new critical severity vulnerability was exploited on an ingress node. Immediate review recommended.',
      'JUST NOW', critical: true),
  _AlertItem(_AlertKind.approved, 'Remediation Approved',
      'Automated patch applied to database clusters following successful analyst review.', '12M AGO'),
  _AlertItem(_AlertKind.completed, 'Scan Completed',
      'Weekly comprehensive scan finished on target cluster-alpha. 0 new findings.', '1H AGO'),
  _AlertItem(_AlertKind.heartbeat, 'Agent Heartbeat Resumed',
      'Telemetry restored for edge nodes in region eu-west-1 after a brief outage.', '4H AGO'),
];

class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  bool _criticalOnly = false;

  (IconData, Color) _meta(_AlertKind kind) => switch (kind) {
        _AlertKind.critical => (Icons.auto_awesome, VulnaraColors.error),
        _AlertKind.approved => (Icons.verified_outlined, VulnaraColors.primary),
        _AlertKind.completed => (Icons.check_circle_outline, VulnaraColors.secondaryFixedDim),
        _AlertKind.heartbeat => (Icons.language, VulnaraColors.onSurfaceVariant),
      };

  @override
  Widget build(BuildContext context) {
    final items = _criticalOnly ? _alerts.where((a) => a.critical).toList() : _alerts;

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: VulnaraAppBar(actions: [VulnaraAvatar(onTap: () => context.go('/profile'))]),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.alerts),
      body: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            VulnaraSpacing.containerPadding,
            80,
            VulnaraSpacing.containerPadding,
            0,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text('Alerts Hub', style: VulnaraFonts.headlineMd()),
                  const Spacer(),
                  _FilterPill(label: 'ALL', selected: !_criticalOnly, onTap: () => setState(() => _criticalOnly = false)),
                  const SizedBox(width: 8),
                  _FilterPill(
                      label: 'CRITICAL', selected: _criticalOnly, onTap: () => setState(() => _criticalOnly = true)),
                ],
              ),
              const SizedBox(height: VulnaraSpacing.stackLg),
              Expanded(
                child: items.isEmpty
                    ? Center(
                        child: Text('No alerts.', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                      )
                    : Container(
                        decoration: BoxDecoration(
                          color: VulnaraColors.surface.withValues(alpha: 0.4),
                          borderRadius: BorderRadius.circular(VulnaraRadius.xl),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                        ),
                        child: ListView.separated(
                          padding: EdgeInsets.zero,
                          itemCount: items.length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final a = items[index];
                            final (icon, color) = _meta(a.kind);
                            return Container(
                              padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
                              decoration: a.critical
                                  ? BoxDecoration(border: Border(left: BorderSide(color: color, width: 3)))
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
                                              child: Text(a.title,
                                                  style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700)),
                                            ),
                                            Text(a.time,
                                                style: VulnaraFonts.labelCaps(
                                                    color: a.critical ? color : VulnaraColors.onSurfaceVariant)),
                                          ],
                                        ),
                                        const SizedBox(height: 4),
                                        Text(a.body,
                                            maxLines: 2,
                                            overflow: TextOverflow.ellipsis,
                                            style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                      ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _FilterPill extends StatelessWidget {
  const _FilterPill({required this.label, required this.selected, required this.onTap});

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
          color: selected ? VulnaraColors.surfaceContainerHighest : Colors.transparent,
          borderRadius: BorderRadius.circular(VulnaraRadius.full),
          border: Border.all(color: VulnaraColors.outlineVariant),
        ),
        child: Text(label,
            style: VulnaraFonts.labelCaps(color: selected ? VulnaraColors.onSurface : VulnaraColors.onSurfaceVariant)),
      ),
    );
  }
}
