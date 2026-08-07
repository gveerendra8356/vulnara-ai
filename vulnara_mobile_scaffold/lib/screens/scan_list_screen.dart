// screens/scan_list_screen.dart -- build order item 3 (home). Entry
// point after login: scan history + FAB into NewScanScreen.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../models/scan.dart';
import '../providers/auth_provider.dart';
import '../providers/scan_providers.dart';

class ScanListScreen extends ConsumerWidget {
  const ScanListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scansAsync = ref.watch(scanListProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Scans'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authProvider.notifier).logout(),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final created = await context.push<bool>('/scans/new');
          if (created == true) ref.invalidate(scanListProvider);
        },
        icon: const Icon(Icons.add),
        label: const Text('New scan'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(scanListProvider),
        child: scansAsync.when(
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, _) => _ErrorView(message: err.toString(), onRetry: () => ref.invalidate(scanListProvider)),
          data: (scans) {
            if (scans.isEmpty) {
              return LayoutBuilder(
                builder: (context, constraints) => SingleChildScrollView(
                  physics: const AlwaysScrollableScrollPhysics(),
                  child: SizedBox(
                    height: constraints.maxHeight,
                    child: const Center(child: Text('No scans yet -- tap "New scan" to start one.')),
                  ),
                ),
              );
            }
            return ListView.separated(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: scans.length,
              separatorBuilder: (_, __) => const Divider(height: 1),
              itemBuilder: (context, index) => _ScanTile(scan: scans[index]),
            );
          },
        ),
      ),
    );
  }
}

class _ScanTile extends StatelessWidget {
  const _ScanTile({required this.scan});

  final Scan scan;

  Color _statusColor(ScanStatus status) => switch (status) {
        ScanStatus.completed => Colors.green,
        ScanStatus.failed => Colors.red,
        ScanStatus.cancelled => Colors.grey,
        ScanStatus.inProgress => Colors.blue,
        ScanStatus.pending => Colors.orange,
      };

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: CircleAvatar(
        backgroundColor: _statusColor(scan.status).withValues(alpha: 0.15),
        child: Icon(Icons.dns_outlined, color: _statusColor(scan.status), size: 20),
      ),
      title: Text(scan.target),
      subtitle: Text('${scan.status.name} · ${DateFormat.yMMMd().add_jm().format(scan.createdAt.toLocal())}'),
      trailing: const Icon(Icons.chevron_right),
      onTap: () => context.push('/scans/${scan.scanId}'),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: const Text('Retry')),
          ],
        ),
      ),
    );
  }
}
