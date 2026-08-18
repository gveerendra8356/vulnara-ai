// router.dart -- go_router config with an auth-aware redirect: anything
// other than /login bounces to /login while AuthState is
// AuthLoggedOut/AuthUnknown, and /login itself bounces forward once
// logged in.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'providers/auth_provider.dart';
import 'screens/admin_users_screen.dart';
import 'screens/audit_log_screen.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';
import 'screens/new_scan_screen.dart';
import 'screens/notifications_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/remediation_approval_screen.dart';
import 'screens/remediation_list_screen.dart';
import 'screens/scan_list_screen.dart';
import 'screens/scan_status_screen.dart';
import 'screens/vulnerability_detail_screen.dart';

final routerProvider = Provider<GoRouter>((ref) {
  return GoRouter(
    initialLocation: '/scans',
    refreshListenable: _AuthListenable(ref),
    redirect: (context, state) {
      final authState = ref.read(authProvider);
      final loggedIn = authState is AuthLoggedIn;
      final onLoginPage = state.matchedLocation == '/login';

      if (authState is AuthUnknown) return '/login'; // prevent booting secure routes before auth check resolves
      if (!loggedIn && !onLoginPage) return '/login';
      if (loggedIn && onLoginPage) return '/scans';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(path: '/dashboard', builder: (context, state) => const DashboardScreen()),
      GoRoute(path: '/scans', builder: (context, state) => const ScanListScreen()),
      GoRoute(path: '/scans/new', builder: (context, state) => const NewScanScreen()),
      GoRoute(path: '/notifications', builder: (context, state) => const NotificationsScreen()),
      GoRoute(path: '/profile', builder: (context, state) => const ProfileScreen()),
      GoRoute(path: '/audit-log', builder: (context, state) => const AuditLogScreen()),
      GoRoute(path: '/admin/users', builder: (context, state) => const AdminUsersScreen()),
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
      GoRoute(
        path: '/scans/:scanId/vulnerabilities/:vulnId',
        builder: (context, state) => VulnerabilityDetailScreen(
          scanId: state.pathParameters['scanId']!,
          vulnId: state.pathParameters['vulnId']!,
        ),
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
