// repositories/notification_repository.dart
//
// Synthesises the Alerts Hub feed from two real backend endpoints:
//
//   GET /scans        → each COMPLETED or FAILED scan becomes a notification;
//                       a scan with vuln_count_by_severity.CRITICAL > 0 also
//                       yields a criticalVuln alert (we use the detail endpoint
//                       for that because the list response doesn't carry counts).
//
//   GET /remediations → PENDING → remediationPending
//                       APPROVED → remediationApproved
//                       EXECUTED → remediationExecuted
//
// Items are sorted newest-first by their source timestamp before returning.

import '../models/app_notification.dart';
import '../models/remediation.dart';
import '../models/scan.dart';
import 'remediation_repository.dart';
import 'scan_repository.dart';

class NotificationRepository {
  NotificationRepository(this._scanRepo, this._remRepo);

  final ScanRepository _scanRepo;
  final RemediationRepository _remRepo;

  Future<List<AppNotification>> fetchNotifications() async {
    // Fetch both in parallel; let individual failures propagate.
    final results = await Future.wait([
      _scanRepo.listScans(),
      _remRepo.listRemediations(),
    ]);

    final scans = results[0] as List<Scan>;
    final remediations = results[1] as List<Remediation>;

    final notifications = <AppNotification>[];

    // ── Scan-derived alerts ────────────────────────────────────────────────
    for (final scan in scans) {
      if (scan.status == ScanStatus.completed) {
        // If we already have severity counts (admin/analyst view), check crits.
        final counts = scan.severityCounts;
        if (counts != null && counts.critical > 0) {
          notifications.add(AppNotification(
            id: 'crit-${scan.scanId}',
            kind: AppNotificationKind.criticalVuln,
            title: 'Critical Vulnerability Detected',
            body: '${counts.critical} critical finding${counts.critical > 1 ? 's' : ''} '
                'on target ${scan.target}. Immediate review recommended.',
            timestamp: scan.createdAt,
          ));
        }

        notifications.add(AppNotification(
          id: 'scan-done-${scan.scanId}',
          kind: AppNotificationKind.scanCompleted,
          title: 'Scan Completed',
          body: 'Scan of ${scan.target} finished successfully'
              '${counts != null ? ' with ${counts.total} finding${counts.total != 1 ? 's' : ''}' : ''}.',
          timestamp: scan.createdAt,
        ));
      } else if (scan.status == ScanStatus.failed) {
        notifications.add(AppNotification(
          id: 'scan-fail-${scan.scanId}',
          kind: AppNotificationKind.scanFailed,
          title: 'Scan Failed',
          body: 'The scan of ${scan.target} encountered an error and did not complete.',
          timestamp: scan.createdAt,
        ));
      }
    }

    // ── Remediation-derived alerts ─────────────────────────────────────────
    for (final rem in remediations) {
      switch (rem.status) {
        case RemediationStatus.pending:
          notifications.add(AppNotification(
            id: 'rem-pending-${rem.remediationId}',
            kind: AppNotificationKind.remediationPending,
            title: 'Remediation Awaiting Review',
            body: rem.executiveSummary.length > 120
                ? '${rem.executiveSummary.substring(0, 120)}…'
                : rem.executiveSummary,
            timestamp: rem.createdAt,
          ));
        case RemediationStatus.approved:
          notifications.add(AppNotification(
            id: 'rem-approved-${rem.remediationId}',
            kind: AppNotificationKind.remediationApproved,
            title: 'Remediation Approved',
            body: rem.executiveSummary.length > 120
                ? '${rem.executiveSummary.substring(0, 120)}…'
                : rem.executiveSummary,
            timestamp: rem.createdAt,
          ));
        case RemediationStatus.executed:
          notifications.add(AppNotification(
            id: 'rem-executed-${rem.remediationId}',
            kind: AppNotificationKind.remediationExecuted,
            title: 'Remediation Executed',
            body: rem.executiveSummary.length > 120
                ? '${rem.executiveSummary.substring(0, 120)}…'
                : rem.executiveSummary,
            timestamp: rem.createdAt,
          ));
        case RemediationStatus.rejected:
          // Rejected remediations are not surfaced as notifications.
          break;
      }
    }

    // Sort newest first.
    notifications.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return notifications;
  }
}
