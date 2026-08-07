// core/api_exception.dart
//
// Maps the backend's standard error envelope (API contract section on
// error responses: `{ "error": { "code", "message", "details" } }`)
// into a typed Dart exception so screens can show `message` directly
// without reaching into raw response JSON.

class ApiException implements Exception {
  ApiException({required this.statusCode, required this.code, required this.message, this.details});

  final int statusCode;
  final String code;
  final String message;
  final Map<String, dynamic>? details;

  /// True for 401s that aren't the login/refresh endpoints themselves --
  /// api_client.dart's interceptor already tries a silent refresh before
  /// this ever reaches calling code, so if you see this, the session is
  /// genuinely dead and the UI should route to the login screen.
  bool get isUnauthorized => statusCode == 401;

  factory ApiException.fromResponseData(int statusCode, dynamic data) {
    if (data is Map && data['error'] is Map) {
      final err = data['error'] as Map;
      return ApiException(
        statusCode: statusCode,
        code: (err['code'] as String?) ?? 'unknown_error',
        message: (err['message'] as String?) ?? 'Something went wrong.',
        details: (err['details'] as Map?)?.cast<String, dynamic>(),
      );
    }
    return ApiException(
      statusCode: statusCode,
      code: 'unknown_error',
      message: 'Something went wrong (HTTP $statusCode).',
    );
  }

  @override
  String toString() => 'ApiException($code): $message';
}
