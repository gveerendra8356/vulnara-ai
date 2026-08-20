// screens/dashboard_screen.dart
//
// "Global Analytics" dashboard tab — all values now sourced from real
// backend data via dashboardStatsProvider (providers/dashboard_providers.dart).
//
// Data sources:
//   GET /scans              → scan status counts, integrity %, recent scans
//   GET /scans/{id}         → per-severity counts (enriched for completed scans)
//   GET /remediations        → pending / approved remediation counts
//   "Threats Over Time"     → client-side bucketing of (critical + high)
//                             findings per completed scan by calendar day

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../providers/dashboard_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/vulnara_app_bar.dart';
import '../widgets/vulnara_bottom_nav.dart';

// Returns the accent colour associated with a role string.
Color _roleColor(String role) => switch (role) {
      'admin' => VulnaraColors.error,
      'analyst' => VulnaraColors.primary,
      _ => VulnaraColors.secondaryFixedDim,
    };

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final statsAsync = ref.watch(dashboardStatsProvider);
    final authState = ref.watch(authProvider);
    final role = authState is AuthLoggedIn ? authState.user.role : 'client';

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: VulnaraAppBar(
        actions: [
          IconButton(
            icon: const Icon(Icons.search,
                color: VulnaraColors.onSurfaceVariant),
            onPressed: () {},
          ),
          const SizedBox(width: 4),
          VulnaraAvatar(onTap: () => context.go('/profile')),
        ],
      ),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.dashboard),
      body: statsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => _ErrorBody(
          message: err.toString(),
          onRetry: () => ref.invalidate(dashboardStatsProvider),
        ),
        data: (stats) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(dashboardStatsProvider),
          child: ListView(
            padding: EdgeInsets.fromLTRB(
              VulnaraSpacing.containerPadding,
              MediaQuery.of(context).padding.top + 64 + 16,
              VulnaraSpacing.containerPadding,
              32,
            ),
            children: [
              // Role badge
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(
                  color: _roleColor(role).withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(VulnaraRadius.full),
                  border: Border.all(color: _roleColor(role).withValues(alpha: 0.3)),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.shield_outlined, size: 11, color: _roleColor(role)),
                    const SizedBox(width: 5),
                    Text(role.toUpperCase(),
                        style: VulnaraFonts.labelCaps(color: _roleColor(role), fontSize: 9)),
                  ],
                ),
              ),
              Text(
                role == 'admin' ? 'Global Analytics' : 'Threat Analytics',
                style: VulnaraFonts.headlineMd(),
              ),
              const SizedBox(height: 8),
              Text(
                role == 'admin'
                    ? 'Org-wide threat telemetry and remediation tracking across all users and environments.'
                    : 'Real-time threat telemetry and remediation tracking across all monitored environments.',
                style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
              ),
              const SizedBox(height: VulnaraSpacing.stackLg),

              // ── Stat cards row ─────────────────────────────────────────────
              Row(
                children: [
                  Expanded(
                    child: _StatCard(
                      label: 'CRITICAL VULNS',
                      value: '${stats.totalCritical}',
                      badge: stats.totalHigh > 0
                          ? '+${stats.totalHigh} HIGH'
                          : null,
                      badgeUp: stats.totalHigh > 0,
                      watermark: Icons.warning_amber_rounded,
                      accentColor: VulnaraColors.error,
                    ),
                  ),
                  const SizedBox(width: VulnaraSpacing.stackMd),
                  Expanded(
                    child: _StatCard(
                      label: 'REMEDIATIONS PENDING',
                      value: '${stats.remediationsPending}',
                      badge: stats.remediationsApproved > 0
                          ? '${stats.remediationsApproved} READY'
                          : 'NONE READY',
                      badgeUp: false,
                      watermark: Icons.build_outlined,
                      accentColor: VulnaraColors.primary,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: VulnaraSpacing.stackMd),

              // ── Active scans + integrity row ───────────────────────────────
              Row(
                children: [
                  Expanded(
                    child: _StatCard(
                      label: 'ACTIVE SCANS',
                      value: '${stats.inProgressScans}',
                      badge: '${stats.totalScans} TOTAL',
                      badgeUp: stats.inProgressScans > 0,
                      watermark: Icons.radar,
                      accentColor: VulnaraColors.secondaryFixedDim,
                    ),
                  ),
                  const SizedBox(width: VulnaraSpacing.stackMd),
                  Expanded(
                    child: _StatCard(
                      label: 'MEDIUM VULNS',
                      value: '${stats.totalMedium}',
                      badge: stats.totalMedium > 0 ? 'REVIEW' : 'CLEAN',
                      badgeUp: stats.totalMedium > 0,
                      watermark: Icons.info_outline,
                      accentColor: VulnaraColors.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: VulnaraSpacing.stackMd),

              // ── System integrity ring ──────────────────────────────────────
              _IntegrityCard(stats: stats),
              const SizedBox(height: VulnaraSpacing.stackMd),

              // ── Threats over time chart (real data) ───────────────────────
              _ThreatsChartCard(
                series: stats.chartSeries,
                labels: stats.chartLabels,
              ),
              const SizedBox(height: VulnaraSpacing.stackMd),

              // ── Recent scans quick-access ──────────────────────────────────
              if (stats.recentScans.isNotEmpty) ...[
                _RecentScansCard(
                  scans: stats.recentScans,
                  onTap: (scanId) => context.go('/scans/$scanId'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

// ── Stat card ─────────────────────────────────────────────────────────────────

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.watermark,
    required this.accentColor,
    this.badge,
    this.badgeUp = false,
  });

  final String label;
  final String value;
  final String? badge;
  final bool badgeUp;
  final IconData watermark;
  final Color accentColor;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
      decoration: BoxDecoration(
        color: VulnaraColors.surface.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(VulnaraRadius.xl),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Stack(
        children: [
          Positioned(
            right: -8,
            top: -8,
            child: Icon(watermark,
                size: 56, color: Colors.white.withValues(alpha: 0.04)),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style: VulnaraFonts.labelCaps(fontSize: 9)),
              const SizedBox(height: 12),
              Text(
                value,
                style: VulnaraFonts.outfit(
                    fontSize: 32,
                    fontWeight: FontWeight.w700,
                    color: accentColor),
              ),
              if (badge != null) ...[
                const SizedBox(height: 6),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                  decoration: BoxDecoration(
                    color: VulnaraColors.surfaceContainerHigh,
                    borderRadius: BorderRadius.circular(VulnaraRadius.sm),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        badgeUp ? Icons.arrow_upward : Icons.arrow_downward,
                        size: 10,
                        color: VulnaraColors.onSurfaceVariant,
                      ),
                      const SizedBox(width: 3),
                      Flexible(
                        child: Text(
                          badge!,
                          style: VulnaraFonts.codeSm(
                              fontSize: 9,
                              color: VulnaraColors.onSurfaceVariant),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

// ── Integrity card ────────────────────────────────────────────────────────────

class _IntegrityCard extends StatelessWidget {
  const _IntegrityCard({required this.stats});

  final DashboardStats stats;

  @override
  Widget build(BuildContext context) {
    final score = stats.integrityScore;
    final Color ringColor = score >= 90
        ? VulnaraColors.primary
        : score >= 60
            ? VulnaraColors.secondaryFixedDim
            : VulnaraColors.error;

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
          Text('SYSTEM INTEGRITY', style: VulnaraFonts.labelCaps()),
          const SizedBox(height: 16),
          Row(
            children: [
              // Ring
              SizedBox(
                width: 100,
                height: 100,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    SizedBox(
                      width: 100,
                      height: 100,
                      child: CircularProgressIndicator(
                        value: score / 100,
                        strokeWidth: 8,
                        backgroundColor: VulnaraColors.surfaceContainerHighest,
                        valueColor: AlwaysStoppedAnimation(ringColor),
                      ),
                    ),
                    Text('$score%', style: VulnaraFonts.headlineMd()),
                  ],
                ),
              ),
              const SizedBox(width: 20),
              // Breakdown legend
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _LegendRow(
                        label: 'Completed',
                        count: stats.completedScans,
                        color: VulnaraColors.primary),
                    const SizedBox(height: 6),
                    _LegendRow(
                        label: 'In Progress',
                        count: stats.inProgressScans,
                        color: VulnaraColors.secondaryFixedDim),
                    const SizedBox(height: 6),
                    _LegendRow(
                        label: 'Failed',
                        count: stats.failedScans,
                        color: VulnaraColors.error),
                    const SizedBox(height: 6),
                    _LegendRow(
                        label: 'Total Scans',
                        count: stats.totalScans,
                        color: VulnaraColors.onSurfaceVariant),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _LegendRow extends StatelessWidget {
  const _LegendRow(
      {required this.label, required this.count, required this.color});

  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(label,
              style: VulnaraFonts.codeSm(
                  fontSize: 11, color: VulnaraColors.onSurfaceVariant)),
        ),
        Text('$count',
            style: VulnaraFonts.codeSm(
                fontSize: 11, fontWeight: FontWeight.w700)),
      ],
    );
  }
}

// ── Threats chart card ────────────────────────────────────────────────────────

class _ThreatsChartCard extends StatelessWidget {
  const _ThreatsChartCard({
    required this.series,
    required this.labels,
  });

  final List<double> series;
  final List<String> labels;

  @override
  Widget build(BuildContext context) {
    final hasData = series.any((v) => v > 0);

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
            children: [
              const Icon(Icons.show_chart,
                  size: 16, color: VulnaraColors.onSurfaceVariant),
              const SizedBox(width: 8),
              Expanded(
                child: Text('Critical + High Findings — Last 7 Days',
                    style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700)),
              ),
            ],
          ),
          const SizedBox(height: VulnaraSpacing.stackLg),
          if (!hasData)
            Center(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  'No completed scans in the last 7 days.',
                  style: VulnaraFonts.codeSm(
                      color: VulnaraColors.onSurfaceVariant),
                ),
              ),
            )
          else ...[
            SizedBox(
              height: 160,
              width: double.infinity,
              child: CustomPaint(painter: _LineChartPainter(series)),
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: labels
                  .map((l) => Text(l,
                      style: VulnaraFonts.codeSm(
                          color: VulnaraColors.onSurfaceVariant,
                          fontSize: 10)))
                  .toList(),
            ),
          ],
        ],
      ),
    );
  }
}

// ── Recent scans card ─────────────────────────────────────────────────────────

class _RecentScansCard extends StatelessWidget {
  const _RecentScansCard({required this.scans, required this.onTap});

  final List scans;
  final void Function(String scanId) onTap;

  @override
  Widget build(BuildContext context) {
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
            children: [
              const Icon(Icons.history,
                  size: 16, color: VulnaraColors.onSurfaceVariant),
              const SizedBox(width: 8),
              Text('Recent Scans',
                  style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700)),
            ],
          ),
          const SizedBox(height: 12),
          ...scans.map((scan) {
            final (icon, color) = _scanMeta(scan.status);
            return InkWell(
              onTap: () => onTap(scan.scanId),
              borderRadius: BorderRadius.circular(VulnaraRadius.lg),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: Row(
                  children: [
                    Icon(icon, size: 16, color: color),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        scan.target,
                        style: VulnaraFonts.codeSm(),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (scan.severityCounts != null &&
                        scan.severityCounts!.critical > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: VulnaraColors.error.withValues(alpha: 0.15),
                          borderRadius:
                              BorderRadius.circular(VulnaraRadius.sm),
                        ),
                        child: Text(
                          '${scan.severityCounts!.critical}C',
                          style: VulnaraFonts.codeSm(
                              fontSize: 10, color: VulnaraColors.error),
                        ),
                      ),
                  ],
                ),
              ),
            );
          }),
        ],
      ),
    );
  }

  (IconData, Color) _scanMeta(dynamic status) {
    // Using string comparison to avoid importing models here.
    final s = status.toString();
    if (s.contains('completed')) {
      return (Icons.check_circle_outline, VulnaraColors.primary);
    }
    if (s.contains('inProgress')) {
      return (Icons.sync, VulnaraColors.secondaryFixedDim);
    }
    if (s.contains('failed')) {
      return (Icons.error_outline, VulnaraColors.error);
    }
    if (s.contains('cancelled')) {
      return (Icons.cancel_outlined, VulnaraColors.onSurfaceVariant);
    }
    return (Icons.hourglass_top_outlined, VulnaraColors.onSurfaceVariant);
  }
}

