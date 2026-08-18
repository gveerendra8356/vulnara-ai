// screens/admin_users_screen.dart -- Admin-only user management screen.
// Lists all users with role badges, scan counts, last login, and
// an enable/disable toggle. Tap a user row to see their scan history
// in a bottom sheet.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/core_providers.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/vulnara_app_bar.dart';

// ── Providers ─────────────────────────────────────────────────────────────

final adminUsersProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  return ref.watch(adminRepositoryProvider).listUsers();
});

final _userScansProvider =
    FutureProvider.autoDispose.family<Map<String, dynamic>, String>((ref, userId) async {
  return ref.watch(adminRepositoryProvider).getUserScans(userId);
});

// ── Screen ─────────────────────────────────────────────────────────────────

class AdminUsersScreen extends ConsumerStatefulWidget {
  const AdminUsersScreen({super.key});

  @override
  ConsumerState<AdminUsersScreen> createState() => _AdminUsersScreenState();
}

class _AdminUsersScreenState extends ConsumerState<AdminUsersScreen> {
  String _search = '';
  String _roleFilter = 'ALL';

  Color _roleColor(String role) => switch (role) {
        'admin' => VulnaraColors.error,
        'analyst' => VulnaraColors.primary,
        _ => VulnaraColors.secondaryFixedDim,
      };

  void _showUserScans(Map<String, dynamic> user) {
    showModalBottomSheet(
      context: context,
      backgroundColor: VulnaraColors.pageBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      isScrollControlled: true,
      builder: (ctx) => _UserScansSheet(userId: user['user_id'] as String),
    );
  }

