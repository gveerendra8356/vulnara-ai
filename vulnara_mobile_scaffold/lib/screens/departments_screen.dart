// screens/departments_screen.dart -- admin-only department management.
// Create/delete departments and assign analysts. Mirrors the web
// DepartmentsPage. Admin-only route (router bounces non-admins).

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/core_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/glass_panel.dart';

final _departmentsProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(organizationRepositoryProvider).listDepartments(),
);
final _usersProvider = FutureProvider.autoDispose<List<Map<String, dynamic>>>(
  (ref) => ref.watch(adminRepositoryProvider).listUsers(),
);

class DepartmentsScreen extends ConsumerStatefulWidget {
  const DepartmentsScreen({super.key});

  @override
  ConsumerState<DepartmentsScreen> createState() => _DepartmentsScreenState();
}

class _DepartmentsScreenState extends ConsumerState<DepartmentsScreen> {
  final _nameController = TextEditingController();
  final _descController = TextEditingController();
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _nameController.dispose();
    _descController.dispose();
    super.dispose();
  }

  void _refresh() {
    ref.invalidate(_departmentsProvider);
    ref.invalidate(_usersProvider);
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() { _busy = true; _error = null; });
    try {
      await action();
      _refresh();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final depsAsync = ref.watch(_departmentsProvider);
    final usersAsync = ref.watch(_usersProvider);
    final repo = ref.read(organizationRepositoryProvider);

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: VulnaraColors.onSurfaceVariant),
          onPressed: () => context.canPop() ? context.pop() : context.go('/profile'),
        ),
        title: Text('Departments', style: VulnaraFonts.headlineMd()),
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(
            VulnaraSpacing.containerPadding, 8, VulnaraSpacing.containerPadding, 32),
        children: [
          Text(
            "Create departments and assign analysts. Each analyst sees only their department's data.",
            style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
          ),
          const SizedBox(height: VulnaraSpacing.stackMd),
          if (_error != null) ...[
            Text(_error!, style: VulnaraFonts.codeSm(color: VulnaraColors.error)),
            const SizedBox(height: 8),
          ],

          // Create department
          GlassPanel(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('NEW DEPARTMENT', style: VulnaraFonts.labelCaps()),
              const SizedBox(height: 10),
              _field(_nameController, 'Department name (e.g. IT Security)'),
              const SizedBox(height: 8),
              _field(_descController, 'Description (optional)'),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                height: 44,
                child: ElevatedButton(
                  onPressed: _busy
                      ? null
                      : () {
                          final name = _nameController.text.trim();
                          if (name.isEmpty) return;
                          _run(() async {
                            await repo.createDepartment(name, description: _descController.text.trim());
                            _nameController.clear();
                            _descController.clear();
                          });
                        },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: VulnaraColors.primaryContainer,
                    foregroundColor: Colors.white,
                    elevation: 0,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                  ),
                  child: Text('CREATE DEPARTMENT',
                      style: VulnaraFonts.codeSm(color: Colors.white, fontWeight: FontWeight.w700)),
                ),
              ),
            ]),
          ),

          const SizedBox(height: VulnaraSpacing.stackMd),
          Text('DEPARTMENTS', style: VulnaraFonts.labelCaps()),
          const SizedBox(height: 8),
          depsAsync.when(
            loading: () => const Center(child: Padding(padding: EdgeInsets.all(16), child: CircularProgressIndicator())),
            error: (e, _) => Text(e.toString(), style: VulnaraFonts.codeSm(color: VulnaraColors.error)),
            data: (departments) => departments.isEmpty
                ? Text('No departments yet.', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant))
                : Column(
                    children: departments.map((d) => Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: GlassPanel(
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                            child: Row(children: [
                              Expanded(
                                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                  Text('${d['name']}',
                                      style: VulnaraFonts.bodyBase(color: VulnaraColors.onSurface)),
                                  Text('${d['description'] ?? 'No description'} · ${d['member_count']} analysts',
                                      style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                                ]),
                              ),
                              IconButton(
                                icon: const Icon(Icons.delete_outline, color: VulnaraColors.error, size: 20),
                                onPressed: _busy
                                    ? null
                                    : () => _run(() => repo.deleteDepartment('${d['department_id']}')),
                              ),
                            ]),
                          ),
                        )).toList(),
                  ),
          ),

          const SizedBox(height: VulnaraSpacing.stackMd),
          Text('ANALYST ASSIGNMENTS', style: VulnaraFonts.labelCaps()),
          const SizedBox(height: 8),
          _buildAssignments(context, usersAsync, depsAsync, repo),
        ],
      ),
    );
  }

  Widget _buildAssignments(
    BuildContext context,
    AsyncValue<List<Map<String, dynamic>>> usersAsync,
    AsyncValue<List<Map<String, dynamic>>> depsAsync,
    dynamic repo,
  ) {
    final departments = depsAsync.asData?.value ?? [];
    return usersAsync.when(
      loading: () => const SizedBox.shrink(),
      error: (e, _) => Text(e.toString(), style: VulnaraFonts.codeSm(color: VulnaraColors.error)),
      data: (users) {
        final analysts = users.where((u) => u['role'] == 'analyst').toList();
        if (analysts.isEmpty) {
          return Text('No analysts yet.', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant));
        }
        return Column(
          children: analysts.map((u) => Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: GlassPanel(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  child: Row(children: [
                    Expanded(
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${u['full_name']}',
                            maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: VulnaraFonts.bodyBase(color: VulnaraColors.onSurface)),
                        Text('${u['email']}',
                            maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                      ]),
                    ),
                    DropdownButton<String?>(
                      value: u['department_id'] as String?,
                      hint: Text('Unassigned', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                      dropdownColor: VulnaraColors.surfaceContainerHigh,
                      underline: const SizedBox.shrink(),
                      items: [
                        DropdownMenuItem<String?>(
                          value: null,
                          child: Text('Unassigned', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                        ),
                        for (final d in departments)
                          DropdownMenuItem<String?>(
                            value: d['department_id'] as String,
                            child: Text('${d['name']}', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface)),
                          ),
                      ],
                      onChanged: _busy
                          ? null
                          : (val) => _run(() => repo.assignUserDepartment('${u['user_id']}', val)),
                    ),
                  ]),
                ),
              )).toList(),
        );
      },
    );
  }

  Widget _field(TextEditingController controller, String hint) {
    return Container(
      decoration: BoxDecoration(
        color: VulnaraColors.inputFill,
        borderRadius: BorderRadius.circular(VulnaraRadius.sm),
        border: Border.all(color: VulnaraColors.outlineVariant),
      ),
      child: TextField(
        controller: controller,
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
