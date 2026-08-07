// repositories/scan_repository.dart -- wraps contract 2.1, 2.2, 2.3.

import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../models/scan.dart';

class ScanRepository {
  ScanRepository(this._client);

  final ApiClient _client;

  /// Contract 2.1 -- the mandatory authorization gate is enforced
  /// server-side (422 if not confirmed / justification empty), but we
  /// require it client-side too so the user gets instant feedback
  /// instead of a round trip.
  Future<Scan> createScan({
    required String target,
    required String authorizationJustification,
    required bool activeTestingEnabled,
  }) async {
    try {
      final response = await _client.dio.post('/scans', data: {
        'target': target,
        'authorization_confirmed': true,
        'authorization_justification': authorizationJustification,
        'active_testing_enabled': activeTestingEnabled,
      });
      return Scan.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<Scan> getScan(String scanId) async {
    try {
      final response = await _client.dio.get('/scans/$scanId');
      return Scan.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  /// Contract 2.3 -- paginated. Mobile keeps it simple: page 1, a fixed
  /// page_size, no infinite-scroll pagination UI in this scope.
  Future<List<Scan>> listScans({int page = 1, int pageSize = 20}) async {
    try {
      final response = await _client.dio.get('/scans', queryParameters: {
        'page': page,
        'page_size': pageSize,
      });
      final items = (response.data as List).cast<Map<String, dynamic>>();
      return items.map(Scan.fromJson).toList();
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<List<Map<String, dynamic>>> getVulnerabilities(String scanId) async {
    try {
      final response = await _client.dio.get('/scans/$scanId/vulnerabilities');
      return (response.data as List).cast<Map<String, dynamic>>();
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }
}
