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
}
