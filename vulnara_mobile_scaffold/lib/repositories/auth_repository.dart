// repositories/auth_repository.dart -- wraps contract section 1 (Auth).

import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../models/auth_tokens.dart';
import '../models/user.dart';

class AuthRepository {
  AuthRepository(this._client);

  final ApiClient _client;

  Future<LoginResult> login({required String email, required String password}) async {
    try {
      final response = await _client.dio.post('/auth/login', data: {
        'email': email,
        'password': password,
      });
      return LoginResult.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<User> register({
    required String email,
    required String password,
    required String fullName,
  }) async {
    try {
      final response = await _client.dio.post('/auth/register', data: {
        'email': email,
        'password': password,
        'full_name': fullName,
        'role': 'client',
      });
      return User.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<User> me() async {
    try {
      final response = await _client.dio.get('/auth/me');
      return User.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<void> logout(String refreshToken) async {
    try {
      await _client.dio.post('/auth/logout', data: {'refresh_token': refreshToken});
    } on DioException catch (e) {
      // Logout failing server-side (e.g. token already expired) shouldn't
      // block the client from clearing its own local session -- the
      // caller (auth_provider) clears local tokens regardless.
      if (e.response?.statusCode != 401) rethrow;
    }
  }

  Future<User> updateProfile({
    String? fullName,
    String? email,
    String? currentPassword,
    String? newPassword,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (fullName != null) body['full_name'] = fullName;
      if (email != null) body['email'] = email;
      if (currentPassword != null) body['current_password'] = currentPassword;
      if (newPassword != null) body['new_password'] = newPassword;
      final response = await _client.dio.patch('/auth/me', data: body);
      return User.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }
}

// ── Admin user management ──────────────────────────────────────────────────

class AdminRepository {
  AdminRepository(this._client);
  final ApiClient _client;

  Future<List<Map<String, dynamic>>> listUsers() async {
    try {
      final response = await _client.dio.get('/admin/users');
      return (response.data as List).cast<Map<String, dynamic>>();
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<Map<String, dynamic>> getUserScans(String userId) async {
    try {
      final response = await _client.dio.get('/admin/users/$userId/scans');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<Map<String, dynamic>> toggleUserActive(String userId, {required bool isActive}) async {
    try {
      final response = await _client.dio.patch('/admin/users/$userId', data: {'is_active': isActive});
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }
}

