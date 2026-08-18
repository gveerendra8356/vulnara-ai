// screens/dashboard_screen.dart -- new screen (no existing route in
// lib_me) added for the "Dashboard" tab of the bottom nav.
//
// UI matches the Stitch "global_analytics_dashboard" mock: stat cards
// (open critical vulns, remediations pending, system integrity ring)
// and a "Threats Over Time" line chart.
//
// Data note: lib_me's API surface (contract 2.x/5.x) has no dedicated
// analytics/aggregate endpoint yet. "Open Critical Vulnerabilities" is
// derived client-side from the real scan list (sum of severityCounts
// across completed scans); "Remediations Pending" and the time-series
// chart use representative placeholder data, called out below, until a
// backend aggregate endpoint exists.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/scan.dart';
import '../providers/scan_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/vulnara_app_bar.dart';
import '../widgets/vulnara_bottom_nav.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scansAsync = ref.watch(scanListProvider);

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: VulnaraAppBar(
        actions: [
          IconButton(icon: const Icon(Icons.search, color: VulnaraColors.onSurfaceVariant), onPressed: () {}),
          const SizedBox(width: 4),
          VulnaraAvatar(onTap: () => context.go('/profile')),
        ],
      ),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.dashboard),
      body: ListView(
        padding: EdgeInsets.fromLTRB(
          VulnaraSpacing.containerPadding,
          MediaQuery.of(context).padding.top + 64 + 16,
          VulnaraSpacing.containerPadding,
          32,
        ),
        children: [
          Text('Global Analytics', style: VulnaraFonts.headlineMd()),
          const SizedBox(height: 8),
          Text(
            'Real-time threat telemetry and remediation tracking across all monitored environments.',
            style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
          ),
          const SizedBox(height: VulnaraSpacing.stackLg),
          scansAsync.when(
            loading: () => const Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: Center(child: CircularProgressIndicator()),
            ),
            error: (err, _) => Text(err.toString(), style: VulnaraFonts.bodyBase()),
            data: (scans) {
              final criticalTotal = scans
                  .where((s) => s.status == ScanStatus.completed && s.severityCounts != null)
                  .fold<int>(0, (sum, s) => sum + s.severityCounts!.critical);
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _StatCard(
                    label: 'OPEN CRITICAL VULNERABILITIES',
                    value: '$criticalTotal',
                    delta: '24H',
                    deltaValue: '+${scans.where((s) => s.status == ScanStatus.inProgress).length}',
                    up: true,
                    watermark: Icons.warning_amber_rounded,
                  ),
                  const SizedBox(height: VulnaraSpacing.stackMd),
                  const _StatCard(
                    label: 'REMEDIATIONS PENDING',
                    value: '--',
                    delta: '24H',
                    deltaValue: 'per-scan',
                    up: false,
                    watermark: Icons.build_outlined,
                    footnote: 'Open a scan to view its pending remediations.',
                  ),
                  const SizedBox(height: VulnaraSpacing.stackMd),
                  _IntegrityCard(scans: scans),
                  const SizedBox(height: VulnaraSpacing.stackMd),
                  const _ThreatsChartCard(),
                ],
              );
            },
          ),
        ],
      ),
    );
  }
}

class _StatCard extends StatelessWidget {
  const _StatCard({
    required this.label,
    required this.value,
    required this.delta,
    required this.deltaValue,
    required this.up,
    required this.watermark,
    this.footnote,
  });

