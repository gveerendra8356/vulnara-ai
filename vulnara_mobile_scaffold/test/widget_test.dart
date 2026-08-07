// test/widget_test.dart
//
// Replaces the default `flutter create` template test, which references
// `MyApp` -- a class that doesn't exist here (our root widget is
// `VulnaraApp`, see lib/app.dart). This is why `flutter analyze` flagged
// the original file with "The name 'MyApp' isn't a class".
//
// This is a minimal smoke test, not real coverage (see README's "Known
// issues" section -- no test suite was built for this task, same gap
// noted for the backend at the end of Task 5). It just confirms the app
// boots to the login screen without throwing, since AuthNotifier starts
// in AuthUnknown -> AuthLoggedOut (no stored session in a fresh test
// environment) and router.dart redirects AuthLoggedOut to /login.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:vulnara_mobile/app.dart';
import 'package:vulnara_mobile/core/secure_storage.dart';
import 'package:vulnara_mobile/providers/core_providers.dart';

class FakeSecureStorage implements SecureStorage {
  @override
  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {}

  @override
  Future<String?> get accessToken async => null;

  @override
  Future<String?> get refreshToken async => null;

  @override
  Future<void> clearTokens() async {}

  @override
  Future<bool> get hasSession async => false;
}

void main() {
  testWidgets('App boots and redirects to the login screen', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          secureStorageProvider.overrideWithValue(FakeSecureStorage()),
        ],
        child: const VulnaraApp(),
      ),
    );

    // AuthNotifier's initial session-restore check runs async; pump past
    // it so the router's redirect (AuthUnknown -> AuthLoggedOut -> /login)
    // has settled before asserting.
    await tester.pumpAndSettle();

    expect(find.byType(TextFormField), findsWidgets); // email + password fields
    expect(find.text('Sign in'), findsOneWidget);
  });
}
