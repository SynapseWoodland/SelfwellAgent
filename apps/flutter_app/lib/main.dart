import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/api/dio_client.dart';
import 'core/router/app_router.dart';
import 'core/storage/secure_storage.dart';
import 'core/theme/app_theme.dart';
import 'core/theme/color_tokens.dart';
import 'pages/splash/splash_page.dart' show secureStorageProvider;

/// App entry point. Wires:
///   1. ProviderScope + Riverpod
///   2. Token bootstrap (device_id, JWT) via SecureStorage
///   3. ThemeData from design tokens
///   4. go_router with auth-aware redirect
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final ProviderContainer container = ProviderContainer();
  final SecureStorage storage = container.read(secureStorageProvider);
  await storage.ensureDeviceId();
  runApp(
    UncontrolledProviderScope(
      container: container,
      child: const SelfwellApp(),
    ),
  );
}

class SelfwellApp extends ConsumerWidget {
  const SelfwellApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final SecureStorage storage = ref.watch(secureStorageProvider);

    return MaterialApp.router(
      title: 'Selfwell',
      theme: AppTheme.light(),
      debugShowCheckedModeBanner: false,
      routerConfig: buildAppRouter(storage: storage),
      builder: (BuildContext context, Widget? child) {
        return Banner(
          message: 'SF0 scaffold',
          location: BannerLocation.topEnd,
          color: AppColors.primaryPeach,
          child: child ?? const SizedBox.shrink(),
        );
      },
    );
  }
}

/// Provider exposing the singleton [Dio]. Tests can override with a mock.
final Provider<Dio> dioProvider = Provider<Dio>((Ref ref) {
  final SecureStorage storage = ref.watch(secureStorageProvider);
  return buildDio(
    baseUrl: const String.fromEnvironment(
      'SELFWELL_API_BASE',
      defaultValue: 'https://api.selfwell.example.com/v1',
    ),
    tokenProvider: storage.readJwt,
  );
});