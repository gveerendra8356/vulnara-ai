// providers/notification_providers.dart
//
// Riverpod providers that back the Alerts Hub screen.
//
// notificationsProvider  – fetches and synthesises the unified feed from
//                          GET /scans + GET /remediations via
//                          NotificationRepository. Auto-disposes when
//                          the screen leaves the widget tree.

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/app_notification.dart';
import 'core_providers.dart';

final notificationsProvider =
    FutureProvider.autoDispose<List<AppNotification>>((ref) async {
  return ref.watch(notificationRepositoryProvider).fetchNotifications();
});
