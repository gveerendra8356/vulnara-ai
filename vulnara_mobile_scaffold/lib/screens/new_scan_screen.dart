// screens/new_scan_screen.dart -- build order item 3: scan trigger +
// authorization confirmation screen. The authorization checkbox and
// justification field are NOT optional UI polish -- contract 2.1 makes
// the server reject with 422 if authorization_confirmed isn't true or
// justification is empty, so this screen enforces the same gate
// client-side for immediate feedback, mirroring scan_repository.dart.
//
// UI matches the Stitch "new_scan_configurator" mock: a focused modal
// card (no nav shell) with target/justification inputs, an explicit
// permission-confirmation card, an AI active-testing toggle card, and
// a full-width "INITIALIZE SCAN" footer CTA.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/api_exception.dart';
import '../providers/core_providers.dart';
import '../theme/vulnara_theme.dart';

class NewScanScreen extends ConsumerStatefulWidget {
  const NewScanScreen({super.key});

  @override
  ConsumerState<NewScanScreen> createState() => _NewScanScreenState();
}

class _NewScanScreenState extends ConsumerState<NewScanScreen> {
  final _formKey = GlobalKey<FormState>();
  final _targetController = TextEditingController();
  final _justificationController = TextEditingController();
  bool _authorizationConfirmed = false;
  bool _activeTestingEnabled = true;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _targetController.dispose();
    _justificationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: VulnaraColors.pageBackground,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(VulnaraSpacing.containerPadding),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 560),
              child: Container(
                decoration: BoxDecoration(
                  color: VulnaraColors.surface.withValues(alpha: 0.85),
                  borderRadius: BorderRadius.circular(VulnaraRadius.xl),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
                ),
                child: Form(
                  key: _formKey,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      // Header
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: const BoxDecoration(
                          border: Border(bottom: BorderSide(color: Colors.white10)),
                        ),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 40,
                              height: 40,
                              decoration: BoxDecoration(
                                color: VulnaraColors.surfaceContainer,
                                borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                                border: Border.all(color: VulnaraColors.outlineVariant),
                              ),
                              child: const Icon(Icons.radar, color: VulnaraColors.primary, size: 20),
                            ),
                            const SizedBox(width: 12),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('New Target Configuration', style: VulnaraFonts.headlineMd()),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Define parameters and establish rules of engagement.',
                                    style: VulnaraFonts.codeSm(color: VulnaraColors.onSurfaceVariant),
                                  ),
                                ],
                              ),
                            ),
                            IconButton(
                              icon: const Icon(Icons.close, color: VulnaraColors.outline),
                              onPressed: () => context.pop(),
                            ),
                          ],
                        ),
                      ),
                      // Form body
                      Padding(
                        padding: const EdgeInsets.all(20),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            const _FieldLabel(icon: Icons.language, label: 'TARGET ADDRESS / IP RANGE'),
                            const SizedBox(height: 8),
                            _ConfigField(
                              controller: _targetController,
                              hint: 'e.g., https://api.internal.corp or 10.0.0.1/24',
                              validator: (v) => (v == null || v.trim().isEmpty) ? 'Target is required' : null,
                            ),
                            const SizedBox(height: VulnaraSpacing.stackLg),
                            const _FieldLabel(
                              icon: Icons.gavel,
                              label: 'AUTHORIZATION JUSTIFICATION',
                              color: VulnaraColors.onSurfaceVariant,
                            ),
                            const SizedBox(height: 8),
                            _ConfigField(
                              controller: _justificationController,
                              hint: 'Provide Jira ticket reference, engagement code, or business '
                                  'context for this active scan...',
                              minLines: 3,
                              maxLines: 5,
                              validator: (v) => (v == null || v.trim().isEmpty)
                                  ? 'Required -- the server rejects an empty justification'
                                  : null,
                            ),
                            const SizedBox(height: VulnaraSpacing.stackLg),
                            InkWell(
                              borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                              onTap: () => setState(() => _authorizationConfirmed = !_authorizationConfirmed),
                              child: Container(
                                padding: const EdgeInsets.all(16),
                                decoration: BoxDecoration(
                                  color: VulnaraColors.surfaceContainer.withValues(alpha: 0.4),
                                  borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                                  border: Border.all(color: Colors.white.withValues(alpha: 0.05)),
                                ),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Container(
                                      width: 20,
                                      height: 20,
                                      margin: const EdgeInsets.only(top: 2),
                                      decoration: BoxDecoration(
                                        color: VulnaraColors.inputFill,
                                        borderRadius: BorderRadius.circular(4),
                                        border: Border.all(
                                          color: _authorizationConfirmed
                                              ? VulnaraColors.primary
                                              : VulnaraColors.outlineVariant,
                                        ),
                                      ),
                                      child: _authorizationConfirmed
                                          ? const Icon(Icons.check, size: 14, color: VulnaraColors.primary)
                                          : null,
                                    ),
                                    const SizedBox(width: 16),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'Explicit Permission Confirmation',
                                            style: VulnaraFonts.codeSm(fontWeight: FontWeight.w700),
                                          ),
                                          const SizedBox(height: 4),
                                          Text(
                                            'I confirm documented authorization exists to execute security '
                                            'testing against the defined infrastructure. I accept '
                                            'accountability for potential service disruption.',
                                            style: VulnaraFonts.inter(
                                              fontSize: 13,
                                              height: 18 / 13,
                                              color: VulnaraColors.onSurfaceVariant,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            const SizedBox(height: VulnaraSpacing.stackMd),
                            Container(
                              padding: const EdgeInsets.all(16),
                              decoration: BoxDecoration(
                                color: VulnaraColors.primary.withValues(alpha: 0.05),
                                borderRadius: BorderRadius.circular(VulnaraRadius.lg),
                                border: Border.all(color: VulnaraColors.primary.withValues(alpha: 0.2)),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            const Icon(Icons.smart_toy_outlined, size: 16, color: VulnaraColors.primary),
                                            const SizedBox(width: 6),
                                            Text(
                                              'Enable AI Active Testing',
                                              style: VulnaraFonts.codeSm(
                                                color: VulnaraColors.primary,
                                                fontWeight: FontWeight.w700,
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 4),
                                        Text(
                                          'Utilize on-the-fly LLM payload generation to bypass adaptive '
                                          'WAFs. May increase noise.',
                                          style: VulnaraFonts.inter(
                                            fontSize: 13,
                                            height: 18 / 13,
                                            color: VulnaraColors.primary.withValues(alpha: 0.7),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Switch(
                                    value: _activeTestingEnabled,
                                    onChanged: (v) => setState(() => _activeTestingEnabled = v),
                                    activeThumbColor: VulnaraColors.onPrimary,
                                    activeTrackColor: VulnaraColors.primary,
                                  ),
                                ],
                              ),
                            ),
                            if (_error != null) ...[
                              const SizedBox(height: VulnaraSpacing.stackMd),
                              Text(_error!, style: const TextStyle(color: VulnaraColors.error)),
                            ],
                          ],
                        ),
                      ),
                      // Footer CTA
                      Container(
                        padding: const EdgeInsets.all(20),
                        decoration: const BoxDecoration(
                          border: Border(top: BorderSide(color: Colors.white10)),
                        ),
                        child: SizedBox(
                          height: 56,
                          child: ElevatedButton(
                            onPressed: _submitting ? null : _submit,
                            style: ElevatedButton.styleFrom(
                              backgroundColor: VulnaraColors.primary,
                              foregroundColor: VulnaraColors.onPrimary,
                              elevation: 0,
                              shape:
                                  RoundedRectangleBorder(borderRadius: BorderRadius.circular(VulnaraRadius.lg)),
                            ),
                            child: _submitting
                                ? const SizedBox(
                                    height: 18,
                                    width: 18,
                                    child: CircularProgressIndicator(
                                        strokeWidth: 2, color: VulnaraColors.onPrimary),
                                  )
                                : Row(
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      const Icon(Icons.rocket_launch, size: 20),
                                      const SizedBox(width: 8),
                                      Text(
                                        'INITIALIZE SCAN',
                                        style: VulnaraFonts.labelCaps(color: VulnaraColors.onPrimary)
                                            .copyWith(fontSize: 13, letterSpacing: 1.5),
                                      ),
                                    ],
                                  ),
                          ),
                        ),
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

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (!_authorizationConfirmed) {
      setState(() => _error = 'You must confirm authorization before starting a scan.');
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      await ref.read(scanRepositoryProvider).createScan(
            target: _targetController.text.trim(),
            authorizationJustification: _justificationController.text.trim(),
            activeTestingEnabled: _activeTestingEnabled,
          );
      if (mounted) context.pop(true);
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }
}

class _FieldLabel extends StatelessWidget {
  const _FieldLabel({required this.icon, required this.label, this.color});

  final IconData icon;
  final String label;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final c = color ?? VulnaraColors.primary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: c),
        const SizedBox(width: 8),
        Text(label, style: VulnaraFonts.labelCaps(color: c)),
      ],
    );
  }
}

class _ConfigField extends StatelessWidget {
  const _ConfigField({
    required this.controller,
    required this.hint,
    this.minLines,
    this.maxLines = 1,
    this.validator,
  });

  final TextEditingController controller;
  final String hint;
  final int? minLines;
  final int maxLines;
  final String? Function(String?)? validator;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: VulnaraColors.inputFill,
        borderRadius: BorderRadius.circular(VulnaraRadius.lg),
        border: Border.all(color: VulnaraColors.outlineVariant),
      ),
      child: TextFormField(
        controller: controller,
        minLines: minLines,
        maxLines: maxLines,
        validator: validator,
        style: VulnaraFonts.codeSm(),
        cursorColor: VulnaraColors.primary,
        decoration: InputDecoration(
          border: InputBorder.none,
          contentPadding: const EdgeInsets.all(14),
          hintText: hint,
          hintStyle: VulnaraFonts.codeSm(color: VulnaraColors.outline.withValues(alpha: 0.5)),
        ),
      ),
    );
  }
}
