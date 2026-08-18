// screens/scan_list_screen.dart -- build order item 3 (home). Entry
// point after login: scan history + FAB into NewScanScreen.
//
// UI matches the Stitch "scans_list" mock: accent-striped scan cards
// with a status pill, timestamp row, and a live progress bar for
// in-progress scans, plus the shared VULNARA app bar / bottom nav.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../models/scan.dart';
import '../providers/auth_provider.dart';
import '../providers/scan_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/glass_panel.dart';
import '../widgets/vulnara_app_bar.dart';
import '../widgets/vulnara_bottom_nav.dart';

class ScanListScreen extends ConsumerWidget {
  const ScanListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scansAsync = ref.watch(scanListProvider);
    final authState = ref.watch(authProvider);
    final isAdmin = authState is AuthLoggedIn && authState.user.role == 'admin';

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: VulnaraAppBar(actions: [VulnaraAvatar(onTap: () => context.go('/profile'))]),
      floatingActionButton: FloatingActionButton(
        backgroundColor: VulnaraColors.primary,
        foregroundColor: VulnaraColors.onPrimary,
        elevation: 0,
        onPressed: () async {
          final created = await context.push<bool>('/scans/new');
          if (created == true) ref.invalidate(scanListProvider);
        },
        child: const Icon(Icons.add),
      ),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.scans),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(scanListProvider),
        child: scansAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => _ErrorView(message: err.toString(), onRetry: () => ref.invalidate(scanListProvider)),
          data: (scans) => CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverPadding(
                padding: EdgeInsets.fromLTRB(
                  VulnaraSpacing.containerPadding,
                  MediaQuery.of(context).padding.top + 64 + 16,
                  VulnaraSpacing.containerPadding,
                  0,
                ),
                sliver: SliverToBoxAdapter(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        isAdmin ? 'All Scans' : 'Active Scans',
                        style: VulnaraFonts.headlineMd(),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'Monitoring ${scans.length} target${scans.length == 1 ? '' : 's'}.',
                        style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                      ),
                      const SizedBox(height: VulnaraSpacing.stackLg),
                    ],
                  ),
                ),
              ),
              if (scans.isEmpty)
                SliverFillRemaining(
                  hasScrollBody: false,
                  child: Center(
                    child: Text(
                      'No scans yet -- tap "+" to start one.',
                      style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                    ),
                  ),
                )
              else
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(
                    VulnaraSpacing.containerPadding,
                    0,
                    VulnaraSpacing.containerPadding,
                    120,
                  ),
                  sliver: SliverList.separated(
                    itemCount: scans.length,
                    separatorBuilder: (_, __) => const SizedBox(height: VulnaraSpacing.stackMd),
                    itemBuilder: (context, index) => _ScanCard(scan: scans[index], showUser: isAdmin),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ScanCard extends StatelessWidget {
  const _ScanCard({required this.scan, this.showUser = false});

  final Scan scan;
  final bool showUser;

  (Color, String, IconData) _statusMeta() => switch (scan.status) {
        ScanStatus.inProgress => (VulnaraColors.primary, 'IN PROGRESS', Icons.dns_outlined),
        ScanStatus.failed => (VulnaraColors.error, 'FAILED', Icons.language),
        ScanStatus.completed => (VulnaraColors.secondaryFixedDim, 'COMPLETED', Icons.lan),
        ScanStatus.pending => (VulnaraColors.outline, 'PENDING', Icons.storage),
        ScanStatus.cancelled => (VulnaraColors.outline, 'CANCELLED', Icons.storage),
      };

  @override
  Widget build(BuildContext context) {
    final (accent, label, icon) = _statusMeta();
    final dateStr = DateFormat("yyyy-MM-dd HH:mm:ss 'UTC'").format(scan.createdAt.toUtc());
    final isPending = scan.status == ScanStatus.pending || scan.status == ScanStatus.cancelled;

    return Opacity(
      opacity: isPending ? 0.7 : 1,
      child: Material(
        color: VulnaraColors.surfaceContainer,
        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
        child: InkWell(
          borderRadius: BorderRadius.circular(VulnaraRadius.lg),
          onTap: () => context.push('/scans/${scan.scanId}'),
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(VulnaraRadius.lg),
              border: Border.all(color: VulnaraColors.outlineVariant.withValues(alpha: 0.3)),
            ),
            child: Stack(
              children: [
                Positioned(
                  left: 0,
                  top: 0,
                  bottom: 0,
                  child: Container(width: 4, decoration: BoxDecoration(color: accent)),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, VulnaraSpacing.stackMd, VulnaraSpacing.stackMd,
                      VulnaraSpacing.stackMd),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(icon, color: accent, size: 20),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              scan.target,
                              style: VulnaraFonts.codeSm(fontWeight: FontWeight.w700),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          const SizedBox(width: 8),
                          VulnaraChip(label: label, color: accent, dot: scan.status == ScanStatus.inProgress),
                        ],
                      ),
                      // Admin: show who initiated this scan
                      if (showUser && scan.userEmail != null) ...[
                        const SizedBox(height: 6),
                        Row(
                          children: [
                            const Icon(Icons.person_outline, size: 12, color: VulnaraColors.onSurfaceVariant),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                scan.userEmail!,
                                style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)
                                    .copyWith(fontSize: 10),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                            if (scan.userRole != null)
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: VulnaraColors.primary.withValues(alpha: 0.1),
                                  borderRadius: BorderRadius.circular(VulnaraRadius.full),
                                  border: Border.all(color: VulnaraColors.primary.withValues(alpha: 0.25)),
                                ),
                                child: Text(
                                  scan.userRole!.toUpperCase(),
                                  style: VulnaraFonts.labelCaps(color: VulnaraColors.primary)
                                      .copyWith(fontSize: 8),
                                ),
                              ),
                          ],
                        ),
                      ],
                      const SizedBox(height: VulnaraSpacing.stackMd),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                scan.status == ScanStatus.completed ? 'COMPLETED' : 'INITIATED',
                                style: VulnaraFonts.labelCaps(),
                              ),
                              const SizedBox(height: 4),
                              Text(dateStr, style: VulnaraFonts.codeSm()),
                            ],
                          ),
                          const Spacer(),
                          if (scan.severityCounts != null && scan.status == ScanStatus.completed) ...[
                            const Icon(Icons.bug_report_outlined, size: 16, color: VulnaraColors.onSurfaceVariant),
                            const SizedBox(width: 4),
                            Text('${scan.severityCounts!.total} Vulns',
                                style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                            const SizedBox(width: 12),
                          ],
                          const Icon(Icons.arrow_forward, size: 20, color: VulnaraColors.onSurfaceVariant),
                        ],
                      ),
                      if (scan.status == ScanStatus.inProgress) ...[
                        const SizedBox(height: VulnaraSpacing.stackMd),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(VulnaraRadius.full),
                          child: const LinearProgressIndicator(
                            value: null,
                            minHeight: 4,
                            backgroundColor: VulnaraColors.surfaceContainerHighest,
                            valueColor: AlwaysStoppedAnimation(VulnaraColors.primary),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

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
            Text(message, textAlign: TextAlign.center, style: VulnaraFonts.bodyBase()),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
