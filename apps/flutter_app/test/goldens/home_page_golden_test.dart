import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/theme/app_theme.dart';
import 'package:selfwell_app/pages/home/home_page.dart';

import '../helpers/fake_api.dart';

/// §18 golden baseline for P02 (首页 / 今日打卡).
/// Reference: docs/design/figma-pixso-spec/pages/03-home.html
/// Allowed pixel diff: ≤ 2 % (per §17 hard-constraint #18).
void main() {
  testWidgets('home page matches design baseline (P02)',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(375, 812);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final FakeApi api = FakeApi();
    await tester.pumpWidget(
      ProviderScope(
        overrides: apiServiceOverrides(api),
        child: MaterialApp(
          theme: AppTheme.light(),
          home: const HomePage(),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    await expectLater(
      find.byType(HomePage),
      matchesGoldenFile('goldens/home_page.png'),
    );
  });
}
