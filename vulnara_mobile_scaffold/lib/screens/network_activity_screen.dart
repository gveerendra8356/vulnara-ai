// screens/network_activity_screen.dart -- the organization security
// overview ("network activity"). Admins see org-wide data; analysts see
// their department only (the backend scopes it). Mirrors the web
// OrgOverviewPage: metrics, discovered assets, and a recent activity feed.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/core_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/glass_panel.dart';

final overviewProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) {
  return ref.watch(organizationRepositoryProvider).getOverview();
});

const _sevColors = {
  'CRITICAL': Color(0xFFF87171),
  'HIGH': Color(0xFFFB923C),
  'MEDIUM': Color(0xFFFACC15),
  'LOW': Color(0xFF60A5FA),
  'INFO': Color(0xFF94A3B8),
};

class NetworkActivityScreen extends ConsumerWidget {
  const NetworkActivityScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(overviewProvider);

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: VulnaraColors.onSurfaceVariant),
          onPressed: () => context.canPop() ? context.pop() : context.go('/dashboard'),
        ),
        title: Text('Network Activity', style: VulnaraFonts.headlineMd()),
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(e.toString(), style: VulnaraFonts.bodyBase(color: VulnaraColors.error)),
          ),
        ),
        data: (data) => _buildBody(context, ref, data),
      ),
    );
  }

  Widget _buildBody(BuildContext context, WidgetRef ref, Map<String, dynamic> data) {
    final isOrg = data['scope'] == 'organization';
    final m = (data['metrics'] as Map?) ?? {};
    final sev = (m['findings_by_severity'] as Map?) ?? {};
    final assets = (data['assets'] as List?) ?? [];
    final activity = (data['activity'] as List?) ?? [];
    final departments = (data['departments'] as List?) ?? [];

    int sevCount(String k) => (sev[k] as num?)?.toInt() ?? 0;
    int metric(String k) => (m[k] as num?)?.toInt() ?? 0;

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(overviewProvider);
        await ref.read(overviewProvider.future);
      },
      child: ListView(
        padding: const EdgeInsets.fromLTRB(
          VulnaraSpacing.containerPadding, 16, VulnaraSpacing.containerPadding, 32),
        children: [
          Text(
            isOrg ? 'Organization-wide' : 'Your department',
            style: VulnaraFonts.labelCaps(color: VulnaraColors.onSurfaceVariant),
          ),
          const SizedBox(height: VulnaraSpacing.stackMd),

          // Metric cards
          Row(children: [
            Expanded(child: _Metric(label: 'SCANS', value: metric('total_scans'), icon: Icons.radar)),
            const SizedBox(width: VulnaraSpacing.stackMd),
            Expanded(child: _Metric(label: 'ASSETS', value: metric('total_assets'), icon: Icons.dns)),
          ]),
          const SizedBox(height: VulnaraSpacing.stackMd),
          Row(children: [
            Expanded(child: _Metric(label: 'OPEN FINDINGS', value: metric('open_findings'), icon: Icons.bug_report)),
            const SizedBox(width: VulnaraSpacing.stackMd),
            Expanded(child: _Metric(label: 'CRITICAL', value: sevCount('CRITICAL'), icon: Icons.warning, accent: _sevColors['CRITICAL'])),
          ]),
          const SizedBox(height: VulnaraSpacing.stackLg),

          // Severity breakdown
          GlassPanel(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('FINDINGS BY SEVERITY', style: VulnaraFonts.labelCaps()),
              const SizedBox(height: 12),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final s in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO'])
                  _SevChip(label: s, count: sevCount(s), color: _sevColors[s]!),
              ]),
            ]),
          ),

          if (isOrg && departments.isNotEmpty) ...[
            const SizedBox(height: VulnaraSpacing.stackMd),
            GlassPanel(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('SCANS BY DEPARTMENT', style: VulnaraFonts.labelCaps()),
                const SizedBox(height: 12),
                Wrap(spacing: 8, runSpacing: 8, children: [
                  for (final d in departments.cast<Map<String, dynamic>>())
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: VulnaraColors.surface.withValues(alpha: 0.4),
                        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                        border: Border.all(color: VulnaraColors.outlineVariant),
                      ),
                      child: Text('${d['name']} · ${d['scan_count']}',
                          style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface)),
                    ),
                ]),
              ]),
            ),
          ],

          const SizedBox(height: VulnaraSpacing.stackMd),
          Text('DISCOVERED ASSETS', style: VulnaraFonts.labelCaps()),
          const SizedBox(height: 8),
          if (assets.isEmpty)
            Text('No assets discovered yet.', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant))
          else
            ...assets.cast<Map<String, dynamic>>().take(30).map((a) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: GlassPanel(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                    child: Row(children: [
                      Expanded(
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${a['host']}:${a['port']}',
                              style: VulnaraFonts.codeSm(color: VulnaraColors.primary)),
                          Text('${a['service_name'] ?? '—'} · ${a['finding_count']} findings',
                              style: VulnaraFonts.codeSm(
                                  color: VulnaraColors.onSurfaceVariant)),
                        ]),
                      ),
                      Text(
                        a['max_cvss'] != null ? (a['max_cvss'] as num).toStringAsFixed(1) : '—',
                        style: VulnaraFonts.headlineMd(
                          color: (a['max_cvss'] as num? ?? 0) >= 9
                              ? _sevColors['CRITICAL']
                              : (a['max_cvss'] as num? ?? 0) >= 7
                                  ? _sevColors['HIGH']
                                  : VulnaraColors.onSurfaceVariant,
                        ),
                      ),
                    ]),
                  ),
                )),

          const SizedBox(height: VulnaraSpacing.stackMd),
          Text('RECENT ACTIVITY', style: VulnaraFonts.labelCaps()),
          const SizedBox(height: 8),
          if (activity.isEmpty)
            Text('No activity yet.', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant))
          else
            ...activity.cast<Map<String, dynamic>>().map((ev) => Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: InkWell(
                    onTap: () => context.push('/scans/${ev['scan_id']}'),
                    borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                    child: GlassPanel(
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                      child: Row(children: [
                        Expanded(
                          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${ev['target']}',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface)),
                            Text('${ev['user_full_name'] ?? ev['user_email']} · ${ev['finding_count']} findings',
                                style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                          ]),
                        ),
                        Text('${ev['status']}',
                            style: VulnaraFonts.labelCaps(
                                color: ev['status'] == 'COMPLETED'
                                    ? VulnaraColors.statusSuccess
                                    : ev['status'] == 'FAILED'
                                        ? VulnaraColors.error
                                        : VulnaraColors.onSurfaceVariant)),
                      ]),
                    ),
                  ),
                )),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value, required this.icon, this.accent});
  final String label;
  final int value;
  final IconData icon;
  final Color? accent;

  @override
  Widget build(BuildContext context) {
    final color = accent ?? VulnaraColors.primary;
    return GlassPanel(
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(icon, color: color, size: 20),
        const SizedBox(height: 8),
        Text('$value', style: VulnaraFonts.displayLg(color: VulnaraColors.onSurface).copyWith(fontSize: 28)),
        Text(label, style: VulnaraFonts.labelCaps(color: VulnaraColors.onSurfaceVariant)),
      ]),
    );
  }
}

class _SevChip extends StatelessWidget {
  const _SevChip({required this.label, required this.count, required this.color});
  final String label;
  final int count;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Text('$count', style: VulnaraFonts.headlineMd(color: color).copyWith(fontSize: 16)),
        const SizedBox(width: 6),
        Text(label, style: VulnaraFonts.labelCaps(color: color)),
      ]),
    );
  }
}