// ── Line chart painter ────────────────────────────────────────────────────────

class _LineChartPainter extends CustomPainter {
  _LineChartPainter(this.values);
  final List<double> values;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty || values.length < 2) return;

    final maxV = values.reduce((a, b) => a > b ? a : b);
    const minV = 0.0; // Always start from zero for meaningful chart.
    final range = (maxV - minV).clamp(1, double.infinity);

    // Gridlines
    final gridPaint = Paint()
      ..color = Colors.white.withValues(alpha: 0.06)
      ..strokeWidth = 1;
    for (var i = 0; i <= 3; i++) {
      final y = size.height / 3 * i;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    final points = <Offset>[
      for (var i = 0; i < values.length; i++)
        Offset(
          size.width * i / (values.length - 1),
          size.height - ((values[i] - minV) / range) * size.height,
        ),
    ];

    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (final p in points.skip(1)) {
      linePath.lineTo(p.dx, p.dy);
    }

    final fillPath = Path.from(linePath)
      ..lineTo(points.last.dx, size.height)
      ..lineTo(points.first.dx, size.height)
      ..close();

    canvas.drawPath(
      fillPath,
      Paint()
        ..shader = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            VulnaraColors.primary.withValues(alpha: 0.25),
            VulnaraColors.primary.withValues(alpha: 0),
          ],
        ).createShader(Rect.fromLTWH(0, 0, size.width, size.height)),
    );

    canvas.drawPath(
      linePath,
      Paint()
        ..color = VulnaraColors.primary
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5
        ..strokeJoin = StrokeJoin.round
        ..strokeCap = StrokeCap.round,
    );

    // Live dot on the last data point.
    canvas.drawCircle(points.last, 4, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) =>
      oldDelegate.values != values;
}

// ── Error body ────────────────────────────────────────────────────────────────

class _ErrorBody extends StatelessWidget {
  const _ErrorBody({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.cloud_off_outlined,
                size: 48, color: VulnaraColors.error),
            const SizedBox(height: 12),
            Text('Failed to load analytics',
                style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            Text(
              message,
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: VulnaraFonts.codeSm(
                  color: VulnaraColors.onSurfaceVariant),
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