  Future<void> _toggleActive(Map<String, dynamic> user) async {
    final current = user['is_active'] as bool? ?? true;
    try {
      await ref.read(adminRepositoryProvider).toggleUserActive(
            user['user_id'] as String,
            isActive: !current,
          );
      ref.invalidate(adminUsersProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: ${e.toString()}')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final usersAsync = ref.watch(adminUsersProvider);

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      appBar: const VulnaraAppBar(),
      body: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('User Management', style: VulnaraFonts.headlineMd()),
                  const SizedBox(height: 4),
                  Text(
                    'All registered users · manage access',
                    style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                  ),
                  const SizedBox(height: 12),
                  // Search
                  TextField(
                    onChanged: (v) => setState(() => _search = v),
                    style: VulnaraFonts.codeSm(),
                    decoration: InputDecoration(
                      hintText: 'Search name or email…',
                      hintStyle: VulnaraFonts.codeSm(
                          color: VulnaraColors.onSurfaceVariant.withValues(alpha: 0.5)),
                      filled: true,
                      fillColor: VulnaraColors.surfaceContainerHigh,
                      prefixIcon: const Icon(Icons.search, size: 18, color: VulnaraColors.onSurfaceVariant),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                        borderSide: const BorderSide(color: VulnaraColors.outlineVariant),
                      ),
                      enabledBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                        borderSide: const BorderSide(color: VulnaraColors.outlineVariant),
                      ),
                      focusedBorder: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                        borderSide:
                            const BorderSide(color: VulnaraColors.primary, width: 1.5),
                      ),
                      contentPadding: const EdgeInsets.symmetric(vertical: 12),
                      isDense: true,
                    ),
                  ),
                  const SizedBox(height: 10),
                  // Role filter chips
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: ['ALL', 'admin', 'analyst', 'client'].map((r) {
                        final active = _roleFilter == r;
                        return Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: GestureDetector(
                            onTap: () => setState(() => _roleFilter = r),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                              decoration: BoxDecoration(
                                color: active
                                    ? VulnaraColors.primary.withValues(alpha: 0.15)
                                    : VulnaraColors.surfaceContainerHigh,
                                borderRadius: BorderRadius.circular(VulnaraRadius.full),
                                border: Border.all(
                                  color: active
                                      ? VulnaraColors.primary.withValues(alpha: 0.5)
                                      : VulnaraColors.outlineVariant,
                                ),
                              ),
                              child: Text(
                                r.toUpperCase(),
                                style: VulnaraFonts.labelCaps(
                                  color: active ? VulnaraColors.primary : VulnaraColors.onSurfaceVariant,
                                ),
                              ),
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),

            // User list
            Expanded(
              child: usersAsync.when(
                loading: () => const Center(child: CircularProgressIndicator()),
                error: (err, _) => Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(err.toString(), style: VulnaraFonts.bodyBase()),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: () => ref.invalidate(adminUsersProvider),
                        child: const Text('Retry'),
                      ),
                    ],
                  ),
                ),
                data: (users) {
                  final filtered = users.where((u) {
                    final matchRole = _roleFilter == 'ALL' || u['role'] == _roleFilter;
                    final q = _search.toLowerCase();
                    final matchSearch = q.isEmpty ||
                        (u['full_name'] as String? ?? '').toLowerCase().contains(q) ||
                        (u['email'] as String? ?? '').toLowerCase().contains(q);
                    return matchRole && matchSearch;
                  }).toList();

                  if (filtered.isEmpty) {
                    return Center(
                      child: Text(
                        'No users found.',
                        style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                      ),
                    );
                  }

                  return RefreshIndicator(
                    onRefresh: () async => ref.invalidate(adminUsersProvider),
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(20, 4, 20, 80),
                      itemCount: filtered.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (ctx, i) => _UserCard(
                        user: filtered[i],
                        roleColor: _roleColor(filtered[i]['role'] as String? ?? 'client'),
                        onViewScans: () => _showUserScans(filtered[i]),
                        onToggleActive: () => _toggleActive(filtered[i]),
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── User Card ──────────────────────────────────────────────────────────────

class _UserCard extends StatelessWidget {
  const _UserCard({
    required this.user,
    required this.roleColor,
    required this.onViewScans,
    required this.onToggleActive,
  });

  final Map<String, dynamic> user;
  final Color roleColor;
  final VoidCallback onViewScans;
  final VoidCallback onToggleActive;

  @override
  Widget build(BuildContext context) {
    final name = user['full_name'] as String? ?? '?';
    final email = user['email'] as String? ?? '';
    final role = user['role'] as String? ?? 'client';
    final isActive = user['is_active'] as bool? ?? true;
    final scanCount = user['scan_count'] as int? ?? 0;
    final lastLogin = user['last_login_at'] as String?;

    return Material(
      color: VulnaraColors.surfaceContainer,
      borderRadius: BorderRadius.circular(VulnaraRadius.lg),
      child: InkWell(
        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
        onTap: onViewScans,
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(VulnaraRadius.lg),
            border: Border.all(color: VulnaraColors.outlineVariant.withValues(alpha: 0.3)),
          ),
          child: Stack(
            children: [
              // Left role accent bar
              Positioned(
                left: 0, top: 0, bottom: 0,
                child: Container(
                  width: 3,
                  decoration: BoxDecoration(
                    color: isActive ? roleColor : VulnaraColors.outlineVariant,
                    borderRadius: const BorderRadius.horizontal(left: Radius.circular(VulnaraRadius.lg)),
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 14, 14, 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        // Avatar initial
                        Container(
                          width: 36,
                          height: 36,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: roleColor.withValues(alpha: 0.1),
                            border: Border.all(color: roleColor.withValues(alpha: 0.3)),
                          ),
                          child: Center(
                            child: Text(
                              name.isNotEmpty ? name[0].toUpperCase() : '?',
                              style: VulnaraFonts.labelCaps(color: roleColor),
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(name,
                                  style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w600),
                                  overflow: TextOverflow.ellipsis),
                              Text(email,
                                  style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                                  overflow: TextOverflow.ellipsis),
                            ],
                          ),
                        ),
                        // Role chip
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(
                            color: roleColor.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(VulnaraRadius.full),
                            border: Border.all(color: roleColor.withValues(alpha: 0.3)),
                          ),
                          child: Text(role.toUpperCase(),
                              style: VulnaraFonts.labelCaps(color: roleColor).copyWith(fontSize: 9)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    const Divider(height: 1),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        // Scan count
                        _MetaChip(
                          icon: Icons.biotech_outlined,
                          label: '$scanCount scan${scanCount == 1 ? '' : 's'}',
                        ),
                        const SizedBox(width: 8),
                        // Status
                        _MetaChip(
                          icon: isActive ? Icons.check_circle_outline : Icons.block_outlined,
                          label: isActive ? 'Active' : 'Disabled',
                          color: isActive ? Colors.green : VulnaraColors.onSurfaceVariant,
                        ),
                        const Spacer(),
                        // View scans button
                        _ActionBtn(label: 'Scans', icon: Icons.arrow_forward_ios, onTap: onViewScans),
                        const SizedBox(width: 6),
                        // Toggle button
                        _ActionBtn(
                          label: isActive ? 'Disable' : 'Enable',
                          icon: isActive ? Icons.block : Icons.check_circle,
                          color: isActive ? VulnaraColors.error : Colors.green,
                          onTap: onToggleActive,
                        ),
                      ],
                    ),
                    if (lastLogin != null) ...[
                      const SizedBox(height: 6),
                      Text(
                        'Last login: ${DateTime.tryParse(lastLogin)?.toLocal().toString().substring(0, 16) ?? lastLogin}',
                        style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)
                            .copyWith(fontSize: 10),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _MetaChip extends StatelessWidget {
  const _MetaChip({required this.icon, required this.label, this.color});
  final IconData icon;
  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? VulnaraColors.onSurfaceVariant;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 13, color: c),
        const SizedBox(width: 4),
        Text(label, style: VulnaraFonts.codeSm(color: c).copyWith(fontSize: 11)),
      ],
    );
  }
}

class _ActionBtn extends StatelessWidget {
  const _ActionBtn({required this.label, required this.icon, required this.onTap, this.color});
  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? VulnaraColors.primary;
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: c.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(VulnaraRadius.lg),
          border: Border.all(color: c.withValues(alpha: 0.25)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: c),
            const SizedBox(width: 4),
            Text(label, style: VulnaraFonts.labelCaps(color: c).copyWith(fontSize: 9)),
          ],
        ),
      ),
    );
  }
}

// ── User Scans Bottom Sheet ────────────────────────────────────────────────

class _UserScansSheet extends ConsumerWidget {
  const _UserScansSheet({required this.userId});
  final String userId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final scansAsync = ref.watch(_userScansProvider(userId));

