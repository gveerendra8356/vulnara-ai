// providers/auth_provider.dart -- session state for the whole app.
// router.dart reads `authProvider` to decide login-screen vs. app-shell
// redirects; ApiClient.onSessionExpired (wired in build()) routes back
// to logged-out state the moment a refresh fails anywhere in the app,
// not just on a manual logout tap.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_exception.dart';
import '../models/user.dart';
import 'core_providers.dart';

sealed class AuthState {
  const AuthState();
}

class AuthUnknown extends AuthState {
  const AuthUnknown();
}

class AuthLoggedOut extends AuthState {
  const AuthLoggedOut({this.error});
  final String? error;
}

class AuthLoggingIn extends AuthState {
  const AuthLoggingIn();
}

class AuthLoggedIn extends AuthState {
  const AuthLoggedIn(this.user);
  final User user;
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._ref) : super(const AuthUnknown()) {
    _ref.read(apiClientProvider).onSessionExpired = () {
      state = const AuthLoggedOut(error: 'Your session expired -- please sign in again.');
    };
    _tryRestoreSession();
  }

  final Ref _ref;

  Future<void> _tryRestoreSession() async {
    final storage = _ref.read(secureStorageProvider);
    if (!await storage.hasSession) {
      state = const AuthLoggedOut();
      return;
    }
    try {
      final user = await _ref.read(authRepositoryProvider).me();
      state = AuthLoggedIn(user);
      await _ref.read(pushNotificationServiceProvider).registerDevice();
    } catch (_) {
      await storage.clearTokens();
      state = const AuthLoggedOut();
    }
  }

  Future<void> login({required String email, required String password}) async {
    state = const AuthLoggingIn();
    try {
      final result = await _ref.read(authRepositoryProvider).login(email: email, password: password);
      await _ref.read(secureStorageProvider).saveTokens(
            accessToken: result.accessToken,
            refreshToken: result.refreshToken,
          );
      state = AuthLoggedIn(result.user);
      await _ref.read(pushNotificationServiceProvider).registerDevice();
    } on ApiException catch (e) {
      state = AuthLoggedOut(error: e.message);
    }
  }

  Future<void> logout() async {
    final storage = _ref.read(secureStorageProvider);
    final refreshToken = await storage.refreshToken;
    if (refreshToken != null) {
      await _ref.read(authRepositoryProvider).logout(refreshToken);
    }
    await storage.clearTokens();
    state = const AuthLoggedOut();
  }

  /// Update the user's profile (name / email / password). Returns null on
  /// success or an error message string on failure.
  Future<String?> updateProfile({
    String? fullName,
    String? email,
    String? currentPassword,
    String? newPassword,
  }) async {
    try {
      final updated = await _ref.read(authRepositoryProvider).updateProfile(
            fullName: fullName,
            email: email,
            currentPassword: currentPassword,
            newPassword: newPassword,
          );
      state = AuthLoggedIn(updated);
      return null; // success
    } on ApiException catch (e) {
      return e.message;
    } catch (e) {
      return e.toString();
    }
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) => AuthNotifier(ref));
