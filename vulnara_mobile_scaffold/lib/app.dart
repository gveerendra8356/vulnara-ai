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
    );
  }
}
