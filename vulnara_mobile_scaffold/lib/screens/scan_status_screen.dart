// screens/scan_status_screen.dart -- build order item 4: live scan
// status consuming the WebSocket, plus the "simplified threat summary"
// (severity counts + top findings only). Also the entry point into the
// remediation approve/reject flow once a scan is complete.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../models/scan.dart';
import '../models/vulnerability.dart';
import '../providers/scan_status_provider.dart';
import '../widgets/severity_badge.dart';

class ScanStatusScreen extends ConsumerWidget {
  const ScanStatusScreen({super.key, required this.scanId});

  final String scanId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(scanStatusProvider(scanId));

    return Scaffold(
      appBar: AppBar(
        title: Text('Scan ${scanId.substring(0, 8)}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.fact_check_outlined),
            tooltip: 'Pending remediations',
            onPressed: () => context.push('/scans/$scanId/remediations'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _StatusHeader(status: status),
          if (status.status == ScanStatus.inProgress && status.reconPercent != null) ...[
            const SizedBox(height: 16),
            LinearProgressIndicator(value: status.reconPercent! / 100),
            const SizedBox(height: 4),
            Text('Recon: ${status.reconPercent}%', style: Theme.of(context).textTheme.bodySmall),
          ],
          const SizedBox(height: 24),
          Text('Findings by severity', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          _SeverityCountRow(counts: status.severityCounts),
          const SizedBox(height: 24),
          Text('Top findings', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (status.topFindings.isEmpty)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 16),
              child: Text('No findings yet.'),
            )
          else
            ...status.topFindings.map((f) => _FindingTile(finding: f)),
          if (status.errorMessage != null) ...[
            const SizedBox(height: 16),
            Text(status.errorMessage!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
          ],
        ],
      ),
    );
  }
}

class _StatusHeader extends StatelessWidget {
  const _StatusHeader({required this.status});

  final ScanStatusState status;

  @override
  Widget build(BuildContext context) {
    final label = switch (status.status) {
      ScanStatus.pending => 'Pending',
      ScanStatus.inProgress => 'In progress',
      ScanStatus.completed => 'Completed',
      ScanStatus.failed => 'Failed',
      ScanStatus.cancelled => 'Cancelled',
    };
    final color = switch (status.status) {
      ScanStatus.completed => Colors.green,
      ScanStatus.failed => Colors.red,
      ScanStatus.cancelled => Colors.grey,
      ScanStatus.inProgress => Colors.blue,
      ScanStatus.pending => Colors.orange,
    };
    return Row(
      children: [
        Icon(Icons.circle, size: 12, color: color),
        const SizedBox(width: 8),
        Text(label, style: Theme.of(context).textTheme.titleLarge),
        if (status.status == ScanStatus.inProgress) ...[
          const SizedBox(width: 12),
          const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2)),
        ],
      ],
    );
  }
}

class _SeverityCountRow extends StatelessWidget {
  const _SeverityCountRow({required this.counts});

  final SeverityCounts counts;

  @override
  Widget build(BuildContext context) {
    final entries = [
      ('CRITICAL', counts.critical),
      ('HIGH', counts.high),
      ('MEDIUM', counts.medium),
      ('LOW', counts.low),
      ('INFO', counts.info),
    ];
    return Wrap(
      spacing: 12,
      runSpacing: 8,
      children: entries.map((e) {
        return Chip(
          avatar: SeverityBadge(severity: e.$1),
          label: Text('${e.$2}'),
        );
      }).toList(),
    );
  }
}

class _FindingTile extends StatelessWidget {
  const _FindingTile({required this.finding});

  final VulnerabilitySummary finding;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: SeverityBadge(severity: finding.severity),
        title: Text(finding.serviceName ?? 'Unknown service'),
        subtitle: Text('${finding.host}${finding.port != null ? ':${finding.port}' : ''}'),
        trailing: finding.confidenceScore != null
            ? Text('${(finding.confidenceScore! * 100).round()}%')
            : null,
      ),
    );
  }
}
