// screens/scan_status_screen.dart -- build order item 4: live scan
// status consuming the WebSocket, plus the "simplified threat summary"
// (severity counts + top findings only). Also the entry point into the
// remediation approve/reject flow once a scan is complete.
//
// UI matches the Stitch "live_scan_status" mock: a "SCAN ACTIVE" hero
// panel with a reconnaissance progress bar, a 2x2 severity overview
// grid, and a "Top Findings" list of accent-striped cards.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/scan.dart';
import '../models/vulnerability.dart';
import '../providers/scan_status_provider.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/vulnara_app_bar.dart';
import '../widgets/vulnara_bottom_nav.dart';

class ScanStatusScreen extends ConsumerWidget {
  const ScanStatusScreen({super.key, required this.scanId});

  final String scanId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(scanStatusProvider(scanId));

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: VulnaraAppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.fact_check_outlined, color: VulnaraColors.onSurfaceVariant),
            tooltip: 'Pending remediations',
            onPressed: () => context.push('/scans/$scanId/remediations'),
          ),
          const SizedBox(width: 4),
          const VulnaraAvatar(),
        ],
      ),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.scans),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
          VulnaraSpacing.containerPadding,
          80,
          VulnaraSpacing.containerPadding,
          100,
        ),
        children: [
          _StatusHero(status: status, scanId: scanId),
          const SizedBox(height: VulnaraSpacing.stackLg),
          Row(
            children: [
              const Icon(Icons.bar_chart, size: 16, color: VulnaraColors.onSurfaceVariant),
              const SizedBox(width: 6),
              Text('OVERVIEW', style: VulnaraFonts.labelCaps()),
            ],
          ),
          const SizedBox(height: VulnaraSpacing.stackMd),
          _SeverityGrid(counts: status.severityCounts),
          const SizedBox(height: VulnaraSpacing.stackLg),
          Row(
            children: [
              const Icon(Icons.description_outlined, size: 16, color: VulnaraColors.onSurfaceVariant),
              const SizedBox(width: 6),
              Text('TOP FINDINGS', style: VulnaraFonts.labelCaps()),
              const Spacer(),
              Text('VIEW ALL',
                  style: VulnaraFonts.labelCaps(color: VulnaraColors.primary)),
            ],
          ),
          const SizedBox(height: VulnaraSpacing.stackMd),
          if (status.topFindings.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 16),
              child: Text('No findings yet.', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
            )
          else
            ...status.topFindings.map(
              (f) => Padding(
                padding: const EdgeInsets.only(bottom: VulnaraSpacing.stackMd),
                child: _FindingCard(finding: f, scanId: scanId),
              ),
            ),
          if (status.errorMessage != null) ...[
            const SizedBox(height: VulnaraSpacing.stackMd),
            Text(status.errorMessage!, style: const TextStyle(color: VulnaraColors.error)),
          ],
        ],
      ),
    );
  }
}

class _StatusHero extends StatelessWidget {
  const _StatusHero({required this.status, required this.scanId});

  final ScanStatusState status;
  final String scanId;

  @override
  Widget build(BuildContext context) {
    final label = switch (status.status) {
      ScanStatus.pending => 'SCAN PENDING',
      ScanStatus.inProgress => 'SCAN ACTIVE',
      ScanStatus.completed => 'SCAN COMPLETE',
      ScanStatus.failed => 'SCAN FAILED',
      ScanStatus.cancelled => 'SCAN CANCELLED',
    };
    final color = switch (status.status) {
      ScanStatus.completed => VulnaraColors.secondaryFixedDim,
      ScanStatus.failed => VulnaraColors.error,
      ScanStatus.cancelled => VulnaraColors.outline,
      ScanStatus.inProgress => VulnaraColors.primary,
      ScanStatus.pending => VulnaraColors.outline,
    };

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
      decoration: BoxDecoration(
        color: VulnaraColors.surface.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(VulnaraRadius.xl),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 44,
                height: 44,
                alignment: Alignment.center,
                child: status.status == ScanStatus.inProgress
                    ? SizedBox(
                        width: 28,
                        height: 28,
                        child: CircularProgressIndicator(strokeWidth: 2, color: color),
                      )
                    : Icon(Icons.radar, color: color, size: 28),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(label,
                        style: VulnaraFonts.headlineMd(color: color).copyWith(letterSpacing: 0.5)),
                    const SizedBox(height: 4),
                    Text('Target: scan $scanId', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                  ],
                ),
              ),
            ],
          ),
          if (status.status == ScanStatus.inProgress && status.reconPercent != null) ...[
            const SizedBox(height: VulnaraSpacing.stackLg),
            Row(
              children: [
                Text('Reconnaissance Phase', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                const Spacer(),
                Text('${status.reconPercent}%',
                    style: VulnaraFonts.codeSm(color: VulnaraColors.primary, fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(VulnaraRadius.full),
              child: LinearProgressIndicator(
                value: status.reconPercent! / 100,
                minHeight: 6,
                backgroundColor: VulnaraColors.surfaceContainerHighest,
                valueColor: const AlwaysStoppedAnimation(VulnaraColors.primary),
              ),
            ),
            const SizedBox(height: 8),
            Text('Estimating completion...', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
          ],
        ],
      ),
    );
  }
}

