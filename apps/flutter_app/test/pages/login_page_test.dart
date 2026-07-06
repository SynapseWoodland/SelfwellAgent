/// Widget tests for P01 wechat-login page (SF1).
///
/// IA-REF: docs/design/ia-and-wireframe.md §4.1 P01 启动页 / 登录页
/// 设计稿: docs/design/figma-pixso-spec/pages/02-login.html
/// 后端端点: openapi.yaml tag=[auth] operationId=wxMpLogin POST /auth/wx-login
///
/// §17 hard-constraints exercised:
///   - #11 no forbidden colors
///   - #13 endpoints from ApiPaths only
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/api/api_service.dart';
import 'package:selfwell_app/core/api/api_types.dart';
import 'package:selfwell_app/core/storage/secure_storage.dart';
import 'package:selfwell_app/pages/login/login_page.dart';

import '../widgets/fake_secure_storage.dart';

/// In-memory fake ApiService that simulates wxLogin with a controllable result.
class _FakeApi implements ApiService {
  AuthToken? next;
  Object? error;
  int callCount = 0;

  @override
  Future<AuthToken> wxLogin(WxLoginRequest req) async {
    callCount += 1;
    if (error != null) throw error!;
    return next ?? const AuthToken(
      accessToken: 'access-1',
      userId: 'u-1',
      userIdPseudo: 'p-1',
    );
  }

  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw UnimplementedError('not used in this test: ${invocation.memberName}');
}

ProviderContainer _containerWith({
  required FakeSecureStorage storage,
  required _FakeApi api,
}) {
  return ProviderContainer(
    overrides: <Override>[
      secureStorageProvider.overrideWithValue(storage),
      apiServiceProvider.overrideWithValue(api),
    ],
  );
}

void main() {
  group('LoginPage SF1', () {
    testWidgets('renders title + brand mark + wx-login CTA',
        (WidgetTester tester) async {
      final ProviderContainer container = _containerWith(
        storage: FakeSecureStorage(),
        api: _FakeApi(),
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: LoginPage()),
        ),
      );

      expect(find.text('Selfwell'), findsOneWidget);
      expect(find.text('慢慢自律，慢慢健康'), findsOneWidget);
      expect(find.text('慢慢成为更好的自己'), findsOneWidget);
      expect(find.text('微信一键登录'), findsOneWidget);
      expect(find.text('手机号登录'), findsOneWidget);
      expect(find.text('隐私政策'), findsOneWidget);
      expect(find.text('用户协议'), findsOneWidget);
      expect(find.byIcon(Icons.spa_outlined), findsOneWidget);
    });

    testWidgets('tapping 微信一键登录 persists JWT trio to storage',
        (WidgetTester tester) async {
      final FakeSecureStorage storage = FakeSecureStorage();
      final _FakeApi api = _FakeApi()
        ..next = const AuthToken(
          accessToken: 'access-fake',
          userId: 'u-fake',
          userIdPseudo: 'p-fake',
        );

      final ProviderContainer container = _containerWith(
        storage: storage,
        api: api,
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: LoginPage()),
        ),
      );

      await tester.tap(find.text('微信一键登录'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(api.callCount, 1);
      expect(await storage.readJwt(), 'access-fake');
      expect(await storage.readUserId(), 'u-fake');
      expect(await storage.readUserIdPseudo(), 'p-fake');
    });

    testWidgets('shows snackbar error when wxLogin throws',
        (WidgetTester tester) async {
      final _FakeApi api = _FakeApi()
        ..error = Exception('boom');
      final ProviderContainer container = _containerWith(
        storage: FakeSecureStorage(),
        api: api,
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: const MaterialApp(home: LoginPage()),
        ),
      );

      await tester.tap(find.text('微信一键登录'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(api.callCount, 1);
      expect(find.textContaining('boom'), findsOneWidget);
    });
  });
}
