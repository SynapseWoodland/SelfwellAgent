import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/api/dio_client.dart';
import 'package:selfwell_app/core/storage/secure_storage.dart';
import 'package:selfwell_app/core/theme/app_theme.dart';
import 'package:selfwell_app/pages/login/login_page.dart';

import 'fake_secure_storage.dart';

void main() {
  testWidgets('LoginPage renders WeChat + phone CTAs without auth',
      (WidgetTester tester) async {
    final FakeSecureStorage storage = FakeSecureStorage();

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          secureStorageProvider.overrideWithValue(storage),
          dioProvider.overrideWith(
            (Ref _) => Dio(BaseOptions(baseUrl: 'http://stub')),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.light(),
          home: const LoginPage(),
        ),
      ),
    );

    expect(find.text('Selfwell'), findsOneWidget);
    expect(find.text('微信一键登录'), findsOneWidget);
    expect(find.text('手机号登录'), findsOneWidget);
    expect(find.text('慢慢自律，慢慢健康'), findsOneWidget);
    expect(find.text('慢慢成为更好的自己'), findsOneWidget);
  });

  testWidgets('Tapping WeChat enters busy state', (WidgetTester tester) async {
    final FakeSecureStorage storage = FakeSecureStorage();

    await tester.pumpWidget(
      ProviderScope(
        overrides: <Override>[
          secureStorageProvider.overrideWithValue(storage),
          dioProvider.overrideWith(
            (Ref _) => Dio(BaseOptions(baseUrl: 'http://stub')),
          ),
        ],
        child: MaterialApp(
          theme: AppTheme.light(),
          home: const LoginPage(),
        ),
      ),
    );

    await tester.tap(find.byKey(const Key('login.wechat')));
    await tester.pump();
    // Without a backing server the request errors immediately, but the
    // button must enter the busy state first.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);
    await tester.pump(const Duration(seconds: 1));
  });
}
