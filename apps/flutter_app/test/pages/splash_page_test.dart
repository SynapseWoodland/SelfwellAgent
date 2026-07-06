/// Widget tests for P01 splash page (SF1).
///
/// IA-REF: docs/design/ia-and-wireframe.md §1.2 启动流程 (P01)
/// 设计稿: docs/design/figma-pixso-spec/pages/01-splash.html
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:selfwell_app/core/storage/secure_storage.dart';
import 'package:selfwell_app/pages/splash/splash_page.dart';

import '../widgets/fake_secure_storage.dart';

GoRouter _hostRouter() {
  return GoRouter(
    initialLocation: '/splash',
    routes: <RouteBase>[
      GoRoute(
        path: '/splash',
        builder: (BuildContext _, __) => const SplashPage(),
      ),
      GoRoute(
        path: '/login',
        builder: (BuildContext _, __) =>
            const Scaffold(body: Center(child: Text('LOGIN_PAGE'))),
      ),
      GoRoute(
        path: '/home',
        builder: (BuildContext _, __) =>
            const Scaffold(body: Center(child: Text('HOME_PAGE'))),
      ),
    ],
  );
}

void main() {
  group('SplashPage SF1', () {
    testWidgets('renders brand mark and progress indicator when no JWT',
        (WidgetTester tester) async {
      final FakeSecureStorage storage = FakeSecureStorage();
      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            secureStorageProvider.overrideWithValue(storage),
          ],
          child: MaterialApp.router(routerConfig: _hostRouter()),
        ),
      );
      await tester.pump();

      expect(find.text('Selfwell'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.byIcon(Icons.spa_outlined), findsOneWidget);
    });

    testWidgets('redirects to /home when JWT already present',
        (WidgetTester tester) async {
      final FakeSecureStorage storage = FakeSecureStorage();
      await storage.writeJwt('token-already-set');

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            secureStorageProvider.overrideWithValue(storage),
          ],
          child: MaterialApp.router(routerConfig: _hostRouter()),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('HOME_PAGE'), findsOneWidget);
    });

    testWidgets('redirects to /login when JWT missing',
        (WidgetTester tester) async {
      final FakeSecureStorage storage = FakeSecureStorage();

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            secureStorageProvider.overrideWithValue(storage),
          ],
          child: MaterialApp.router(routerConfig: _hostRouter()),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('LOGIN_PAGE'), findsOneWidget);
    });
  });
}
