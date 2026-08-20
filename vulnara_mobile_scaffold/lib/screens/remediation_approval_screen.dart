// screens/remediation_approval_screen.dart -- build order item 6b: the
// approve/reject screen for a single remediation.
//
// UI matches the Stitch "remediation_review" mock: severity + status
// pills, an executive-summary panel, a "Remediation Actions" panel, and
// a terminal-style code viewer for the generated script.
//
// Design note: the mock's action panel shows "Approve Fix (Analyst)"
// and "Mark Executed (Client)" -- the latter implies a post-approval
// CI/CD execution step that isn't part of this API's scope (contract
// 5.4/5.5 only expose approve/reject). "Approve Fix" is wired to the
// real approve call; "Mark Executed" is kept visually but disabled
// until the remediation is actually approved, and a lightweight Reject
// action is added beneath so the decision this screen exists for is
// still reachable.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/api_exception.dart';
import '../models/remediation.dart';
import '../providers/auth_provider.dart';
import '../providers/core_providers.dart';
import '../providers/remediation_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/glass_panel.dart';
import '../widgets/vulnara_app_bar.dart';

class RemediationApprovalScreen extends ConsumerStatefulWidget {
  const RemediationApprovalScreen({super.key, required this.remediationId});

  final String remediationId;

  @override
  ConsumerState<RemediationApprovalScreen> createState() => _RemediationApprovalScreenState();
}

