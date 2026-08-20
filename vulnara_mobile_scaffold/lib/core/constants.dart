// core/constants.dart
//
// Central place for anything environment-specific. In a real project
// these would come from --dart-define / flavor config rather than being
// hardcoded, but keeping it simple and obvious for a student project.

class ApiConfig {
  ApiConfig._();

  /// Production Render backend.
  /// For local dev against an emulator, change to: http://10.0.2.2:8000
  /// For local dev against iOS simulator / web: http://localhost:8000
  static const String baseUrl = 'http://10.0.2.2:8000';

  /// Same host, wss:// for the live scan status WebSocket.
  static const String wsBaseUrl = 'ws://10.0.2.2:8000';

  static const Duration connectTimeout = Duration(seconds: 60); // longer for Render cold-start
  static const Duration receiveTimeout = Duration(seconds: 60);
}

class StorageKeys {
  StorageKeys._();

  static const String accessToken = 'vulnara_access_token';
  static const String refreshToken = 'vulnara_refresh_token';
}


