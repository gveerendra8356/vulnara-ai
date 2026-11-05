// screens/forgot_password_screen.dart -- "Forgot password?" flow.
// Asks for the registered email and calls POST /auth/forgot-password.
// The backend emails a one-time reset link that opens the web reset page;
// the user sets a new password there, then logs back into the app with it.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../providers/core_providers.dart';
import '../theme/vulnara_theme.dart';

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  bool _busy = false;
  bool _sent = false;
  String? _error;

  @override
  void dispose() {
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(authRepositoryProvider).forgotPassword(_emailController.text.trim());
      if (mounted) setState(() => _sent = true);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: VulnaraColors.onSurfaceVariant),
          onPressed: () => context.go('/login'),
        ),
      ),
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
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 420),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const Icon(Icons.lock_reset, color: VulnaraColors.primary, size: 48),
                    const SizedBox(height: 16),
                    Text('RESET ACCESS',
                        textAlign: TextAlign.center,
                        style: VulnaraFonts.headlineMd(color: VulnaraColors.onSurface)),
                    const SizedBox(height: 8),
                    Text('Recover your account',
                        textAlign: TextAlign.center,
                        style: VulnaraFonts.labelCaps(
                            color: VulnaraColors.onSurfaceVariant.withValues(alpha: 0.6))),
                    const SizedBox(height: 24),
                    Container(
                      padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
                      decoration: BoxDecoration(
                        color: VulnaraColors.surface.withValues(alpha: 0.4),
                        borderRadius: BorderRadius.circular(VulnaraRadius.xl),
                        border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                      ),
                      child: _sent ? _buildSent(context) : _buildForm(),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildForm() {
    return Form(
      key: _formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            "Enter your registered email and we'll send you a link to reset your password.",
            style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
          ),
          const SizedBox(height: 16),
          Text('REGISTERED EMAIL', style: VulnaraFonts.labelCaps()),
          const SizedBox(height: 8),
          Container(
            decoration: BoxDecoration(
              color: VulnaraColors.inputFill,
              borderRadius: BorderRadius.circular(VulnaraRadius.sm),
              border: Border.all(color: VulnaraColors.outlineVariant),
            ),
            child: TextFormField(
              controller: _emailController,
              keyboardType: TextInputType.emailAddress,
              validator: (v) => (v == null || !v.contains('@')) ? 'Enter a valid email' : null,
              style: VulnaraFonts.codeSm(color: VulnaraColors.onSurface),
              cursorColor: VulnaraColors.primary,
              decoration: InputDecoration(
                border: InputBorder.none,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
                prefixIcon: const Icon(Icons.person_outline, size: 18, color: VulnaraColors.outlineVariant),
                prefixIconConstraints: const BoxConstraints(minWidth: 40),
                hintText: 'you@company.com',
                hintStyle: VulnaraFonts.codeSm(color: VulnaraColors.outlineVariant.withValues(alpha: 0.5)),
              ),
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: 12),
            Text(_error!, style: const TextStyle(color: VulnaraColors.error, fontSize: 13)),
          ],
          const SizedBox(height: 20),
          SizedBox(
            height: 48,
            child: ElevatedButton(
              onPressed: _busy ? null : _submit,
              style: ElevatedButton.styleFrom(
                backgroundColor: VulnaraColors.primaryContainer,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                elevation: 0,
              ),
              child: _busy
                  ? const SizedBox(
                      height: 18, width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text('SEND RESET LINK',
                      style: VulnaraFonts.codeSm(color: Colors.white, fontWeight: FontWeight.w700)
                          .copyWith(letterSpacing: 1.2)),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSent(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const Icon(Icons.mark_email_read, color: VulnaraColors.statusSuccess, size: 40),
        const SizedBox(height: 16),
        Text(
          'If an account exists for ${_emailController.text.trim()}, a password reset link has been sent. '
          'Check your inbox (and spam) — the link expires in 30 minutes. Open it to set a new password, '
          'then log in here with it.',
          textAlign: TextAlign.center,
          style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
        ),
        const SizedBox(height: 20),
        SizedBox(
          height: 48,
          child: ElevatedButton(
            onPressed: () => context.go('/login'),
            style: ElevatedButton.styleFrom(
              backgroundColor: VulnaraColors.primaryContainer,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
              elevation: 0,
            ),
            child: Text('BACK TO LOGIN',
                style: VulnaraFonts.codeSm(color: Colors.white, fontWeight: FontWeight.w700)
                    .copyWith(letterSpacing: 1.2)),
          ),
        ),
      ],
    );
  }
}
