// screens/profile_screen.dart -- Profile + account edit screen.
// Allows the logged-in user to update their full name, email address,
// and password. Password change requires the current password for
// verification. All changes call PATCH /auth/me via AuthNotifier.
//
// UI: avatar + role badge at top, then tabbed sections for Account Info
// and Change Password, with inline success / error feedback.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/auth_provider.dart';
import '../theme/vulnara_theme.dart';
import '../widgets/vulnara_app_bar.dart';
import '../widgets/vulnara_bottom_nav.dart';

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tab;

  // Account info controllers
  late final TextEditingController _nameCtrl;
  late final TextEditingController _emailCtrl;

  // Password change controllers
  final _currentPwCtrl = TextEditingController();
  final _newPwCtrl = TextEditingController();
  final _confirmPwCtrl = TextEditingController();

  bool _saving = false;
  String? _success;
  String? _error;

  bool _showCurrentPw = false;
  bool _showNewPw = false;
  bool _notificationsEnabled = true;

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 2, vsync: this);
    final authState = ref.read(authProvider);
    final user = authState is AuthLoggedIn ? authState.user : null;
    _nameCtrl = TextEditingController(text: user?.fullName ?? '');
    _emailCtrl = TextEditingController(text: user?.email ?? '');
  }

  @override
  void dispose() {
    _tab.dispose();
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _currentPwCtrl.dispose();
    _newPwCtrl.dispose();
    _confirmPwCtrl.dispose();
    super.dispose();
  }

  Future<void> _saveAccountInfo() async {
    setState(() { _saving = true; _success = null; _error = null; });
    final authState = ref.read(authProvider);
    final user = authState is AuthLoggedIn ? authState.user : null;

    final newName = _nameCtrl.text.trim();
    final newEmail = _emailCtrl.text.trim();

    if (newName == (user?.fullName ?? '') && newEmail == (user?.email ?? '')) {
      setState(() { _saving = false; _error = 'No changes detected.'; });
      return;
    }

    final err = await ref.read(authProvider.notifier).updateProfile(
          fullName: newName != (user?.fullName ?? '') ? newName : null,
          email: newEmail != (user?.email ?? '') ? newEmail : null,
        );

    setState(() {
      _saving = false;
      if (err == null) _success = 'Profile updated successfully!';
      else _error = err;
    });
  }

  Future<void> _changePassword() async {
    setState(() { _saving = true; _success = null; _error = null; });

    final current = _currentPwCtrl.text;
    final newPw = _newPwCtrl.text;
    final confirm = _confirmPwCtrl.text;

    if (current.isEmpty || newPw.isEmpty) {
      setState(() { _saving = false; _error = 'All password fields are required.'; });
      return;
    }
    if (newPw.length < 8) {
      setState(() { _saving = false; _error = 'New password must be at least 8 characters.'; });
      return;
    }
    if (newPw != confirm) {
      setState(() { _saving = false; _error = 'New passwords do not match.'; });
      return;
    }

    final err = await ref.read(authProvider.notifier).updateProfile(
          currentPassword: current,
          newPassword: newPw,
        );

    setState(() {
      _saving = false;
      if (err == null) {
        _success = 'Password changed successfully!';
        _currentPwCtrl.clear();
        _newPwCtrl.clear();
        _confirmPwCtrl.clear();
      } else {
        _error = err;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final user = authState is AuthLoggedIn ? authState.user : null;
    final initials = (user?.fullName ?? '?').isNotEmpty
        ? (user?.fullName ?? '?').substring(0, 1).toUpperCase()
        : '?';

    final roleColor = switch (user?.role ?? 'client') {
      'admin' => VulnaraColors.error,
      'analyst' => VulnaraColors.primary,
      _ => VulnaraColors.secondaryFixedDim,
    };

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: const VulnaraAppBar(),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.profile),
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // ── Avatar + name + role ──────────────────────────────────────
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
              child: Column(
                children: [
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(colors: [
                        roleColor.withValues(alpha: 0.3),
                        roleColor.withValues(alpha: 0.05),
                      ]),
                      border: Border.all(color: roleColor.withValues(alpha: 0.4), width: 2),
                    ),
                    child: Center(
                      child: Text(
                        initials,
                        style: VulnaraFonts.headlineMd(color: roleColor).copyWith(fontSize: 28),
                      ),
                    ),
                  ),
                  const SizedBox(height: 12),
                  Text(user?.fullName ?? 'Unknown', style: VulnaraFonts.headlineMd()),
                  const SizedBox(height: 4),
                  Text(user?.email ?? '', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      border: Border.all(color: roleColor.withValues(alpha: 0.4)),
                      borderRadius: BorderRadius.circular(VulnaraRadius.full),
                      color: roleColor.withValues(alpha: 0.1),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.shield_outlined, size: 12, color: roleColor),
                        const SizedBox(width: 6),
                        Text((user?.role ?? 'client').toUpperCase(),
                            style: VulnaraFonts.labelCaps(color: roleColor)),
                      ],
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 16),

            // ── Tabs ─────────────────────────────────────────────────────
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 20),
              decoration: BoxDecoration(
                color: VulnaraColors.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(VulnaraRadius.lg),
              ),
              child: TabBar(
                controller: _tab,
                onTap: (_) => setState(() { _success = null; _error = null; }),
                indicator: BoxDecoration(
                  color: VulnaraColors.primary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                  border: Border.all(color: VulnaraColors.primary.withValues(alpha: 0.3)),
                ),
                labelColor: VulnaraColors.primary,
                unselectedLabelColor: VulnaraColors.onSurfaceVariant,
                labelStyle: VulnaraFonts.labelCaps(color: VulnaraColors.primary),
                unselectedLabelStyle: VulnaraFonts.labelCaps(),
                tabs: const [
                  Tab(text: 'ACCOUNT INFO'),
                  Tab(text: 'CHANGE PASSWORD'),
                ],
              ),
            ),

            const SizedBox(height: 8),

            // ── Feedback messages ─────────────────────────────────────────
            if (_success != null || _error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: _success != null
                        ? Colors.green.withValues(alpha: 0.1)
                        : VulnaraColors.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                    border: Border.all(
                      color: _success != null
                          ? Colors.green.withValues(alpha: 0.3)
                          : VulnaraColors.error.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        _success != null ? Icons.check_circle_outline : Icons.error_outline,
                        size: 16,
                        color: _success != null ? Colors.green : VulnaraColors.error,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _success ?? _error ?? '',
                          style: VulnaraFonts.codeSm(
                            color: _success != null ? Colors.green : VulnaraColors.error,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),

            // ── Tab content ───────────────────────────────────────────────
            Expanded(
              child: TabBarView(
                controller: _tab,
                children: [
                  // ── Account Info Tab ──────────────────────────────────
                  _buildAccountTab(),
                  // ── Password Tab ──────────────────────────────────────
                  _buildPasswordTab(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAccountTab() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
      children: [
        _FieldLabel('FULL NAME'),
        const SizedBox(height: 6),
        _VulnaraTextField(controller: _nameCtrl, hint: 'Your full name'),
        const SizedBox(height: 16),
        _FieldLabel('EMAIL ADDRESS'),
        const SizedBox(height: 6),
        _VulnaraTextField(controller: _emailCtrl, hint: 'your@email.com', keyboardType: TextInputType.emailAddress),
        const SizedBox(height: 28),
        SizedBox(
          height: 50,
          child: ElevatedButton.icon(
            onPressed: _saving ? null : _saveAccountInfo,
            style: ElevatedButton.styleFrom(
              backgroundColor: VulnaraColors.primary,
              foregroundColor: VulnaraColors.onPrimary,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(VulnaraRadius.lg),
              ),
            ),
            icon: _saving
                ? const SizedBox(
                    height: 16, width: 16,
                    child: CircularProgressIndicator(strokeWidth: 2, color: VulnaraColors.onPrimary),
                  )
                : const Icon(Icons.save_outlined, size: 18),
            label: Text(
              _saving ? 'SAVING...' : 'SAVE CHANGES',
              style: VulnaraFonts.labelCaps(color: VulnaraColors.onPrimary),
            ),
          ),
        ),
        const SizedBox(height: 24),
        const _SectionDivider(),
        const SizedBox(height: 16),
        _SettingsGroup(children: [
          _SettingsRow(
            icon: Icons.notifications_outlined,
            title: 'Push Notifications',
            subtitle: 'Alerts for HIGH/CRITICAL findings',
            trailing: Switch(
              value: _notificationsEnabled,
              onChanged: (v) => setState(() => _notificationsEnabled = v),
              activeThumbColor: VulnaraColors.onPrimary,
              activeTrackColor: VulnaraColors.primary,
            ),
          ),
        ]),
        // Admin: User Management shortcut
        if (ref.read(authProvider) is AuthLoggedIn &&
            (ref.read(authProvider) as AuthLoggedIn).user.role == 'admin') ...[
          const SizedBox(height: 12),
          _SettingsGroup(children: [
            _SettingsRow(
              icon: Icons.group_outlined,
              title: 'User Management',
              subtitle: 'Manage analyst & client accounts',
              onTap: () => context.push('/admin/users'),
            ),
          ]),
        ],

        const SizedBox(height: 16),
        Center(
          child: OutlinedButton.icon(
            onPressed: () => ref.read(authProvider.notifier).logout(),
            style: OutlinedButton.styleFrom(
              foregroundColor: VulnaraColors.error,
              side: const BorderSide(color: VulnaraColors.error),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
              shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
            ),
            icon: const Icon(Icons.logout, size: 16),
            label: Text('LOG OUT', style: VulnaraFonts.labelCaps(color: VulnaraColors.error)),
          ),
        ),
      ],
    );
  }

  Widget _buildPasswordTab() {
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 120),
      children: [
        _FieldLabel('CURRENT PASSWORD'),
        const SizedBox(height: 6),
        _VulnaraTextField(
          controller: _currentPwCtrl,
          hint: 'Your current password',
          obscure: !_showCurrentPw,
          suffix: IconButton(
            icon: Icon(
              _showCurrentPw ? Icons.visibility_off_outlined : Icons.visibility_outlined,
              size: 18, color: VulnaraColors.onSurfaceVariant,
            ),
            onPressed: () => setState(() => _showCurrentPw = !_showCurrentPw),
          ),
        ),
        const SizedBox(height: 16),
        _FieldLabel('NEW PASSWORD'),
        const SizedBox(height: 6),
        _VulnaraTextField(
          controller: _newPwCtrl,
          hint: 'Min. 8 characters',
          obscure: !_showNewPw,
          suffix: IconButton(
            icon: Icon(
              _showNewPw ? Icons.visibility_off_outlined : Icons.visibility_outlined,
              size: 18, color: VulnaraColors.onSurfaceVariant,
            ),
            onPressed: () => setState(() => _showNewPw = !_showNewPw),
          ),
        ),
        const SizedBox(height: 16),
        _FieldLabel('CONFIRM NEW PASSWORD'),
        const SizedBox(height: 6),
        _VulnaraTextField(
          controller: _confirmPwCtrl,
          hint: 'Repeat new password',
          obscure: true,
        ),
        const SizedBox(height: 28),
        SizedBox(
          height: 50,
          child: ElevatedButton.icon(
            onPressed: _saving ? null : _changePassword,
            style: ElevatedButton.styleFrom(
              backgroundColor: VulnaraColors.primary,
              foregroundColor: VulnaraColors.onPrimary,
              elevation: 0,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(VulnaraRadius.lg),
              ),
            ),
            icon: _saving
                ? const SizedBox(
                    height: 16, width: 16,
                    child: CircularProgressIndicator(strokeWidth: 2, color: VulnaraColors.onPrimary),
                  )
                : const Icon(Icons.lock_reset, size: 18),
            label: Text(
              _saving ? 'UPDATING...' : 'UPDATE PASSWORD',
              style: VulnaraFonts.labelCaps(color: VulnaraColors.onPrimary),
            ),
          ),
        ),
        const SizedBox(height: 16),
        Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: VulnaraColors.primary.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(VulnaraRadius.lg),
            border: Border.all(color: VulnaraColors.primary.withValues(alpha: 0.15)),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Icon(Icons.info_outline, size: 16, color: VulnaraColors.primary),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  'You must enter your current password to change it. '
                  'New password must be at least 8 characters.',
                  style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)
                      .copyWith(height: 1.6),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ── Shared helper widgets ──────────────────────────────────────────────────

class _FieldLabel extends StatelessWidget {
  const _FieldLabel(this.label);
  final String label;
  @override
  Widget build(BuildContext context) =>
      Text(label, style: VulnaraFonts.labelCaps());
}

class _VulnaraTextField extends StatelessWidget {
  const _VulnaraTextField({
    required this.controller,
    required this.hint,
    this.obscure = false,
    this.suffix,
    this.keyboardType,
  });
  final TextEditingController controller;
  final String hint;
  final bool obscure;
  final Widget? suffix;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: controller,
      obscureText: obscure,
      keyboardType: keyboardType,
      style: VulnaraFonts.codeSm(),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant.withValues(alpha: 0.5)),
        filled: true,
        fillColor: VulnaraColors.surfaceContainerHigh,
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
          borderSide: const BorderSide(color: VulnaraColors.primary, width: 1.5),
        ),
        suffixIcon: suffix,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }
}

