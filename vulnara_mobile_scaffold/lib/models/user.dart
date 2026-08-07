// models/user.dart -- matches API contract 1.2/1.5 `user` shape.

class User {
  User({required this.userId, required this.email, required this.fullName, required this.role});

  final String userId;
  final String email;
  final String fullName;
  final String role; // 'admin' | 'analyst' | 'client'

  factory User.fromJson(Map<String, dynamic> json) => User(
        userId: json['user_id'] as String,
        email: json['email'] as String,
        fullName: json['full_name'] as String,
        role: json['role'] as String,
      );
}
