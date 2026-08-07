// repositories/device_repository.dart -- wraps POST /devices/register.
//
// This endpoint is NOT part of the original Task 2 API contract -- it
// was added on the backend in Task 6 specifically to support FCM (see
// vulnara-backend/migrations/003_add_device_tokens.sql and
// app/api/routes/devices.py). Flagging that here too so it's obvious
// this repository talks to new surface area, not something pre-existing
// that was simply undocumented in the contract file.

import 'package:dio/dio.dart';

import '../core/api_client.dart';

class DeviceRepository {
  DeviceRepository(this._client);

  final ApiClient _client;

  Future<void> registerToken({required String fcmToken, required String platform}) async {
    try {
      await _client.dio.post('/devices/register', data: {
        'fcm_token': fcmToken,
        'platform': platform,
      });
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }
}
