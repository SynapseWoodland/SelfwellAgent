import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/widgets/progress_ring.dart';

void main() {
  group('ProgressRing', () {
    testWidgets('renders custom center label', (WidgetTester tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Center(
              child: ProgressRing(
                size: 120,
                progress: 0.5,
                centerLabel: '7',
                centerSubLabel: '/ 21 天',
              ),
            ),
          ),
        ),
      );

      expect(find.text('7'), findsOneWidget);
      expect(find.text('/ 21 天'), findsOneWidget);
    });

    testWidgets('clamps invalid progress values via assert', (WidgetTester tester) async {
      expect(
        () => ProgressRing(progress: -0.1),
        throwsA(isA<AssertionError>()),
      );
      expect(
        () => ProgressRing(progress: 1.1),
        throwsA(isA<AssertionError>()),
      );
    });
  });
}