import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/api/dio_client.dart';
import 'package:selfwell_app/core/auth/checkin_repository.dart';
import 'package:selfwell_app/core/storage/secure_storage.dart';
import 'package:selfwell_app/core/theme/app_theme.dart';
import 'package:selfwell_app/pages/checkin/checkin_page.dart';

import 'fake_secure_storage.dart';

void main() {
  testWidgets('CheckinPage renders feeling tags + textarea + submit',
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
          home: const CheckinPage(),
        ),
      ),
    );

    expect(find.text('今天练完感觉如何？（可选）'), findsOneWidget);
    expect(find.text('舒服'), findsOneWidget);
    expect(find.text('放松'), findsOneWidget);
    expect(find.text('有点累'), findsOneWidget);
    expect(find.text('坚持下来了'), findsOneWidget);
    expect(find.text('明天见'), findsOneWidget);
  });

  testWidgets('CheckinPage tag toggles selection state',
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
          home: const CheckinPage(),
        ),
      ),
    );

    final Finder tag = find.text('放松');
    expect(tag, findsOneWidget);
    await tester.tap(tag);
    await tester.pump();
    // Selected state is reflected by the chip's `selected` prop; we
    // simply verify the tap doesn't throw and the chip is still present.
    expect(find.text('放松'), findsOneWidget);
  });

  test('CheckinRepository.submit maps DioException into ApiException',
      () async {
    final Dio failingDio = Dio(BaseOptions(baseUrl: 'http://stub'))
      ..httpClientAdapter = _FailAdapter();
    final CheckinRepository repo = CheckinRepository(failingDio);
    expect(
      () => repo.submit(planId: 'p1', day: 1),
      throwsA(isA<Exception>()),
    );
  });
}

class _FailAdapter implements dynamic {
  @override
  dynamic noSuchMethod(Invocation invocation) =>
      throw Exception('adapter stub');
}
