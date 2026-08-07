// providers/scan_providers.dart -- scan list + single-scan REST state.
// Live in-progress updates are a separate concern, see
// scan_status_provider.dart (WebSocket-driven).

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/scan.dart';
import 'core_providers.dart';

/// Home screen list. `.refresh()` (via ref.invalidate) is called after
/// returning from NewScanScreen so a freshly created scan shows up
/// immediately without a manual pull-to-refresh.
final scanListProvider = FutureProvider.autoDispose<List<Scan>>((ref) async {
  return ref.watch(scanRepositoryProvider).listScans();
});

/// One-shot detail fetch (contract 2.2) -- used for the initial paint of
/// ScanStatusScreen before the WebSocket stream takes over for live
/// updates, and as a fallback if the socket never connects.
final scanDetailProvider = FutureProvider.autoDispose.family<Scan, String>((ref, scanId) async {
  return ref.watch(scanRepositoryProvider).getScan(scanId);
});
