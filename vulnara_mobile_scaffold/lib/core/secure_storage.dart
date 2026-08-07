// core/secure_storage.dart
//
// Thin wrapper around flutter_secure_storage so the rest of the app
// (api_client.dart's interceptor, auth_provider.dart) never touches the
// plugin directly -- makes it swappable/mockable in tests.

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'constants.dart';

class SecureStorage {
  SecureStorage() : _storage = const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  Future<void> saveTokens({required String accessToken, required String refreshToken}) async {
    await _storage.write(key: StorageKeys.accessToken, value: accessToken);
    await _storage.write(key: StorageKeys.refreshToken, value: refreshToken);
  }

  Future<String?> get accessToken => _storage.read(key: StorageKeys.accessToken);
  Future<String?> get refreshToken => _storage.read(key: StorageKeys.refreshToken);

  Future<void> clearTokens() async {
    await _storage.delete(key: StorageKeys.accessToken);
    await _storage.delete(key: StorageKeys.refreshToken);
  }

  Future<bool> get hasSession async => (await accessToken) != null;
}
