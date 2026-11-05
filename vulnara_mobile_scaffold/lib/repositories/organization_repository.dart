// repositories/organization_repository.dart -- organization security
// overview (admin "network activity") and department management. Mirrors the
// web app's /overview and /departments endpoints.

import 'package:dio/dio.dart';

import '../core/api_client.dart';

class OrganizationRepository {
  OrganizationRepository(this._client);

  final ApiClient _client;

  /// Org-wide (admin) or department-scoped (analyst) security overview:
  /// metrics, discovered assets, recent activity, department breakdown.
  Future<Map<String, dynamic>> getOverview() async {
    try {
      final response = await _client.dio.get('/overview');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<List<Map<String, dynamic>>> listDepartments() async {
    try {
      final response = await _client.dio.get('/departments');
      return (response.data as List).cast<Map<String, dynamic>>();
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<void> createDepartment(String name, {String? description}) async {
    try {
      await _client.dio.post('/admin/departments', data: {
        'name': name,
        if (description != null && description.isNotEmpty) 'description': description,
      });
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<void> deleteDepartment(String departmentId) async {
    try {
      await _client.dio.delete('/admin/departments/$departmentId');
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }

  Future<void> assignUserDepartment(String userId, String? departmentId) async {
    try {
      await _client.dio.patch('/admin/users/$userId/department', data: {
        'department_id': departmentId,
      });
    } on DioException catch (e) {
      throw ApiClient.toApiException(e);
    }
  }
}
