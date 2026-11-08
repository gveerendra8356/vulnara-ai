// screens/scheduled_scans_screen.dart -- recurring scans (continuous
// monitoring). Create a schedule, pause/resume, or delete. Mirrors the web
// Scheduled Scans page.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/core_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/glass_panel.dart';

final _schedulesProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(organizationRepositoryProvider).listSchedules(),
);

const _intervals = {
  15: 'Every 15 minutes',
  60: 'Hourly',
  360: 'Every 6 hours',
  1440: 'Daily',
  10080: 'Weekly',
};

class ScheduledScansScreen extends ConsumerStatefulWidget {
  const ScheduledScansScreen({super.key});

  @override
  ConsumerState<ScheduledScansScreen> createState() => _ScheduledScansScreenState();
}

class _ScheduledScansScreenState extends ConsumerState<ScheduledScansScreen> {
  final _target = TextEditingController();
  final _justify = TextEditingController();
  int _interval = 1440;
  bool _activeTesting = false;
  bool _authorized = false;
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _target.dispose();
    _justify.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() { _busy = true; _error = null; });
    try {
      await action();
      ref.invalidate(_schedulesProvider);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final schedulesAsync = ref.watch(_schedulesProvider);
    final repo = ref.read(organizationRepositoryProvider);
    final canCreate = _target.text.trim().isNotEmpty && _authorized && _justify.text.trim().length >= 10;

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: VulnaraColors.onSurfaceVariant),
          onPressed: () => context.canPop() ? context.pop() : context.go('/scans'),
        ),
        title: Text('Scheduled Scans', style: VulnaraFonts.headlineMd()),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
            VulnaraSpacing.containerPadding, 8, VulnaraSpacing.containerPadding, 32),
        children: [
          Text(
            'Automatically re-scan a target on a recurring interval. Each run is tagged to your department.',
            style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
          ),
          const SizedBox(height: VulnaraSpacing.stackMd),
          if (_error != null) ...[
            Text(_error!, style: VulnaraFonts.codeSm(color: VulnaraColors.error)),
            const SizedBox(height: 8),
          ],

          GlassPanel(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('NEW SCHEDULE', style: VulnaraFonts.labelCaps()),
              const SizedBox(height: 10),
              _field(_target, 'Target (IP, domain or URL)', onChanged: (_) => setState(() {})),
              const SizedBox(height: 8),
              _field(_justify, 'Authorization justification (min 10 chars)', onChanged: (_) => setState(() {})),
              const SizedBox(height: 10),
              Row(children: [
                Text('Interval', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                const SizedBox(width: 12),
                DropdownButton<int>(
                  value: _interval,
                  dropdownColor: VulnaraColors.surfaceContainerHigh,
                  underline: const SizedBox.shrink(),
                  items: _intervals.entries
                      .map((e) => DropdownMenuItem(value: e.key,
                          child: Text(e.value, style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface))))
                      .toList(),
                  onChanged: (v) => setState(() => _interval = v ?? 1440),
                ),
              ]),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                controlAffinity: ListTileControlAffinity.leading,
                value: _activeTesting,
                onChanged: (v) => setState(() => _activeTesting = v ?? false),
                title: Text('Active AI testing', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface)),
              ),
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                controlAffinity: ListTileControlAffinity.leading,
                value: _authorized,
                onChanged: (v) => setState(() => _authorized = v ?? false),
                title: Text("I'm authorized to scan this target", style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface)),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                height: 44,
                child: ElevatedButton(
                  onPressed: (!canCreate || _busy) ? null : () => _run(() async {
                    await repo.createSchedule(
                      target: _target.text.trim(),
                      justification: _justify.text.trim(),
                      intervalMinutes: _interval,
                      activeTesting: _activeTesting,
                    );
                    _target.clear();
                    _justify.clear();
                    setState(() { _authorized = false; _activeTesting = false; });
                  }),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: VulnaraColors.primaryContainer,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                  ),
                  child: Text('SCHEDULE SCAN',
                      style: VulnaraFonts.codeSm(color: Colors.white, fontWeight: FontWeight.w700)),
                ),
              ),
            ]),
          ),

          const SizedBox(height: VulnaraSpacing.stackMd),
          Text('ACTIVE SCHEDULES', style: VulnaraFonts.labelCaps()),
          const SizedBox(height: 8),
          schedulesAsync.when(
            loading: () => const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator())),
            error: (e, _) => Text(e.toString(), style: VulnaraFonts.codeSm(color: VulnaraColors.error)),
            data: (list) => list.isEmpty
                ? Text('No schedules yet.', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant))
                : Column(
                    children: list.map((s) {
                      final enabled = s['enabled'] == true;
                      final interval = (s['interval_minutes'] as num?)?.toInt() ?? 0;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: GlassPanel(
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                          child: Row(children: [
                            Expanded(
                              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text('${s['target']}',
                                    maxLines: 1, overflow: TextOverflow.ellipsis,
                                    style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface)),
                                Text('${_intervals[interval] ?? 'every $interval min'}'
                                    '${s['active_testing_enabled'] == true ? ' · active testing' : ''}',
                                    style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                              ]),
                            ),
                            TextButton(
                              onPressed: _busy ? null : () => _run(() => repo.toggleSchedule('${s['schedule_id']}', !enabled)),
                              child: Text(enabled ? 'Enabled' : 'Paused',
                                  style: VulnaraFonts.codeSm(
                                      color: enabled ? VulnaraColors.statusSuccess : VulnaraColors.onSurfaceVariant)),
                            ),
                            IconButton(
                              icon: const Icon(Icons.delete_outline, color: VulnaraColors.error, size: 20),
                              onPressed: _busy ? null : () => _run(() => repo.deleteSchedule('${s['schedule_id']}')),
                            ),
                          ]),
                        ),
                      );
                    }).toList(),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _field(TextEditingController controller, String hint, {ValueChanged<String>? onChanged}) {
    return Container(
      decoration: BoxDecoration(
        color: VulnaraColors.inputFill,
        borderRadius: BorderRadius.circular(VulnaraRadius.sm),
        border: Border.all(color: VulnaraColors.outlineVariant),
      ),
      child: TextField(
        controller: controller,
        onChanged: onChanged,
        style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface),
        cursorColor: VulnaraColors.primary,
        decoration: InputDecoration(
          border: InputBorder.none,
          isDense: true,
          contentPadding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
          hintText: hint,
          hintStyle: VulnaraFonts.codeSm(color: VulnaraColors.outlineVariant),
        ),
      ),
    );
  }
}
