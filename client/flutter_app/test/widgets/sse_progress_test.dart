import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/widgets/sse_progress.dart';

void main() {
  testWidgets('SseProgress renders 8-stage counter', (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: SseProgress(
            current: 3,
            total: 8,
            label: '正在分析肤况…',
          ),
        ),
      ),
    );

    expect(find.text('正在分析肤况…'), findsOneWidget);
    expect(find.text('3 / 8'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
  });

  test('asserts current <= total', () {
    expect(
      () => const SseProgress(current: 9, total: 8),
      throwsA(isA<AssertionError>()),
    );
  });
}