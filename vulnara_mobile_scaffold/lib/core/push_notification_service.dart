// core/push_notification_service.dart
//
// Firebase Cloud Messaging setup for the `alert.critical` push path.
// Two delivery cases per FCM's own model, both handled here:
//   - Foreground: FCM delivers a *data* message silently; we show our
//     own local notification via flutter_local_notifications so the
//     user sees something even with the app open.
//   - Background/terminated: FCM shows the OS notification tray entry
//     itself using the `notification` block the backend sends (see
//     core/push_notifications.py on the backend) -- no app code runs
//     unless the user taps it, which is handled by
//     onMessageOpenedApp/getInitialMessage below.
//
// Registration flow: request permission -> get token -> hand it to
// DeviceRepository.registerToken(). Called once after login (see
// providers/auth_provider.dart) and again on onTokenRefresh, since FCM
// tokens can rotate at any time.

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart' show defaultTargetPlatform, TargetPlatform;
import 'package:flutter/widgets.dart' show WidgetsBinding;
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:go_router/go_router.dart';

import '../repositories/device_repository.dart';
import '../router.dart';

/// Must be a top-level function (not a class method) -- this is FCM's
/// requirement for the background message handler, since it can run in
/// a separate isolate with no app state.
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  // Nothing to do here for our use case: a real notification payload
  // (not just data-only) means the OS already renders the tray entry
  // without any app code running. This handler exists so FCM doesn't
  // log a warning about a missing background handler, and as the place
  // to add analytics/data-sync-on-receipt later if needed.
}

class PushNotificationService {
  PushNotificationService(this._deviceRepository);

  final DeviceRepository _deviceRepository;
  final _localNotifications = FlutterLocalNotificationsPlugin();

  /// initialize() is called on every login / session-restore; guard it so
  /// the listeners and channel are only ever wired once per process.
  bool _initialized = false;

  static const _channel = AndroidNotificationChannel(
    'vulnara_critical_alerts',
    'Critical vulnerability alerts',
    description: 'Notifications for CRITICAL severity findings during a scan.',
    importance: Importance.high,
  );

  Future<void> initialize() async {
    if (_initialized) return;
    _initialized = true;

    await FirebaseMessaging.instance.requestPermission(alert: true, badge: true, sound: true);

    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(_channel);

    await _localNotifications.initialize(
      const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
      // Tapping a notification the app itself displayed (foreground case):
      // the scan id travels in the payload so we can deep-link to it.
      onDidReceiveNotificationResponse: (response) =>
          _navigateToScan(response.payload),
    );

    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    // Foreground: show a local notification manually -- FCM does not
    // surface `notification` blocks to the OS tray while the app is open.
    FirebaseMessaging.onMessage.listen((message) {
      final notification = message.notification;
      if (notification == null) return;
      _localNotifications.show(
        notification.hashCode,
        notification.title,
        notification.body,
        NotificationDetails(
          android: AndroidNotificationDetails(_channel.id, _channel.name, channelDescription: _channel.description),
          iOS: const DarwinNotificationDetails(),
        ),
        // Carry the scan id so a tap on this notification deep-links.
        payload: message.data['scan_id'] as String?,
      );
    });

    // Background (app alive, not foregrounded): OS shows the tray entry and
    // delivers the message here when the user taps it.
    FirebaseMessaging.onMessageOpenedApp.listen(_openFromRemoteMessage);

    // Terminated: the tap that cold-started the app is retrieved once.
    final initialMessage = await FirebaseMessaging.instance.getInitialMessage();
    if (initialMessage != null) _openFromRemoteMessage(initialMessage);
  }

  void _openFromRemoteMessage(RemoteMessage message) {
    _navigateToScan(message.data['scan_id'] as String?);
  }

  /// Navigates to a scan's detail screen (or the Alerts Hub as a fallback)
  /// using the global navigator key, since this runs with no BuildContext.
  /// Deferred to after the current frame so navigation is safe even when
  /// the router is still mounting on a cold start.
  void _navigateToScan(String? scanId) {
    final route = (scanId != null && scanId.isNotEmpty)
        ? '/scans/$scanId'
        : '/notifications';
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final context = rootNavigatorKey.currentContext;
      if (context != null) context.push(route);
    });
  }

  /// Registers (or re-registers) this device's current FCM token with
  /// the backend, and keeps it registered if FCM rotates the token later.
  Future<void> registerDevice() async {
    final token = await FirebaseMessaging.instance.getToken();
    if (token != null) {
      await _deviceRepository.registerToken(
        fcmToken: token,
        platform: _currentPlatform(),
      );
    }
    FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
      _deviceRepository.registerToken(fcmToken: newToken, platform: _currentPlatform());
    });
  }

  String _currentPlatform() {
    // This app only targets Android/iOS, matching the DeviceTokens
    // CHECK constraint (migration 003) which rejects anything else.
    return defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android';
  }
}
