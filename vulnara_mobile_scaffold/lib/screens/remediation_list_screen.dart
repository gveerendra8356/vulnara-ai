// screens/remediation_list_screen.dart -- build order item 6a: shows
// remediations for a scan that are PENDING a decision.
//
// No dedicated Stitch mock exists for this list (only the single-item
// "remediation_review" screen does) -- styled to match the same design
// system (glass cards, mono labels, primary accents) used everywhere
// else so it reads as part of the same app.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/remediation_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/glass_panel.dart';
import '../widgets/vulnara_app_bar.dart';

class RemediationListScreen extends ConsumerWidget {
  const RemediationListScreen({super.key, required this.scanId});

  final String scanId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final remediationsAsync = ref.watch(pendingRemediationsProvider(scanId));

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      appBar: VulnaraAppBar(
        showWordmark: false,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: VulnaraColors.onSurfaceVariant),
          onPressed: () => context.pop(),
        ),
        actions: const [VulnaraAvatar()],
      ),
      body: SafeArea(
        child: remediationsAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => Center(child: Text(err.toString(), style: VulnaraFonts.bodyBase())),
          data: (remediations) {
            return CustomScrollView(
              slivers: [
                SliverPadding(
                  padding: const EdgeInsets.fromLTRB(
                    VulnaraSpacing.containerPadding,
                    24,
                    VulnaraSpacing.containerPadding,
                    0,
                  ),
                  sliver: SliverToBoxAdapter(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Pending Remediations', style: VulnaraFonts.headlineMd()),
                        const SizedBox(height: 8),
                        Text(
                          'Fixes awaiting an analyst decision for this scan.',
                          style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                        ),
                        const SizedBox(height: VulnaraSpacing.stackLg),
                      ],
                    ),
                  ),
                ),
                if (remediations.isEmpty)
                  SliverFillRemaining(
                    hasScrollBody: false,
                    child: Center(
                      child: Text(
                        'Nothing awaiting review for this scan.',
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
                      32,
                    ),
                    sliver: SliverList.separated(
                      itemCount: remediations.length,
                      separatorBuilder: (_, __) => const SizedBox(height: VulnaraSpacing.stackMd),
                      itemBuilder: (context, index) {
                        final r = remediations[index];
                        return Material(
                          color: Colors.transparent,
                          child: InkWell(
                            borderRadius: BorderRadius.circular(VulnaraRadius.xl),
                            onTap: () async {
                              final decided = await context.push<bool>('/remediations/${r.remediationId}');
                              if (decided == true) ref.invalidate(pendingRemediationsProvider(scanId));
                            },
                            child: GlassPanel(
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(r.targetOs ?? 'Remediation',
                                            style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w700)),
                                        const SizedBox(height: 4),
                                        Text(
                                          r.executiveSummary,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                                        ),
                                        const SizedBox(height: 8),
                                        VulnaraChip(
                                          label: '${(r.aiConfidence * 100).round()}% AI CONFIDENCE',
                                          color: VulnaraColors.primary,
                                          icon: Icons.psychology_outlined,
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  const Icon(Icons.chevron_right, color: VulnaraColors.onSurfaceVariant),
                                ],
                              ),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
