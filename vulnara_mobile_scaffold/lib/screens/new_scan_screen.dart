// screens/new_scan_screen.dart -- build order item 3: scan trigger +
// authorization confirmation screen. The authorization checkbox and
// justification field are NOT optional UI polish -- contract 2.1 makes
// the server reject with 422 if authorization_confirmed isn't true or
// justification is empty, so this screen enforces the same gate
// client-side for immediate feedback, mirroring scan_repository.dart.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/api_exception.dart';
import '../providers/core_providers.dart';

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
  bool _activeTestingEnabled = false;
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
      appBar: AppBar(title: const Text('New scan')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _targetController,
                  decoration: const InputDecoration(
                    labelText: 'Target',
                    hintText: 'domain.com or IP address',
                  ),
                  validator: (v) => (v == null || v.trim().isEmpty) ? 'Target is required' : null,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _justificationController,
                  minLines: 3,
                  maxLines: 5,
                  decoration: const InputDecoration(
                    labelText: 'Authorization justification',
                    hintText: 'e.g. "I own this domain" or engagement/ticket reference',
                    alignLabelWithHint: true,
                  ),
                  validator: (v) =>
                      (v == null || v.trim().isEmpty) ? 'Required -- the server rejects an empty justification' : null,
                ),
                const SizedBox(height: 8),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  controlAffinity: ListTileControlAffinity.leading,
                  value: _authorizationConfirmed,
                  onChanged: (v) => setState(() => _authorizationConfirmed = v ?? false),
                  title: const Text('I confirm I own this target or have explicit written permission to test it.'),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _activeTestingEnabled,
                  onChanged: (v) => setState(() => _activeTestingEnabled = v),
                  title: const Text('Enable active testing'),
                  subtitle: const Text('Opt-in SQLi/XSS/command-injection payload testing (Task 5 module).'),
                ),
                const SizedBox(height: 16),
                if (_error != null) ...[
                  Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  const SizedBox(height: 12),
                ],
                FilledButton(
                  onPressed: _submitting ? null : _submit,
                  child: _submitting
                      ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                      : const Text('Start scan'),
                ),
              ],
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
