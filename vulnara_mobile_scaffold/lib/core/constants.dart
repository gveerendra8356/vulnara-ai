// core/constants.dart
//
// Central place for anything environment-specific. In a real project
// these would come from --dart-define / flavor config rather than being
// hardcoded, but keeping it simple and obvious for a student project.

class ApiConfig {
  ApiConfig._();

  /// Change this to your deployed backend's base URL.
  /// Use 10.0.2.2 instead of localhost when testing against a backend
  /// running on your dev machine from the Android emulator.
  static const String baseUrl = 'https://your-vulnara-backend.example.com';

  /// Same host, but ws(s):// scheme, for the live scan status socket.
  static const String wsBaseUrl = 'wss://your-vulnara-backend.example.com';

  static const Duration connectTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 15);
}

class StorageKeys {
  StorageKeys._();

  static const String accessToken = 'vulnara_access_token';
  static const String refreshToken = 'vulnara_refresh_token';
}
