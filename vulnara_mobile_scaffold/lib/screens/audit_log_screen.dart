// screens/audit_log_screen.dart -- new screen (no existing route in
// lib_me), reachable from Profile > Security. No bottom nav (it's a
// drill-down destination, not a primary tab), matching how the mock
// treats it as a secondary screen off the main shell.
//
// UI matches the Stitch "audit_log_history" mock: filter row (time
// range / role), export button, and a striped table of timestamped
// events with a status chip per row.
//
// Data note: lib_me's API has no audit-log endpoint yet, so this
// renders representative placeholder rows with the exact visual
// structure of the design until that endpoint exists.

import 'package:flutter/material.dart';

import '../theme/vulnara_theme.dart';
import '../widgets/glass_panel.dart';
import '../widgets/vulnara_app_bar.dart';

class _AuditRow {
  const _AuditRow(this.timestamp, this.detail, this.status, this.statusColor, this.accent);
  final String timestamp;
  final String detail;
  final String status;
  final Color statusColor;
  final Color accent;
}

final _rows = [
  const _AuditRow(
    '2023-10-27 14:32:01.442',
    '[ALERT] Vulnerability scanner detected unauthorized access attempt targeting API_GATEWAY_01. Source flagged.',
    'CRITICAL',
    VulnaraColors.error,
    VulnaraColors.error,
  ),
  const _AuditRow(
    '2023-10-27 14:28:15.910',
    'User [Analyst B] approved automated remediation script REM-CVE-2023-XXXX on cluster alpha.',
    'EXEC',
    VulnaraColors.primary,
    VulnaraColors.primary,
  ),
  const _AuditRow(
    '2023-10-27 14:15:00.000',
    'Routine dependency scan completed across 14 repositories. 0 new vulnerabilities found.',
    'INFO',
    VulnaraColors.onSurfaceVariant,
    VulnaraColors.onSurfaceVariant,
  ),
  const _AuditRow(
    '2023-10-27 13:55:22.105',
    'User [Client A] executed hotfix deployment for CVE-2023-1245 in production environment.',
    'SUCCESS',
    VulnaraColors.secondaryFixedDim,
    VulnaraColors.secondaryFixedDim,
  ),
  const _AuditRow(
    '2023-10-27 13:10:45.002',
    '[WARN] Rate limit exceeded on authentication endpoint for IP 192.168.1.45. Throttling applied.',
    'WARN',
    VulnaraColors.statusWarn,
    VulnaraColors.statusWarn,
  ),
];

class AuditLogScreen extends StatelessWidget {
  const AuditLogScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      appBar: VulnaraAppBar(
        showWordmark: false,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: VulnaraColors.onSurfaceVariant),
          onPressed: () => Navigator.of(context).maybePop(),
        ),
        actions: const [VulnaraAvatar()],
      ),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                VulnaraSpacing.containerPadding,
                16,
                VulnaraSpacing.containerPadding,
                0,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('System Audit Log', style: VulnaraFonts.headlineMd()),
                  const SizedBox(height: 8),
                  Text(
                    'Chronological record of platform activities and security events.',
                    style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                  ),
                  const SizedBox(height: VulnaraSpacing.stackLg),
                  const Row(
                    children: [
                      Expanded(child: _FilterButton(icon: Icons.calendar_today_outlined, label: 'Last 24 Hours')),
                      SizedBox(width: 8),
                      Expanded(child: _FilterButton(icon: Icons.filter_alt_outlined, label: 'Role: All')),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                      border: Border.all(color: VulnaraColors.outlineVariant),
                    ),
                    child: const Icon(Icons.download_outlined, size: 18, color: VulnaraColors.onSurfaceVariant),
                  ),
                  const SizedBox(height: VulnaraSpacing.stackLg),
                ],
              ),
            ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.symmetric(horizontal: VulnaraSpacing.containerPadding),
                itemCount: _rows.length + 2,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  if (index == 0) {
                    return Container(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      color: VulnaraColors.surfaceContainerHighest.withValues(alpha: 0.5),
                      child: Row(
                        children: [
                          const SizedBox(width: 12),
                          Expanded(
                              flex: 3,
                              child: Text('TIMESTAMP (UTC)', style: VulnaraFonts.labelCaps(fontSize: 10))),
                          Expanded(
                              flex: 5, child: Text('EVENT DETAILS', style: VulnaraFonts.labelCaps(fontSize: 10))),
                          Expanded(
                            flex: 2,
                            child: Text('STATUS',
                                style: VulnaraFonts.labelCaps(fontSize: 10), textAlign: TextAlign.right),
                          ),
                        ],
                      ),
                    );
                  }
                  if (index == _rows.length + 1) {
                    return Padding(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text('Showing 1-${_rows.length} of 12,402 entries',
                              style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant, fontSize: 12)),
                          const Row(
                            children: [
                              Icon(Icons.chevron_left, size: 18, color: VulnaraColors.outlineVariant),
                              SizedBox(width: 12),
                              Icon(Icons.chevron_right, size: 18, color: VulnaraColors.onSurfaceVariant),
                            ],
                          ),
                        ],
                      ),
                    );
                  }
                  final row = _rows[index - 1];
                  return Container(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    decoration: BoxDecoration(border: Border(left: BorderSide(color: row.accent, width: 3))),
                    child: Padding(
                      padding: const EdgeInsets.only(left: 12),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Expanded(
                                child: Text(row.timestamp,
                                    style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant, fontSize: 11)),
                              ),
                              VulnaraChip(label: row.status, color: row.statusColor),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(row.detail, style: VulnaraFonts.bodyBase(fontSize: 14)),
                        ],
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

class _FilterButton extends StatelessWidget {
  const _FilterButton({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
        border: Border.all(color: VulnaraColors.outlineVariant),
      ),
      child: Row(
        children: [
          Icon(icon, size: 16, color: VulnaraColors.onSurfaceVariant),
          const SizedBox(width: 8),
          Expanded(child: Text(label, style: VulnaraFonts.codeSm(fontSize: 12))),
          const Icon(Icons.expand_more, size: 16, color: VulnaraColors.onSurfaceVariant),
        ],
      ),
    );
  }
}
