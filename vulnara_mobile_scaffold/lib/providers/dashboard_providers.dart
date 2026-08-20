// providers/dashboard_providers.dart
//
// Aggregated analytics for the Dashboard screen, computed client-side
// from the two real endpoints available:
//
//   GET /scans        → list of user's scans (list endpoint does NOT return
//                       vuln_count_by_severity, so we fetch each completed
//                       scan's detail to get real severity counts)
//   GET /remediations → all remediations for counting PENDING/APPROVED totals
//
// All heavy lifting is done in the provider so DashboardScreen stays a
// pure layout widget.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/remediation.dart';
import '../models/scan.dart';
import 'core_providers.dart';

// ── Data model ────────────────────────────────────────────────────────────────

class DashboardStats {
  const DashboardStats({
    required this.totalCritical,
    required this.totalHigh,
    required this.totalMedium,
    required this.remediationsPending,
    required this.remediationsApproved,
    required this.totalScans,
    required this.completedScans,
    required this.failedScans,
    required this.inProgressScans,
    required this.recentScans,
    required this.chartSeries,
    required this.chartLabels,
  });

  /// Sum of CRITICAL findings across all completed scans.
  final int totalCritical;

  /// Sum of HIGH findings across all completed scans.
  final int totalHigh;

  /// Sum of MEDIUM findings across all completed scans.
  final int totalMedium;

  /// Number of remediations with status PENDING.
  final int remediationsPending;

  /// Number of remediations with status APPROVED (deployed / executed).
  final int remediationsApproved;

  final int totalScans;
  final int completedScans;
  final int failedScans;
  final int inProgressScans;

  /// Up to 5 most recent scans for quick status glance.
  final List<Scan> recentScans;

  /// Daily total-vuln counts for the last 7 calendar days (index 0 = oldest).
  /// Derived from completed scan `createdAt` + their per-severity totals.
  final List<double> chartSeries;

  /// Human-readable labels for each point in [chartSeries].
  final List<String> chartLabels;

  /// Integrity score: % of scans that completed successfully (0-100).
  int get integrityScore =>
      totalScans == 0 ? 100 : ((completedScans / totalScans) * 100).round();

  /// Scans created in the last 24 hours.
  int get scansLast24h {
    final cutoff = DateTime.now().subtract(const Duration(hours: 24));
    return recentScans
        .where((s) => s.createdAt.isAfter(cutoff))
        .length;
  }
}

// ── Provider ──────────────────────────────────────────────────────────────────

final dashboardStatsProvider =
    FutureProvider.autoDispose<DashboardStats>((ref) async {
  final scanRepo = ref.watch(scanRepositoryProvider);
  final remRepo = ref.watch(remediationRepositoryProvider);

  // Fetch scans and remediations in parallel.
  final results = await Future.wait([
    scanRepo.listScans(),
    remRepo.listRemediations(),
  ]);

  final scans = results[0] as List<Scan>;
  final remediations = results[1] as List<Remediation>;

  // For completed scans that have no severity counts (list endpoint doesn't
  // return them), fetch the detail endpoint in parallel to get real counts.
  final completedWithoutCounts = scans
      .where(
          (s) => s.status == ScanStatus.completed && s.severityCounts == null)
      .toList();

  List<Scan> enriched = [];
  if (completedWithoutCounts.isNotEmpty) {
    final details = await Future.wait(
      completedWithoutCounts.map((s) => scanRepo.getScan(s.scanId)),
    );
    enriched = details;
  }

  // Build a map from scanId → enriched Scan for quick lookup.
  final enrichedMap = {for (final s in enriched) s.scanId: s};

  // Merge: use enriched detail if available, otherwise keep original.
  final mergedScans = scans.map((s) => enrichedMap[s.scanId] ?? s).toList();

  // ── Aggregate severity totals ──────────────────────────────────────────────
  int totalCritical = 0;
  int totalHigh = 0;
  int totalMedium = 0;

  for (final s in mergedScans) {
    if (s.status == ScanStatus.completed && s.severityCounts != null) {
      totalCritical += s.severityCounts!.critical;
      totalHigh += s.severityCounts!.high;
      totalMedium += s.severityCounts!.medium;
    }
  }

  // ── Remediation counts ─────────────────────────────────────────────────────
  final remediationsPending =
      remediations.where((r) => r.status == RemediationStatus.pending).length;
  final remediationsApproved =
      remediations.where((r) => r.status == RemediationStatus.approved).length;

  // ── Scan status counts ─────────────────────────────────────────────────────
  final completedScans =
      mergedScans.where((s) => s.status == ScanStatus.completed).length;
  final failedScans =
      mergedScans.where((s) => s.status == ScanStatus.failed).length;
  final inProgressScans =
      mergedScans.where((s) => s.status == ScanStatus.inProgress).length;

  // ── "Threats Over Time" — last 7 days, bucketted by calendar day ──────────
  // We bucket the sum of (critical + high) per completed scan into the day
  // it was created. This is the best approximation without a dedicated
  // analytics endpoint.
  final now = DateTime.now();
  final dayBuckets = List<double>.filled(7, 0);

  for (final s in mergedScans) {
    if (s.status != ScanStatus.completed) continue;
    final counts = s.severityCounts;
    if (counts == null) continue;
    final daysAgo = now
        .difference(DateTime(s.createdAt.year, s.createdAt.month, s.createdAt.day))
        .inDays;
    if (daysAgo >= 0 && daysAgo < 7) {
      // Index 0 = oldest (6 days ago), index 6 = today.
      dayBuckets[6 - daysAgo] += (counts.critical + counts.high).toDouble();
    }
  }

  // Build labels: "Mon", "Tue", … → actual weekday names for last 7 days.
  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  final labels = List.generate(7, (i) {
    final day = now.subtract(Duration(days: 6 - i));
    return i == 6 ? 'Today' : weekdays[day.weekday - 1];
  });

  return DashboardStats(
    totalCritical: totalCritical,
    totalHigh: totalHigh,
    totalMedium: totalMedium,
    remediationsPending: remediationsPending,
    remediationsApproved: remediationsApproved,
    totalScans: mergedScans.length,
    completedScans: completedScans,
    failedScans: failedScans,
    inProgressScans: inProgressScans,
    recentScans: mergedScans.take(5).toList(),
    chartSeries: dayBuckets,
    chartLabels: labels,
  );
});