class _RemediationApprovalScreenState extends ConsumerState<RemediationApprovalScreen> {
  bool _submitting = false;
  String? _error;

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(remediationDetailProvider(widget.remediationId));

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
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(err.toString(), style: VulnaraFonts.bodyBase())),
        data: (remediation) => _buildContent(context, remediation),
      ),
    );
  }

  Widget _buildContent(BuildContext context, Remediation remediation) {
    final authState = ref.read(authProvider);
    final user = authState is AuthLoggedIn ? authState.user : null;
    final isClient = user?.role == 'client';

    final isPending = remediation.status == RemediationStatus.pending;
    final isApproved = remediation.status == RemediationStatus.approved;
    final alreadyDecided = remediation.status != RemediationStatus.pending;

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(
          VulnaraSpacing.containerPadding,
          16,
          VulnaraSpacing.containerPadding,
          32,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('ID: ${remediation.remediationId}', style: VulnaraFonts.labelCaps()),
            const SizedBox(height: 4),
            Text('Remediation Review', style: VulnaraFonts.headlineMd()),
            const SizedBox(height: VulnaraSpacing.stackSm),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                VulnaraChip(label: 'CONFIDENCE ${(remediation.aiConfidence * 100).round()}%',
                    color: VulnaraColors.primary, icon: Icons.psychology),
                if (remediation.targetOs != null)
                  VulnaraChip(label: remediation.targetOs!.toUpperCase(), color: VulnaraColors.onSurfaceVariant),
                VulnaraChip(
                  label: switch (remediation.status) {
                    RemediationStatus.pending => 'PENDING APPROVAL',
                    RemediationStatus.approved => 'APPROVED',
                    RemediationStatus.rejected => 'REJECTED',
                    RemediationStatus.executed => 'EXECUTED',
                  },
                  color: alreadyDecided ? VulnaraColors.secondaryFixedDim : VulnaraColors.onSurfaceVariant,
                ),
              ],
            ),
            const SizedBox(height: VulnaraSpacing.stackLg),
            GlassPanel(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.subject, size: 16, color: VulnaraColors.onSurfaceVariant),
                      const SizedBox(width: 8),
                      Text('EXECUTIVE SUMMARY', style: VulnaraFonts.labelCaps()),
                    ],
                  ),
                  const Divider(height: 24),
                  Text(remediation.executiveSummary, style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w400)),
                ],
              ),
            ),
            const SizedBox(height: VulnaraSpacing.stackMd),
            GlassPanel(
              borderColor: VulnaraColors.primary.withValues(alpha: 0.2),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.gavel, size: 16, color: VulnaraColors.primary),
                      const SizedBox(width: 8),
                      Text('REMEDIATION ACTIONS',
                          style: VulnaraFonts.labelCaps(color: VulnaraColors.primary)),
                    ],
                  ),
                  const Divider(height: 24),
                  if (_error != null) ...[
                    Text(_error!, style: const TextStyle(color: VulnaraColors.error)),
                    const SizedBox(height: 12),
                  ],

                  // ── Clients: read-only status panel ───────────────────────
                  if (isClient) ...[
                    Container(
                      padding: const EdgeInsets.all(14),
                      decoration: BoxDecoration(
                        color: VulnaraColors.surfaceContainerHigh,
                        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                        border: Border.all(color: VulnaraColors.outlineVariant),
                      ),
                      child: Row(
                        children: [
                          const Icon(Icons.info_outline,
                              size: 16, color: VulnaraColors.onSurfaceVariant),
                          const SizedBox(width: 10),
                          Expanded(
                            child: Text(
                              switch (remediation.status) {
                                RemediationStatus.pending =>
                                  'This remediation is awaiting analyst review.',
                                RemediationStatus.approved =>
                                  'Approved by an analyst. Awaiting execution.',
                                RemediationStatus.rejected =>
                                  'This remediation was rejected by an analyst.',
                                RemediationStatus.executed =>
                                  'Executed successfully.',
                              },
                              style: VulnaraFonts.codeSm(
                                  color: VulnaraColors.onSurfaceVariant),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ]

                  // ── Analyst / Admin: full action panel ────────────────────
                  else if (remediation.status == RemediationStatus.rejected ||
                      remediation.status == RemediationStatus.executed)
                    Text('Already ${remediation.status.name}.',
                        style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w600))
                  else ...[
                    // Approve button (analyst/admin only)
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: ElevatedButton.icon(
                        onPressed:
                            (_submitting || !isPending) ? null : () => _decide(approve: true),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: VulnaraColors.primaryContainer,
                          foregroundColor: Colors.white,
                          elevation: 0,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                        ),
                        icon: (_submitting && isPending)
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.check_circle),
                        label: const Text('Approve Fix'),
                      ),
                    ),
                    const SizedBox(height: 12),
                    // Mark Executed (once approved)
                    SizedBox(
                      width: double.infinity,
                      height: 48,
                      child: OutlinedButton.icon(
                        onPressed: (_submitting || !isApproved) ? null : _execute,
                        style: OutlinedButton.styleFrom(
                          foregroundColor: VulnaraColors.onSurfaceVariant,
                          side: const BorderSide(color: VulnaraColors.outlineVariant),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                        ),
                        icon: (_submitting && isApproved)
                            ? const SizedBox(
                                height: 16,
                                width: 16,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                    color: VulnaraColors.onSurfaceVariant))
                            : const Icon(Icons.play_arrow),
                        label: const Text('Mark Executed'),
                      ),
                    ),
                    if (isPending) ...[
                      const SizedBox(height: 8),
                      Center(
                        child: TextButton(
                          onPressed:
                              _submitting ? null : () => _decide(approve: false),
                          child: Text('Reject remediation',
                              style: VulnaraFonts.codeSm(color: VulnaraColors.error)),
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Requires dual-authorization before automated deployment via CI/CD.',
                        textAlign: TextAlign.center,
                        style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)
                            .copyWith(fontSize: 11),
                      ),
                    ],
                  ],
                ],
              ),
            ),
            const SizedBox(height: VulnaraSpacing.stackMd),
            _CodeViewer(filename: 'remediation_script.py', code: remediation.technicalScript),
          ],
        ),
      ),
    );
  }

  Future<void> _decide({required bool approve}) async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final repo = ref.read(remediationRepositoryProvider);
      if (approve) {
        await repo.approve(widget.remediationId);
      } else {
        await repo.reject(widget.remediationId);
      }
      if (mounted) context.pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _execute() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final repo = ref.read(remediationRepositoryProvider);
      await repo.execute(widget.remediationId);
      if (mounted) context.pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class _CodeViewer extends StatelessWidget {
  const _CodeViewer({required this.filename, required this.code});

  final String filename;
  final String code;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(VulnaraRadius.xl),
      child: Container(
        decoration: BoxDecoration(border: Border.all(color: Colors.white.withValues(alpha: 0.1))),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              color: VulnaraColors.surfaceContainerHighest,
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              child: Row(
                children: [
                  const Icon(Icons.terminal, size: 16, color: VulnaraColors.onSurfaceVariant),
                  const SizedBox(width: 8),
                  Text(filename, style: VulnaraFonts.labelCaps()),
                  const Spacer(),
                  IconButton(
                    visualDensity: VisualDensity.compact,
                    icon: const Icon(Icons.copy, size: 16, color: VulnaraColors.onSurfaceVariant),
                    tooltip: 'Copy to clipboard',
                    onPressed: () => Clipboard.setData(ClipboardData(text: code)),
                  ),
                ],
              ),
            ),
            Container(
              width: double.infinity,
              constraints: const BoxConstraints(maxHeight: 360),
              color: const Color(0xE60A0A0A),
              padding: const EdgeInsets.all(14),
              child: SingleChildScrollView(
                child: SelectableText(
                  code.isEmpty ? '# No script generated yet.' : code,
                  style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface).copyWith(height: 1.6),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
