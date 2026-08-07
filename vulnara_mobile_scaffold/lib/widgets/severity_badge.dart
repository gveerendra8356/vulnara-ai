// widgets/severity_badge.dart -- small colored chip reused across the
// scan status and remediation screens for a consistent severity legend.

import 'package:flutter/material.dart';

class SeverityBadge extends StatelessWidget {
  const SeverityBadge({super.key, required this.severity});

  final String severity;

  Color _color(BuildContext context) => switch (severity) {
        'CRITICAL' => Colors.red.shade700,
        'HIGH' => Colors.orange.shade700,
        'MEDIUM' => Colors.amber.shade700,
        'LOW' => Colors.blue.shade600,
        _ => Colors.grey.shade600,
      };

  @override
  Widget build(BuildContext context) {
    final color = _color(context);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(6)),
      child: Text(
        severity,
        style: TextStyle(color: color, fontWeight: FontWeight.bold, fontSize: 11, letterSpacing: 0.5),
      ),
    );
  }
}
