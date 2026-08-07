// providers/remediation_providers.dart -- backs the "remediations
// awaiting my decision" list and the single-remediation approve/reject
// screen (contract 5.2, 5.3, 5.4, 5.5).

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/remediation.dart';
import 'core_providers.dart';

final pendingRemediationsProvider =
    FutureProvider.autoDispose.family<List<Remediation>, String>((ref, scanId) async {
  return ref.watch(remediationRepositoryProvider).listForScan(scanId, status: 'PENDING');
});

final remediationDetailProvider =
    FutureProvider.autoDispose.family<Remediation, String>((ref, remediationId) async {
  return ref.watch(remediationRepositoryProvider).getRemediation(remediationId);
});