  final String label;
  final String value;
  final String delta;
  final String deltaValue;
  final bool up;
  final IconData watermark;
  final String? footnote;

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
      child: Stack(
        children: [
          Positioned(
            right: -8,
            top: -8,
            child: Icon(watermark, size: 64, color: Colors.white.withValues(alpha: 0.04)),
          ),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: VulnaraFonts.labelCaps()),
              const SizedBox(height: 24),
              Row(
                crossAxisAlignment: CrossAxisAlignment.center,
                children: [
                  Text(value, style: VulnaraFonts.outfit(fontSize: 34, fontWeight: FontWeight.w700, color: VulnaraColors.tertiary)),
                  const SizedBox(width: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: VulnaraColors.surfaceContainerHigh,
                      borderRadius: BorderRadius.circular(VulnaraRadius.sm),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(up ? Icons.arrow_upward : Icons.arrow_downward, size: 12, color: VulnaraColors.onSurfaceVariant),
                        const SizedBox(width: 3),
                        Text('$deltaValue $delta', style: VulnaraFonts.codeSm(fontSize: 11, color: VulnaraColors.onSurfaceVariant)),
                      ],
                    ),
                  ),
                ],
              ),
              if (footnote != null) ...[
                const SizedBox(height: 8),
                Text(footnote!, style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant, fontSize: 11)),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _IntegrityCard extends StatelessWidget {
  const _IntegrityCard({required this.scans});

  final List<Scan> scans;

  @override
  Widget build(BuildContext context) {
    final completed = scans.where((s) => s.status == ScanStatus.completed).toList();
    final failed = scans.where((s) => s.status == ScanStatus.failed).length;
    final integrity = scans.isEmpty ? 100 : (((completed.length) / scans.length) * 100).round();

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
          Center(
            child: SizedBox(
              width: 120,
              height: 120,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  SizedBox(
                    width: 120,
                    height: 120,
                    child: CircularProgressIndicator(
                      value: integrity / 100,
                      strokeWidth: 8,
                      backgroundColor: VulnaraColors.surfaceContainerHighest,
                      valueColor: const AlwaysStoppedAnimation(VulnaraColors.primary),
                    ),
                  ),
                  Text('$integrity%', style: VulnaraFonts.headlineMd()),
                ],
              ),
            ),
          ),
          if (failed > 0) ...[
            const SizedBox(height: 12),
            Center(
              child: Text('$failed failed scan${failed == 1 ? '' : 's'} in history',
                  style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
            ),
          ],
        ],
      ),
    );
  }
}

class _ThreatsChartCard extends StatelessWidget {
  const _ThreatsChartCard();

  // Representative series matching the mock's shape -- swap for real
  // telemetry once a `/analytics/threats-over-time` endpoint exists.
  static const _series = [12.0, 22.0, 18.0, 30.0, 26.0, 40.0, 34.0, 52.0];
  static const _labels = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00', 'NOW'];

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
              const Icon(Icons.show_chart, size: 16, color: VulnaraColors.onSurfaceVariant),
              const SizedBox(width: 8),
              Expanded(child: Text('Threats Over Time', style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700))),
              const _Toggle(label: '24H', selected: false),
              const SizedBox(width: 6),
              const _Toggle(label: '7D', selected: true),
            ],
          ),
          const SizedBox(height: VulnaraSpacing.stackLg),
          SizedBox(
            height: 160,
            width: double.infinity,
            child: CustomPaint(painter: _LineChartPainter(_series)),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: _labels
                .map((l) => Text(l, style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant, fontSize: 10)))
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _Toggle extends StatelessWidget {
  const _Toggle({required this.label, required this.selected});
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: selected ? VulnaraColors.surfaceContainerHighest : Colors.transparent,
        borderRadius: BorderRadius.circular(VulnaraRadius.sm),
        border: Border.all(color: VulnaraColors.outlineVariant),
      ),
      child: Text(label, style: VulnaraFonts.labelCaps(fontSize: 10)),
    );
  }
}

class _LineChartPainter extends CustomPainter {
  _LineChartPainter(this.values);
  final List<double> values;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;
    final maxV = values.reduce((a, b) => a > b ? a : b);
    final minV = values.reduce((a, b) => a < b ? a : b);
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
          colors: [VulnaraColors.primary.withValues(alpha: 0.25), VulnaraColors.primary.withValues(alpha: 0)],
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

    canvas.drawCircle(points.last, 4, Paint()..color = Colors.white);
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) => oldDelegate.values != values;
}
