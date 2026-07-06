import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/theme/app_theme.dart';
import 'package:selfwell_app/pages/diagnosis/report/diagnosis_report_page.dart';

import '../helpers/fake_api.dart';

/// §18 golden baseline for the diagnosis report (P03c).
/// Reference: docs/design/figma-pixso-spec/pages/06-butler-analyze-report.html
/// Allowed pixel diff: ≤ 2 % (per §17 hard-constraint #18).
///
/// Update with:
///   flutter test --update-goldens test/goldens/diagnosis_report_golden_test.dart
void main() {
  testWidgets('diagnosis report matches design baseline (P03c)',
      (WidgetTester tester) async {
    tester.view.physicalSize = const Size(375, 812);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    const String reportId = 'golden-diagnosis-001';
    final FakeApi api = FakeApi()
      ..diagnosisReport = const DiagnosisReport(
        id: reportId,
        improveDirections: <ImproveDirection>[
          ImproveDirection(
            title: '侧颈前伸',
            summary: '每 2h 做 1 次收下巴训练',
            severity: '轻度',
          ),
          ImproveDirection(
            title: '眼周疲劳',
            summary: '远眺 30 秒 + 热敷',
            severity: '轻度',
          ),
        ],
        tags: <String>['气色', '肩颈', '护眼', '发质'],
      );

    await tester.pumpWidget(
      ProviderScope(
        overrides: apiServiceOverrides(api),
        child: MaterialApp(
          theme: AppTheme.light(),
          home: const DiagnosisReportPage(diagnosisId: reportId),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    await expectLater(
      find.byType(DiagnosisReportPage),
      matchesGoldenFile('goldens/diagnosis_report.png'),
    );
  });
}
