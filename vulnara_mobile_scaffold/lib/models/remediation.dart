// models/remediation.dart -- matches API contract 5.1/5.2 shapes.
// Mobile's approve/reject screen uses this for the "lightweight summary"
// view -- executive_summary only, not a full script viewer/diff (that's
// the web reviewer's job per the confirmed mobile scope).

enum RemediationStatus { pending, approved, rejected, executed;

  static RemediationStatus fromApi(String v) => switch (v) {
        'PENDING' => RemediationStatus.pending,
        'APPROVED' => RemediationStatus.approved,
        'REJECTED' => RemediationStatus.rejected,
        'EXECUTED' => RemediationStatus.executed,
        _ => RemediationStatus.pending,
      };
}

class Remediation {
  Remediation({
    required this.remediationId,
    required this.vulnId,
    required this.executiveSummary,
    required this.technicalScript,
    required this.aiConfidence,
    required this.status,
    required this.createdAt,
    this.targetOs,
  });

  final String remediationId;
  final String vulnId;
  final String? targetOs;
  final String executiveSummary;
  final String technicalScript;
  final double aiConfidence;
  final RemediationStatus status;
  final DateTime createdAt;

  factory Remediation.fromJson(Map<String, dynamic> json) => Remediation(
        remediationId: json['remediation_id'] as String,
        vulnId: json['vuln_id'] as String,
        targetOs: json['target_os'] as String?,
        executiveSummary: json['executive_summary'] as String,
        technicalScript: json['technical_script'] as String,
        aiConfidence: (json['ai_confidence'] as num).toDouble(),
        status: RemediationStatus.fromApi(json['status'] as String),
        createdAt: DateTime.parse(json['created_at'] as String),
      );
}
