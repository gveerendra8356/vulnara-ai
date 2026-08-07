// providers/core_providers.dart -- the foundation providers everything
// else depends on: storage, api client, repositories. Kept in one file
// since they're all simple singleton `Provider`s with no state of their
// own (the stateful stuff -- auth, scans -- gets its own file).

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/api_client.dart';
import '../core/push_notification_service.dart';
import '../core/secure_storage.dart';
import '../repositories/auth_repository.dart';
import '../repositories/device_repository.dart';
import '../repositories/remediation_repository.dart';
import '../repositories/scan_repository.dart';

final secureStorageProvider = Provider<SecureStorage>((ref) => SecureStorage());

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(ref.watch(secureStorageProvider));
});

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  return AuthRepository(ref.watch(apiClientProvider));
});

final scanRepositoryProvider = Provider<ScanRepository>((ref) {
  return ScanRepository(ref.watch(apiClientProvider));
});

final remediationRepositoryProvider = Provider<RemediationRepository>((ref) {
  return RemediationRepository(ref.watch(apiClientProvider));
});

final deviceRepositoryProvider = Provider<DeviceRepository>((ref) {
  return DeviceRepository(ref.watch(apiClientProvider));
});

final pushNotificationServiceProvider = Provider<PushNotificationService>((ref) {
  return PushNotificationService(ref.watch(deviceRepositoryProvider));
});
