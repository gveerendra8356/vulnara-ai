// app.dart -- root MaterialApp.router, wired to routerProvider.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'router.dart';
import 'theme/vulnara_theme.dart';

class VulnaraApp extends ConsumerWidget {
  const VulnaraApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);

    return MaterialApp.router(
      title: 'Vulnara',
      theme: buildVulnaraTheme(),
      darkTheme: buildVulnaraTheme(),
      themeMode: ThemeMode.dark,
      routerConfig: router,
      // Keep the UI readable and intact across the full range of device
      // sizes and system font-scale settings. The layout already adapts
      // to width/height; this clamps the OS "font size" accessibility
      // setting to a band the dense, fixed-size design can absorb without
      // text overflowing its cards or the chrome stretching out of shape.
      builder: (context, child) {
        final mq = MediaQuery.of(context);
        final clamped = mq.textScaler.clamp(
          minScaleFactor: 0.9,
          maxScaleFactor: 1.15,
        );
        return MediaQuery(
          data: mq.copyWith(textScaler: clamped),
          child: child!,
        );
      },
    );
  }
}
