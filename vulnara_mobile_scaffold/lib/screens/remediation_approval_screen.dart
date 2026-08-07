// screens/remediation_approval_screen.dart -- build order item 6b: the
// lightweight approve/reject screen. Deliberately shows only the
// executive_summary, not technical_script -- full script review is a
// web-only surface per the confirmed mobile scope ("remediation
// already reviewed on web"); this screen just records the decision.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/api_exception.dart';
import '../models/remediation.dart';
import '../providers/core_providers.dart';
import '../providers/remediation_providers.dart';

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
      appBar: AppBar(title: const Text('Review remediation')),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(err.toString())),
        data: (remediation) => _buildContent(context, remediation),
      ),
    );
  }

  Widget _buildContent(BuildContext context, Remediation remediation) {
    final alreadyDecided = remediation.status != RemediationStatus.pending;

    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Confidence: ${(remediation.aiConfidence * 100).round()}%',
                style: Theme.of(context).textTheme.bodySmall),
            if (remediation.targetOs != null)
              Text('Target OS: ${remediation.targetOs}', style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 16),
            Text('Executive summary', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(remediation.executiveSummary),
            const SizedBox(height: 8),
            const Divider(),
            const SizedBox(height: 4),
            Text(
              'Full technical script review happens on the web dashboard. '
              'Only approve here if that review has already been done.',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(fontStyle: FontStyle.italic),
            ),
            const SizedBox(height: 24),
            if (alreadyDecided)
              Text('Already ${remediation.status.name}.', style: Theme.of(context).textTheme.titleMedium)
            else ...[
              if (_error != null) ...[
                Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                const SizedBox(height: 12),
              ],
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _submitting ? null : () => _decide(approve: false),
                      child: const Text('Reject'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: FilledButton(
                      onPressed: _submitting ? null : () => _decide(approve: true),
                      child: _submitting
                          ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                          : const Text('Approve'),
                    ),
                  ),
                ],
              ),
            ],
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
}
