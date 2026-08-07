// router.dart -- go_router config with an auth-aware redirect: anything
// other than /login bounces to /login while AuthState is
// AuthLoggedOut/AuthUnknown, and /login itself bounces forward once
// logged in.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'providers/auth_provider.dart';
import 'screens/login_screen.dart';
import 'screens/new_scan_screen.dart';
import 'screens/remediation_approval_screen.dart';
import 'screens/remediation_list_screen.dart';
import 'screens/scan_list_screen.dart';
import 'screens/scan_status_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/scans',
    refreshListenable: _AuthListenable(ref),
    redirect: (context, state) {
      final authState = ref.read(authProvider);
      final loggedIn = authState is AuthLoggedIn;
      final onLoginPage = state.matchedLocation == '/login';

      if (authState is AuthUnknown) return null; // wait for restore attempt to resolve
      if (!loggedIn && !onLoginPage) return '/login';
      if (loggedIn && onLoginPage) return '/scans';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/scans', builder: (context, state) => const ScanListScreen()),
      GoRoute(path: '/scans/new', builder: (context, state) => const NewScanScreen()),
      GoRoute(
        path: '/scans/:scanId',
        builder: (context, state) => ScanStatusScreen(scanId: state.pathParameters['scanId']!),
      ),
      GoRoute(
        path: '/scans/:scanId/remediations',
        builder: (context, state) => RemediationListScreen(scanId: state.pathParameters['scanId']!),
      ),
      GoRoute(
        path: '/remediations/:remediationId',
        builder: (context, state) =>
            RemediationApprovalScreen(remediationId: state.pathParameters['remediationId']!),
      ),
    ],
  );
});

/// Bridges Riverpod's authProvider into a Listenable go_router can
/// watch, so a login/logout triggers `redirect` to re-run immediately
/// instead of only on the next navigation.
class _AuthListenable extends ChangeNotifier {
  _AuthListenable(this._ref) {
    _ref.listen(authProvider, (_, __) => notifyListeners());
  }
  final Ref _ref;
}
