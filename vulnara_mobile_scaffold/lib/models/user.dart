// models/user.dart -- matches API contract 1.2/1.5 `user` shape.

class User {
  User({
    required this.userId,
    required this.email,
    required this.fullName,
    required this.role,
    this.departmentId,
  });

  final String userId;
  final String email;
  final String fullName;
  final String role; // 'admin' | 'analyst'
  final String? departmentId; // analyst's assigned department (null for admin / unassigned)

  factory User.fromJson(Map<String, dynamic> json) => User(
        userId: json['user_id'] as String,
        email: json['email'] as String,
        fullName: json['full_name'] as String,
        role: json['role'] as String,
        departmentId: json['department_id'] as String?,
      );
}
