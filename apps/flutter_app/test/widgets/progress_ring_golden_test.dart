import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/theme/app_theme.dart';
import 'package:selfwell_app/widgets/progress_ring.dart';

/// Golden baseline for the home progress ring (P02).
/// Reference: docs/design/figma-pixso-spec/pages/03-home.html
///
/// Per §17 hard-constraint #18, this golden must visually align with the
/// HTML mockup within ≤ 2% pixel diff. Update with:
///   `flutter test --update-goldens test/widgets/progress_ring_golden_test.dart`
void main() {
  testWidgets('progress ring matches design baseline',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(375, 812);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      MaterialApp(
        theme: AppTheme.light(),
        home: const Scaffold(
          backgroundColor: Color(0xFFFAFBFC),
          body: Center(
            child: ProgressRing(
              size: 120,
              progress: 0.34,
              centerLabel: '7',
              centerSubLabel: '/ 21 天',
            ),
          ),
        ),
      ),
    );

    await expectLater(
      find.byType(ProgressRing),
      matchesGoldenFile('goldens/progress_ring_home.png'),
    );
  });
}