class _SeverityGrid extends StatelessWidget {
  const _SeverityGrid({required this.counts});

  final SeverityCounts counts;

  @override
  Widget build(BuildContext context) {
    final entries = [
      ('CRITICAL', counts.critical, VulnaraColors.error),
      ('HIGH', counts.high, VulnaraColors.error),
      ('MEDIUM', counts.medium, VulnaraColors.outlineVariant),
      ('LOW', counts.low, VulnaraColors.outlineVariant),
    ];
    return GridView.count(
      crossAxisCount: 2,
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: VulnaraSpacing.gutter,
      crossAxisSpacing: VulnaraSpacing.gutter,
      childAspectRatio: 1.9,
      children: entries.map((e) {
        final borderTinted = e.$1 == 'CRITICAL' || e.$1 == 'HIGH';
        return Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: VulnaraColors.surfaceContainer.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(VulnaraRadius.lg),
            border: Border.all(color: borderTinted ? e.$3.withValues(alpha: 0.6) : e.$3.withValues(alpha: 0.4)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(e.$1,
                  style: VulnaraFonts.labelCaps(color: borderTinted ? VulnaraColors.error : VulnaraColors.onSurfaceVariant)),
              const Spacer(),
              Text('${e.$2}'.padLeft(2, '0'),
                  style: VulnaraFonts.outfit(fontSize: 28, fontWeight: FontWeight.w700)),
            ],
          ),
        );
      }).toList(),
    );
  }
}

class _FindingCard extends StatelessWidget {
  const _FindingCard({required this.finding, required this.scanId});

  final VulnerabilitySummary finding;
  final String scanId;

  Color get _color => switch (finding.severity) {
        'CRITICAL' => VulnaraColors.error,
        'HIGH' => VulnaraColors.error,
        'MEDIUM' => VulnaraColors.statusWarn,
        _ => VulnaraColors.onSurfaceVariant,
      };

  IconData get _icon => switch (finding.severity) {
        'CRITICAL' => Icons.error_outline,
        'HIGH' => Icons.warning_amber_rounded,
        _ => Icons.info_outline,
      };

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
        onTap: () => context.push('/scans/$scanId/vulnerabilities/${finding.vulnId}'),
        child: Container(
          padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
          decoration: BoxDecoration(
            color: VulnaraColors.surface.withValues(alpha: 0.3),
            borderRadius: BorderRadius.circular(VulnaraRadius.lg),
            border: Border.all(color: _color.withValues(alpha: 0.4)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(_icon, color: _color, size: 20),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(finding.serviceName ?? 'Unknown finding',
                            style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700)),
                        const SizedBox(height: 2),
                        Text('Host: ${finding.host}${finding.port != null ? ':${finding.port}' : ''}',
                            style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                      ],
                    ),
                  ),
                ],
              ),
              if (finding.confidenceScore != null) ...[
                const SizedBox(height: 12),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 10),
                  decoration: BoxDecoration(
                    color: VulnaraColors.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(VulnaraRadius.sm),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.gps_fixed, size: 14, color: VulnaraColors.primary),
                      const SizedBox(width: 6),
                      Text('${(finding.confidenceScore! * 100).round()}% AI CONFIDENCE',
                          style: VulnaraFonts.labelCaps(color: VulnaraColors.primary)),
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 10),
              Text(finding.severity, style: VulnaraFonts.labelCaps(color: _color)),
            ],
          ),
        ),
      ),
    );
  }
}
