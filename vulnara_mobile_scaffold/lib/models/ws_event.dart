// models/ws_event.dart -- the WebSocket message envelope from API
// contract section 7: { event, scan_id, timestamp, data }.
//
// Kept as a thin envelope + raw `data` map rather than a sealed class
// per event type -- screens/providers pattern-match on `.event` and
// parse `.data` themselves (e.g. VulnerabilitySummary.fromJson(event.data)
// for `vulnerability.discovered`). Simpler than maintaining 7 parallel
// classes for what's ultimately a small, stable set of message shapes.

class WsEvent {
  WsEvent({required this.event, required this.scanId, required this.timestamp, required this.data});

  final String event;
  final String scanId;
  final DateTime timestamp;
  final Map<String, dynamic> data;

  factory WsEvent.fromJson(Map<String, dynamic> json) => WsEvent(
        event: json['event'] as String,
        scanId: json['scan_id'] as String? ?? '',
        timestamp: json['timestamp'] != null
            ? DateTime.parse(json['timestamp'] as String)
            : DateTime.now(),
        data: (json['data'] as Map?)?.cast<String, dynamic>() ?? const {},
      );
}

/// Event name constants -- avoids typo'd string literals scattered
/// through provider/screen code.
class WsEvents {
  WsEvents._();
  static const scanStatusChanged = 'scan.status_changed';
  static const reconProgress = 'recon.progress';
  static const vulnerabilityDiscovered = 'vulnerability.discovered';
  static const alertCritical = 'alert.critical';
  static const activeTestAttempt = 'active_test.attempt';
  static const scanCompleted = 'scan.completed';
  static const scanFailed = 'scan.failed';
  static const pong = 'pong';
}
