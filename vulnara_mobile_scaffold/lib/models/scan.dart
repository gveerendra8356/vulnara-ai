// models/scan.dart -- matches API contract 2.1/2.2 shapes.

class SeverityCounts {
  const SeverityCounts({
    required this.critical,
    required this.high,
    required this.medium,
    required this.low,
    required this.info,
  });

  final int critical;
  final int high;
  final int medium;
  final int low;
  final int info;

  int get total => critical + high + medium + low + info;

  factory SeverityCounts.fromJson(Map<String, dynamic> json) => SeverityCounts(
        critical: json['CRITICAL'] as int? ?? 0,
        high: json['HIGH'] as int? ?? 0,
        medium: json['MEDIUM'] as int? ?? 0,
        low: json['LOW'] as int? ?? 0,
        info: json['INFO'] as int? ?? 0,
      );

  static const zero = SeverityCounts(critical: 0, high: 0, medium: 0, low: 0, info: 0);
}

/// Status values per contract 2.2: PENDING|IN_PROGRESS|COMPLETED|FAILED|CANCELLED
enum ScanStatus { pending, inProgress, completed, failed, cancelled;

  /// Parses the backend status string defensively. The match is
  /// case-insensitive and tolerant of the common spelling variants
  /// (`RUNNING`, `COMPLETE`, `DONE`, `SUCCESS`, `CANCELED`, …) so a
  /// completed scan can never silently fall through to PENDING just
  /// because of a casing/format mismatch between the API and the app.
  static ScanStatus fromApi(String v) {
    switch (v.trim().toUpperCase().replaceAll('-', '_').replaceAll(' ', '_')) {
      case 'PENDING':
      case 'QUEUED':
      case 'CREATED':
        return ScanStatus.pending;
      case 'IN_PROGRESS':
      case 'INPROGRESS':
      case 'RUNNING':
      case 'SCANNING':
      case 'STARTED':
        return ScanStatus.inProgress;
      case 'COMPLETED':
      case 'COMPLETE':
      case 'DONE':
      case 'SUCCESS':
      case 'SUCCEEDED':
      case 'FINISHED':
        return ScanStatus.completed;
      case 'FAILED':
      case 'FAILURE':
      case 'ERROR':
        return ScanStatus.failed;
      case 'CANCELLED':
      case 'CANCELED':
      case 'ABORTED':
        return ScanStatus.cancelled;
      default:
        return ScanStatus.pending;
    }
  }
}

class Scan {
  Scan({
    required this.scanId,
    required this.target,
    required this.status,
    required this.activeTestingEnabled,
    required this.createdAt,
    this.severityCounts,
    this.userEmail,
    this.userFullName,
    this.userRole,
  });

  final String scanId;
  final String target;
  final ScanStatus status;
  final bool activeTestingEnabled;
  final DateTime createdAt;
  /// Null on the list endpoint (2.3), populated on the detail endpoint (2.2).
  final SeverityCounts? severityCounts;
  /// Admin-only: populated when admin fetches all scans with attribution.
  final String? userEmail;
  final String? userFullName;
  final String? userRole;

  factory Scan.fromJson(Map<String, dynamic> json) => Scan(
        scanId: json['scan_id'] as String,
        target: json['target'] as String,
        status: ScanStatus.fromApi(json['status'] as String),
        activeTestingEnabled: json['active_testing_enabled'] as bool? ?? false,
        createdAt: DateTime.parse(json['created_at'] as String),
        severityCounts: json['vuln_count_by_severity'] != null
            ? SeverityCounts.fromJson(json['vuln_count_by_severity'] as Map<String, dynamic>)
            : null,
        userEmail: json['user_email'] as String?,
        userFullName: json['user_full_name'] as String?,
        userRole: json['user_role'] as String?,
      );
}

