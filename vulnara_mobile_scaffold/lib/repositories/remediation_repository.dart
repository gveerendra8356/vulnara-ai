// repositories/remediation_repository.dart -- wraps contract 5.2, 5.3,
// 5.4, 5.5.
//
// Note on 5.3 (`GET /scans/{scan_id}/remediations`): the contract marks
// its "Client" column as Web, but section 0's conventions explicitly
// say that column only documents which surface is *expected* to call
// an endpoint in practice -- "both clients hit the identical API".
// Mobile's approve/reject screen needs exactly this endpoint (filtered
// to status=PENDING) to know which remediations are awaiting a
// decision for a given scan, so it's used here deliberately, not by
// mistake.

import 'package:dio/dio.dart';

import '../core/api_client.dart';
import '../models/remediation.dart';

class RemediationRepository {
  RemediationRepository(this._client);

  final ApiClient _client;

  Future<List<Remediation>> listForScan(String scanId, {String status = 'PENDING'}) async {
    try {
      final response = await _client.dio.get(
        '/scans/$scanId/remediations',
        queryParameters: {'status': status},
      );
      final items = (response.data['items'] as List).cast<Map<String, dynamic>>();
      return items.map(Remediation.fromJson).toList();
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<Remediation> getRemediation(String remediationId) async {
    try {
      final response = await _client.dio.get('/remediations/$remediationId');
      return Remediation.fromJson(response.data as Map<String, dynamic>);
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<void> approve(String remediationId) async {
    try {
      await _client.dio.post('/remediations/$remediationId/approve');
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<void> reject(String remediationId, {String? reason}) async {
    try {
      await _client.dio.post('/remediations/$remediationId/reject', data: {
        if (reason != null && reason.isNotEmpty) 'reason': reason,
      });
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }
}
