// providers/scan_status_provider.dart
//
// Owns the WebSocketService for one scan and folds incoming events into
// the "simplified threat summary" the mobile scope calls for: live
// status/progress, running severity counts, and a capped list of the
// top findings (critical-first) -- not the full paginated threat
// matrix, which stays a web-only view per the confirmed scope.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/websocket_service.dart';
import '../models/scan.dart';
import '../models/vulnerability.dart';
import '../models/ws_event.dart';
import 'core_providers.dart';

class ScanStatusState {
  const ScanStatusState({
    required this.status,
    required this.severityCounts,
    required this.reconPercent,
    required this.topFindings,
    this.errorMessage,
  });

  final ScanStatus status;
  final SeverityCounts severityCounts;
  final int? reconPercent;
  final List<VulnerabilitySummary> topFindings;
  final String? errorMessage;

  static const _severityRank = {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'INFO': 4};

  static const initial = ScanStatusState(
    status: ScanStatus.pending,
    severityCounts: SeverityCounts.zero,
    reconPercent: null,
    topFindings: [],
  );

  ScanStatusState copyWith({
    ScanStatus? status,
    SeverityCounts? severityCounts,
    int? reconPercent,
    List<VulnerabilitySummary>? topFindings,
    String? errorMessage,
  }) {
    return ScanStatusState(
      status: status ?? this.status,
      severityCounts: severityCounts ?? this.severityCounts,
      reconPercent: reconPercent ?? this.reconPercent,
      topFindings: topFindings ?? this.topFindings,
      errorMessage: errorMessage ?? this.errorMessage,
    );
  }
}

class ScanStatusNotifier extends StateNotifier<ScanStatusState> {
  ScanStatusNotifier(this._ref, this._scanId) : super(ScanStatusState.initial) {
    _init();
  }

  final Ref _ref;
  final String _scanId;
  WebSocketService? _ws;

  static const _maxTopFindings = 5;

  Future<void> _init() async {
    // Seed with the current server state first (contract 2.2) so the
    // screen isn't blank while the socket handshake is in flight.
    try {
      final scan = await _ref.read(scanRepositoryProvider).getScan(_scanId);
      state = state.copyWith(
        status: scan.status,
        severityCounts: scan.severityCounts ?? SeverityCounts.zero,
      );
      if (scan.status == ScanStatus.completed ||
          scan.status == ScanStatus.failed ||
          scan.status == ScanStatus.cancelled) {
        return; // scan is already done -- no point opening a socket
      }
    } catch (_) {
      // Fall through and still try the socket -- REST hiccup shouldn't
      // block live updates if the socket itself works.
    }

    final token = await _ref.read(secureStorageProvider).accessToken;
    if (token == null) return;

    _ws = WebSocketService(scanId: _scanId, accessToken: token)..connect();
    _ws!.events.listen(_handleEvent, onDone: () {
      // Contract: server closes with 4001 on auth/ownership failure.
      // We don't have the close code surfaced by web_socket_channel by
      // default here, so we just leave the last-known state on screen
      // rather than guessing at an error -- REST (scanDetailProvider)
      // remains available as a manual-refresh fallback.
    });
  }

  void _handleEvent(WsEvent event) {
    switch (event.event) {
      case WsEvents.scanStatusChanged:
        state = state.copyWith(status: ScanStatus.fromApi(event.data['status'] as String));
      case WsEvents.reconProgress:
        state = state.copyWith(reconPercent: event.data['percent_complete'] as int?);
      case WsEvents.vulnerabilityDiscovered:
        _addFinding(VulnerabilitySummary.fromJson(event.data));
      case WsEvents.alertCritical:
        // vulnerability.discovered already arrived (or will) with the
        // full summary shape; alert.critical only carries a `summary`
        // string for the push notification, so it's not folded into
        // topFindings again here -- avoids a duplicate/partial entry.
        break;
      case WsEvents.scanCompleted:
        state = state.copyWith(
          status: ScanStatus.completed,
          severityCounts: SeverityCounts.fromJson(
            event.data['vuln_count_by_severity'] as Map<String, dynamic>,
          ),
        );
      case WsEvents.scanFailed:
        state = state.copyWith(
          status: ScanStatus.failed,
          errorMessage: event.data['error_message'] as String?,
        );
    }
  }

  void _addFinding(VulnerabilitySummary finding) {
    final updated = [...state.topFindings, finding]
      ..sort((a, b) {
        final rankA = ScanStatusState._severityRank[a.severity] ?? 5;
        final rankB = ScanStatusState._severityRank[b.severity] ?? 5;
        return rankA.compareTo(rankB);
      });
    state = state.copyWith(
      topFindings: updated.take(_maxTopFindings).toList(),
      severityCounts: _bumpCount(state.severityCounts, finding.severity),
    );
  }

  SeverityCounts _bumpCount(SeverityCounts counts, String severity) {
    return SeverityCounts(
      critical: counts.critical + (severity == 'CRITICAL' ? 1 : 0),
      high: counts.high + (severity == 'HIGH' ? 1 : 0),
      medium: counts.medium + (severity == 'MEDIUM' ? 1 : 0),
      low: counts.low + (severity == 'LOW' ? 1 : 0),
      info: counts.info + (severity == 'INFO' ? 1 : 0),
    );
  }

  @override
  void dispose() {
    _ws?.dispose();
    super.dispose();
  }
}

final scanStatusProvider = StateNotifierProvider.autoDispose
    .family<ScanStatusNotifier, ScanStatusState, String>((ref, scanId) {
  return ScanStatusNotifier(ref, scanId);
});
