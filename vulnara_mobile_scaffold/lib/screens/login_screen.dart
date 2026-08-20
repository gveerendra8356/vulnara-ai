// screens/login_screen.dart -- build order item 1. Everything else
// requires an authenticated session, so this has to exist and work
// before any other screen is reachable.
//
// UI matches the Stitch "login_authentication" mock exactly: glowing
// shield wordmark, glass-panel auth card with email/password inputs,
// biometric + primary CTA row, and a system-status footer.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../providers/auth_provider.dart';
import '../theme/vulnara_theme.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  bool _obscurePassword = true;

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authState = ref.watch(authProvider);
    final isLoggingIn = authState is AuthLoggingIn;
    final error = authState is AuthLoggedOut ? authState.error : null;

    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      body: DecoratedBox(
        decoration: const BoxDecoration(
          gradient: RadialGradient(
            center: Alignment(0, -0.7),
            radius: 0.9,
            colors: [Color(0x0D4A8EFF), Color(0x00131313)],
          ),
        ),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 32),
              child: Form(
                key: _formKey,
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      const _Logo(),
                      const SizedBox(height: 16),
                      Text(
                        'VULNARA',
                        style: VulnaraFonts.displayLg(letterSpacing: 0.1 * 32),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'SECURE TERMINAL ACCESS',
                        style: VulnaraFonts.labelCaps(letterSpacing: 0.2 * 11)
                            .copyWith(color: VulnaraColors.onSurfaceVariant.withValues(alpha: 0.6)),
                      ),
                      const SizedBox(height: 24),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
                        decoration: BoxDecoration(
                          color: VulnaraColors.surface.withValues(alpha: 0.4),
                          borderRadius: BorderRadius.circular(VulnaraRadius.xl),
                          border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            if (error != null) ...[
                              Text(error, style: const TextStyle(color: VulnaraColors.error, fontSize: 13)),
                              const SizedBox(height: 12),
                            ],
                            Text('OPERATOR ID / EMAIL', style: VulnaraFonts.labelCaps()),
                            const SizedBox(height: 8),
                            _VulnaraField(
                              controller: _emailController,
                              hint: 'sysadmin@vulnara.io',
                              icon: Icons.person_outline,
                              keyboardType: TextInputType.emailAddress,
                              validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
                            ),
                            const SizedBox(height: 16),
                            Text('ACCESS KEY', style: VulnaraFonts.labelCaps()),
                            const SizedBox(height: 8),
                            _VulnaraField(
                              controller: _passwordController,
                              hint: '••••••••••••',
                              icon: Icons.lock_outline,
                              obscureText: _obscurePassword,
                              trailing: IconButton(
                                icon: Icon(
                                  _obscurePassword ? Icons.visibility_outlined : Icons.visibility_off_outlined,
                                  size: 18,
                                  color: VulnaraColors.outline,
                                ),
                                onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                              ),
                              validator: (v) => (v == null || v.isEmpty) ? 'Enter your password' : null,
                            ),
                            const SizedBox(height: 16),
                            Row(
                              children: [
                                Container(
                                  width: 48,
                                  height: 48,
                                  decoration: BoxDecoration(
                                    color: VulnaraColors.surface.withValues(alpha: 0.4),
                                    borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                                    border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
                                  ),
                                  child: const Icon(Icons.face_outlined, color: VulnaraColors.outline),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: SizedBox(
                                    height: 48,
                                    child: ElevatedButton(
                                      onPressed: isLoggingIn ? null : _submit,
                                      style: ElevatedButton.styleFrom(
                                        backgroundColor: VulnaraColors.primaryContainer,
                                        foregroundColor: Colors.white,
                                        shape: RoundedRectangleBorder(
                                          borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                                        ),
                                        elevation: 0,
                                      ),
                                      child: isLoggingIn
                                          ? const SizedBox(
                                              height: 18,
                                              width: 18,
                                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                            )
                                          : Row(
                                              mainAxisAlignment: MainAxisAlignment.center,
                                              children: [
                                                Text(
                                                  'INITIALIZE SESSION',
                                                  style: VulnaraFonts.codeSm(
                                                    color: Colors.white,
                                                    fontWeight: FontWeight.w700,
                                                  ).copyWith(letterSpacing: 1.2),
                                                ),
                                                const SizedBox(width: 8),
                                                const Icon(Icons.arrow_forward, size: 18, color: Colors.white),
                                              ],
                                            ),
                                    ),
                                  ),
                                ),
                              ],
                            ),

                          ],
                        ),
                      ),
                      const SizedBox(height: 24),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Container(
                            width: 6,
                            height: 6,
                            decoration:
                                const BoxDecoration(color: VulnaraColors.statusSuccess, shape: BoxShape.circle),
                          ),
                          const SizedBox(width: 8),
                          Text('SYSTEM STATUS: OPTIMAL',
                              style: VulnaraFonts.codeSm(
                                      color: VulnaraColors.onSurfaceVariant.withValues(alpha: 0.5), fontSize: 10)
                                  .copyWith(fontSize: 10)),
                          const SizedBox(width: 16),
                          Text('NODE: V-77X',
                              style: VulnaraFonts.codeSm(
                                      color: VulnaraColors.onSurfaceVariant.withValues(alpha: 0.5), fontSize: 10)
                                  .copyWith(fontSize: 10)),
                        ],
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    ref.read(authProvider.notifier).login(
          email: _emailController.text.trim(),
          password: _passwordController.text,
        );
  }
}

class _Logo extends StatelessWidget {
  const _Logo();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 88,
      height: 88,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(color: VulnaraColors.primary.withValues(alpha: 0.25), blurRadius: 30, spreadRadius: 4),
        ],
      ),
      child: Container(
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: VulnaraColors.surfaceContainerLowest,
          border: Border.all(color: VulnaraColors.primary.withValues(alpha: 0.3)),
        ),
        child: const Icon(Icons.shield, color: VulnaraColors.primary, size: 44),
      ),
    );
  }
}

class _VulnaraField extends StatelessWidget {
  const _VulnaraField({
    required this.controller,
    required this.hint,
    required this.icon,
    this.obscureText = false,
    this.keyboardType,
    this.trailing,
    this.validator,
  });

  final TextEditingController controller;
  final String hint;
  final IconData icon;
  final bool obscureText;
  final TextInputType? keyboardType;
  final Widget? trailing;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: VulnaraColors.inputFill,
        borderRadius: BorderRadius.circular(VulnaraRadius.sm),
        border: Border.all(color: VulnaraColors.outlineVariant),
      ),
      child: TextFormField(
        controller: controller,
        obscureText: obscureText,
        keyboardType: keyboardType,
        validator: validator,
        style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface),
        cursorColor: VulnaraColors.primary,
        decoration: InputDecoration(
          border: InputBorder.none,
          isDense: true,
          contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
          prefixIcon: Icon(icon, size: 18, color: VulnaraColors.outlineVariant),
          prefixIconConstraints: const BoxConstraints(minWidth: 40),
          suffixIcon: trailing,
          hintText: hint,
          hintStyle: VulnaraFonts.codeSm(color: VulnaraColors.outlineVariant.withValues(alpha: 0.5)),
        ),
      ),
    );
  }
}
