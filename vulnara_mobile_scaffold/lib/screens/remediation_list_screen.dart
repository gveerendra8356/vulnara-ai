// screens/remediation_list_screen.dart -- build order item 6a: shows
// remediations for a scan that are PENDING a decision. Uses contract
// 5.3 (`GET /scans/{scan_id}/remediations`) -- see the note in
// remediation_repository.dart about why mobile is allowed to call this
// despite its "Client: Web" label in the contract doc.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/remediation_providers.dart';

class RemediationListScreen extends ConsumerWidget {
  const RemediationListScreen({super.key, required this.scanId});

  final String scanId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final remediationsAsync = ref.watch(pendingRemediationsProvider(scanId));

    return Scaffold(
      appBar: AppBar(title: const Text('Pending remediations')),
      body: remediationsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, _) => Center(child: Text(err.toString())),
        data: (remediations) {
          if (remediations.isEmpty) {
            return const Center(child: Text('Nothing awaiting review for this scan.'));
          }
          return ListView.separated(
            itemCount: remediations.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (context, index) {
              final r = remediations[index];
              return ListTile(
                title: Text(r.targetOs ?? 'Remediation'),
                subtitle: Text(
                  r.executiveSummary,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: Text('${(r.aiConfidence * 100).round()}% conf.'),
                onTap: () async {
                  final decided = await context.push<bool>('/remediations/${r.remediationId}');
                  if (decided == true) ref.invalidate(pendingRemediationsProvider(scanId));
                },
              );
            },
          );
        },
      ),
    );
  }
}
