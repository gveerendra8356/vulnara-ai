// core/api_client.dart
//
// Single Dio instance for the whole app, with one interceptor that:
//   1. Attaches `Authorization: Bearer <access_token>` to every request.
//   2. On a 401 (and the request wasn't already a retry, and it wasn't
//      /auth/login or /auth/refresh itself), pauses, does ONE silent
//      token refresh, then retries the original request exactly once.
//   3. If refresh itself fails, clears the stored session and calls
//      [onSessionExpired] so the app can drop back to the login screen
//      -- wired up once in providers/auth_provider.dart rather than
//      here, to avoid this file depending on Riverpod.
//
// Concurrency note: if five requests all 401 at once, only the first
// triggers an actual refresh call -- the rest await the same in-flight
// Future via [_refreshCompleter] instead of firing five refresh calls.

import 'dart:async';

import 'package:dio/dio.dart';

import 'api_exception.dart';
import 'constants.dart';
import 'secure_storage.dart';

class ApiClient {
  ApiClient(this._storage) {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiConfig.baseUrl,
        connectTimeout: ApiConfig.connectTimeout,
        receiveTimeout: ApiConfig.receiveTimeout,
        contentType: 'application/json',
      ),
    );
    _dio.interceptors.add(_buildAuthInterceptor());
  }

  final SecureStorage _storage;
  late final Dio _dio;

  /// Called once when a refresh attempt fails -- i.e. the session is
  /// truly dead, not just the access token expiring normally.
  void Function()? onSessionExpired;

  Dio get dio => _dio;

  Completer<bool>? _refreshCompleter;

  static const _noAuthPaths = ['/auth/login', '/auth/register', '/auth/refresh'];

  InterceptorsWrapper _buildAuthInterceptor() {
    return InterceptorsWrapper(
      onRequest: (options, handler) async {
        if (!_noAuthPaths.any((p) => options.path.startsWith(p))) {
          final token = await _storage.accessToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token';
          }
        }
        handler.next(options);
      },
      onError: (DioException error, handler) async {
        final response = error.response;
        final requestOptions = error.requestOptions;

        final isAuthEndpoint = _noAuthPaths.any((p) => requestOptions.path.startsWith(p));
        final alreadyRetried = requestOptions.extra['retried'] == true;

        if (response?.statusCode == 401 && !isAuthEndpoint && !alreadyRetried) {
          final refreshed = await _refreshTokenSingleFlight();
          if (refreshed) {
            requestOptions.extra['retried'] = true;
            final token = await _storage.accessToken;
            requestOptions.headers['Authorization'] = 'Bearer $token';
            try {
              final retryResponse = await _dio.fetch(requestOptions);
              return handler.resolve(retryResponse);
            } on DioException catch (retryError) {
              return handler.next(retryError);
            }
          } else {
            await _storage.clearTokens();
            onSessionExpired?.call();
          }
        }

        handler.next(error);
      },
    );
  }

  Future<bool> _refreshTokenSingleFlight() {
    if (_refreshCompleter != null) return _refreshCompleter!.future;

    final completer = Completer<bool>();
    _refreshCompleter = completer;

    () async {
      try {
        final refreshToken = await _storage.refreshToken;
        if (refreshToken == null) {
          completer.complete(false);
          return;
        }
        final response = await _dio.post('/auth/refresh', data: {'refresh_token': refreshToken});
        final newAccess = response.data['access_token'] as String;
        // Contract 1.3 returns only { access_token, expires_in } -- the
        // refresh token itself is NOT rotated, so we keep the existing
        // one. (First draft of this file assumed rotation and tried to
        // read a refresh_token out of this response too -- that field
        // doesn't exist here and would have thrown on every refresh.)
        await _storage.saveTokens(accessToken: newAccess, refreshToken: refreshToken);
        completer.complete(true);
      } catch (_) {
        completer.complete(false);
      } finally {
        _refreshCompleter = null;
      }
    }();

    return completer.future;
  }

  /// Converts a caught DioException into our typed ApiException.
  /// Repositories should catch DioException and rethrow via this.
  static ApiException toApiException(DioException e) {
    final response = e.response;
    if (response != null) {
      return ApiException.fromResponseData(response.statusCode ?? 0, response.data);
    }
    return ApiException(
      statusCode: 0,
      code: 'network_error',
      message: 'Could not reach the server. Check your connection.',
    );
  }
}
