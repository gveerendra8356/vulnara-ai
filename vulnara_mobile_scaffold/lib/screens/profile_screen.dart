// screens/profile_screen.dart -- new screen (no existing route in
// lib_me) added for the "Profile" tab of the bottom nav. Wires the
// real authProvider user + logout action into the design.
//
// UI matches the Stitch "profile_settings" mock: avatar + role badge,
// "Identity & Access" and "Preferences" grouped setting rows, a
// "System About" row, and a bordered "Log Out" button.

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

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  bool _notificationsEnabled = true;
  bool _darkMode = true; // this design system is dark-only; kept as a display toggle

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final user = authState is AuthLoggedIn ? authState.user : null;

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      extendBodyBehindAppBar: true,
      extendBody: true,
      appBar: const VulnaraAppBar(),
      bottomNavigationBar: const VulnaraBottomNav(current: VulnaraTab.profile),
      body: SafeArea(
        bottom: false,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(
            VulnaraSpacing.containerPadding,
            80,
            VulnaraSpacing.containerPadding,
            32,
          ),
          children: [
            Center(
              child: Column(
                children: [
                  Stack(
                    children: [
                      Container(
                        width: 96,
                        height: 96,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: VulnaraColors.surfaceContainerHigh,
                          border: Border.all(color: VulnaraColors.outlineVariant, width: 2),
                        ),
                        child: const Icon(Icons.person, size: 44, color: VulnaraColors.onSurfaceVariant),
                      ),
                      Positioned(
                        right: 4,
                        bottom: 4,
                        child: Container(
                          width: 18,
                          height: 18,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: VulnaraColors.secondaryFixedDim,
                            border: Border.all(color: VulnaraColors.pageBackground, width: 3),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: VulnaraSpacing.stackMd),
                  Text(user?.fullName ?? 'Unknown Operator', style: VulnaraFonts.headlineMd()),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(VulnaraRadius.full),
                      border: Border.all(color: VulnaraColors.outlineVariant),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.shield_outlined, size: 13, color: VulnaraColors.primary),
                        const SizedBox(width: 6),
                        Text((user?.role ?? 'analyst').toUpperCase(), style: VulnaraFonts.labelCaps()),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: VulnaraSpacing.stackLg * 1.5),
            const _SectionLabel('IDENTITY & ACCESS'),
            const SizedBox(height: 8),
            _SettingsGroup(children: [
              _SettingsRow(icon: Icons.badge_outlined, title: 'Account Settings', onTap: () {}),
              _SettingsRow(
                icon: Icons.vpn_key_outlined,
                title: 'Security',
                subtitle: '2FA ENABLED',
                onTap: () => context.push('/audit-log'),
              ),
            ]),
            const SizedBox(height: VulnaraSpacing.stackLg),
            const _SectionLabel('PREFERENCES'),
            const SizedBox(height: 8),
            _SettingsGroup(children: [
              _SettingsRow(
                icon: Icons.notifications_outlined,
                title: 'Notification Preferences',
                subtitle: 'Push & Email',
                trailing: Switch(
                  value: _notificationsEnabled,
                  onChanged: (v) => setState(() => _notificationsEnabled = v),
                  activeThumbColor: VulnaraColors.onPrimary,
                  activeTrackColor: VulnaraColors.primary,
                ),
              ),
              _SettingsRow(
                icon: Icons.contrast,
                title: 'Dark Mode',
                trailing: Switch(
                  value: _darkMode,
                  onChanged: (v) => setState(() => _darkMode = v),
                  activeThumbColor: VulnaraColors.onPrimary,
                  activeTrackColor: VulnaraColors.primary,
                ),
              ),
            ]),
            const SizedBox(height: VulnaraSpacing.stackLg),
            _SettingsGroup(children: [
              _SettingsRow(
                icon: Icons.info_outline,
                title: 'System About',
                trailing: Text('v2.4.1', style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant)),
              ),
            ]),
            const SizedBox(height: VulnaraSpacing.stackLg),
            Center(
              child: OutlinedButton.icon(
                onPressed: () => ref.read(authProvider.notifier).logout(),
                style: OutlinedButton.styleFrom(
                  foregroundColor: VulnaraColors.onSurfaceVariant,
                  side: const BorderSide(color: VulnaraColors.outlineVariant),
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                ),
                icon: const Icon(Icons.logout, size: 16),
                label: Text('LOG OUT', style: VulnaraFonts.labelCaps(color: VulnaraColors.onSurfaceVariant)),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.label);
  final String label;

  @override
  Widget build(BuildContext context) => Text(label, style: VulnaraFonts.labelCaps());
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
  const _SettingsRow({required this.icon, required this.title, this.subtitle, this.trailing, this.onTap});

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
                    Text(subtitle!.toUpperCase(),
                        style: VulnaraFonts.labelCaps(color: VulnaraColors.onSurfaceVariant).copyWith(fontSize: 10)),
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
