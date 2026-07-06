import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/theme/app_theme.dart';
import 'package:selfwell_app/pages/share/hug_card_page.dart';

import '../helpers/fake_api.dart';

/// §18 golden baseline for P07 (抱抱卡 海报).
/// Reference: docs/design/figma-pixso-spec/pages/13-hug-card-day14.html
/// Allowed pixel diff: ≤ 2 % (per §17 hard-constraint #18).
///
/// 3 张海报共用 ?day=7/14/21 — golden snapshots for all three
/// should be regenerated after any visual tweak.
void main() {
  for (final int day in <int>[7, 14, 21]) {
    testWidgets('hug card day $day matches design baseline (P07-$day)',
        (WidgetTester tester) async {
      tester.view.physicalSize = const Size(750, 1000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final FakeApi api = FakeApi();
      await tester.pumpWidget(
        ProviderScope(
          overrides: apiServiceOverrides(api),
          child: MaterialApp(
            theme: AppTheme.light(),
            home: HugCardPage(day: day),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      await expectLater(
        find.byType(HugCardPage),
        matchesGoldenFile('goldens/hug_card_day_$day.png'),
      );
    });
  }
}
