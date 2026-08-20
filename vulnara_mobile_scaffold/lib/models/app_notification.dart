// models/app_notification.dart
//
// A client-side notification item synthesised from real backend data
// (scans + remediations). The backend has no dedicated /notifications
// endpoint, so NotificationRepository assembles this feed locally from:
//   • GET /scans          → completed / failed scans
//   • GET /remediations   → approved, pending, executed remediations

enum AppNotificationKind {
  /// A new CRITICAL severity vulnerability was found in the user's scan.
  criticalVuln,

  /// A scan reached COMPLETED status.
  scanCompleted,

  /// A scan reached FAILED status.
  scanFailed,

  /// A remediation has been approved by an analyst.
  remediationApproved,

  /// A remediation is awaiting analyst review.
  remediationPending,

  /// A remediation has been executed.
  remediationExecuted,
}

class AppNotification {
  const AppNotification({
    required this.id,
    required this.kind,
    required this.title,
    required this.body,
    required this.timestamp,
  });

  /// Stable identifier (e.g. scan_id or remediation_id from the source object).
  final String id;
  final AppNotificationKind kind;
  final String title;
  final String body;
  final DateTime timestamp;

  bool get isCritical => kind == AppNotificationKind.criticalVuln;
}