    return DraggableScrollableSheet(
      initialChildSize: 0.65,
      maxChildSize: 0.92,
      minChildSize: 0.4,
      expand: false,
      builder: (ctx, scrollCtrl) {
        return Column(
          children: [
            // Handle
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Container(
                width: 36, height: 4,
                decoration: BoxDecoration(
                  color: VulnaraColors.outlineVariant,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            scansAsync.when(
              loading: () => const Expanded(child: Center(child: CircularProgressIndicator())),
              error: (err, _) => Expanded(
                child: Center(child: Text(err.toString(), style: VulnaraFonts.bodyBase())),
              ),
              data: (data) {
                final user = data['user'] as Map<String, dynamic>;
                final scans = (data['scans'] as List).cast<Map<String, dynamic>>();
                final name = user['full_name'] as String? ?? 'User';
                final role = user['role'] as String? ?? 'client';

                return Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(name, style: VulnaraFonts.headlineMd()),
                            const SizedBox(height: 2),
                            Text(
                              '${scans.length} scan${scans.length == 1 ? '' : 's'} · ${role.toUpperCase()}',
                              style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Divider(height: 1),
                      if (scans.isEmpty)
                        Expanded(
                          child: Center(
                            child: Text(
                              'No scans yet.',
                              style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                            ),
                          ),
                        )
                      else
                        Expanded(
                          child: ListView.separated(
                            controller: scrollCtrl,
                            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                            itemCount: scans.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 8),
                            itemBuilder: (_, i) {
                              final s = scans[i];
                              final status = s['status'] as String? ?? '';
                              final statusColor = switch (status) {
                                'COMPLETED' => Colors.green,
                                'IN_PROGRESS' => VulnaraColors.primary,
                                'FAILED' => VulnaraColors.error,
                                _ => VulnaraColors.onSurfaceVariant,
                              };

                              return Container(
                                padding: const EdgeInsets.all(14),
                                decoration: BoxDecoration(
                                  color: VulnaraColors.surfaceContainerHigh,
                                  borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                                  border: Border.all(
                                      color: VulnaraColors.outlineVariant.withValues(alpha: 0.3)),
                                ),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            s['target'] as String? ?? '',
                                            style: VulnaraFonts.codeSm(
                                                color: VulnaraColors.primary,
                                                fontWeight: FontWeight.w700),
                                            overflow: TextOverflow.ellipsis,
                                          ),
                                          const SizedBox(height: 4),
                                          if (s['created_at'] != null)
                                            Text(
                                              DateTime.tryParse(s['created_at'] as String)
                                                      ?.toLocal()
                                                      .toString()
                                                      .substring(0, 16) ??
                                                  s['created_at'] as String,
                                              style: VulnaraFonts.codeSm(
                                                      color: VulnaraColors.onSurfaceVariant)
                                                  .copyWith(fontSize: 10),
                                            ),
                                        ],
                                      ),
                                    ),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: statusColor.withValues(alpha: 0.1),
                                        borderRadius: BorderRadius.circular(VulnaraRadius.full),
                                        border: Border.all(color: statusColor.withValues(alpha: 0.3)),
                                      ),
                                      child: Text(
                                        status,
                                        style: VulnaraFonts.labelCaps(color: statusColor)
                                            .copyWith(fontSize: 9),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                        ),
                    ],
                  ),
                );
              },
            ),
          ],
        );
      },
    );
  }
}