class _SectionDivider extends StatelessWidget {
  const _SectionDivider();
  @override
  Widget build(BuildContext context) => Row(children: [
        const Expanded(child: Divider()),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Text('PREFERENCES', style: VulnaraFonts.labelCaps()),
        ),
        const Expanded(child: Divider()),
      ]);
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);
  final String label;
  @override
  Widget build(BuildContext context) =>
      Text(label, style: VulnaraFonts.labelCaps());
}

class _SettingsGroup extends StatelessWidget {
  const _SettingsGroup({required this.children});
  final List<Widget> children;
  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: VulnaraColors.surface.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(VulnaraRadius.xl),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        children: [
          for (int i = 0; i < children.length; i++) ...[
            children[i],
            if (i != children.length - 1) const Divider(height: 1),
          ],
        ],
      ),
    );
  }
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({
    required this.icon,
    required this.title,
    this.subtitle,
    this.trailing,
    this.onTap,
  });
  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: VulnaraColors.surfaceContainerHigh,
                borderRadius: BorderRadius.circular(VulnaraRadius.lg),
              ),
              child: Icon(icon, size: 18, color: VulnaraColors.onSurfaceVariant),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: VulnaraFonts.bodyBase(fontWeight: FontWeight.w500)),
                  if (subtitle != null) ...[
                    const SizedBox(height: 2),
                    Text(subtitle!,
                        style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)
                            .copyWith(fontSize: 10)),
                  ],
                ],
              ),
            ),
            if (trailing != null)
              trailing!
            else if (onTap != null)
              const Icon(Icons.chevron_right, color: VulnaraColors.onSurfaceVariant),
          ],
        ),
      ),
    );
  }
}
