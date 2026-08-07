// models/auth_tokens.dart -- matches API contract 1.2 login response.
// (1.3 refresh returns just access_token + expires_in -- handled
// directly in api_client.dart since it never needs to become app state.)

import 'user.dart';

class LoginResult {
  LoginResult({
    required this.accessToken,
    required this.refreshToken,
    required this.expiresIn,
    required this.user,
  });

  final String accessToken;
  final String refreshToken;
  final int expiresIn;
  final User user;

  factory LoginResult.fromJson(Map<String, dynamic> json) => LoginResult(
        accessToken: json['access_token'] as String,
        refreshToken: json['refresh_token'] as String,
        expiresIn: json['expires_in'] as int,
        user: User.fromJson(json['user'] as Map<String, dynamic>),
      );
}
