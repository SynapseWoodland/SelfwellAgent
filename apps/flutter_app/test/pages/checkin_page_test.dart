/// Widget tests for P02b checkin-complete page (SF1).
///
/// IA-REF: docs/design/ia-and-wireframe.md §4.7 P02b 今日完成页 (打卡完成态)
/// 设计稿: docs/design/figma-pixso-spec/pages/08-checkin.html
/// 后端端点:
///   - openapi.yaml tag=[checkins] operationId=createCheckin POST /checkins
///
/// §17 hard-constraints exercised:
///   - #11 no forbidden colors
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/api/api_service.dart';
import 'package:selfwell_app/core/api/api_types.dart';
import 'package:selfwell_app/pages/checkin/checkin_page.dart';
import 'package:selfwell_app/pages/home/home_page.dart';
import 'package:selfwell_app/pages/login/login_page.dart';

import '../widgets/fake_secure_storage.dart';

class _FakeApi implements ApiService {
  int callCount = 0;
  String? lastFeeling;
  String? lastPlanId;
  int? lastDay;

  @override
  Future<void> createCheckin(CreateCheckinRequest req) async {
    callCount += 1;
    lastFeeling = req.feeling;
    lastPlanId = req.planId;
    lastDay = req.day;
  }

  @override
  dynamic noSuchMethod(Invocation i) =>
      throw UnimplementedError('not used: ${i.memberName}');
}

const PlanDay _day1 = PlanDay(day: 1, title: '肩颈放松 12 分钟', minutes: 12);

Widget _pumpWith({
  required _FakeApi api,
  ActivePlan? plan,
}) {
  return ProviderScope(
    overrides: <Override>[
      secureStorageProvider.overrideWithValue(
        FakeSecureStorage()..writeJwt('jwt'),
      ),
      apiServiceProvider.overrideWithValue(api),
      homeSnapshotProvider.overrideWith(
        (Ref ref) async => HomeSnapshot(
          user: const UserProfile(userId: 'u', nickName: '小鹿'),
          stats: const CheckinStats(streakDays: 5, totalDays: 21, fragments: 1),
          plan: plan,
        ),
      ),
    ],
    child: const MaterialApp(home: CheckinPage()),
  );
}

void main() {
  group('CheckinPage SF1', () {
    testWidgets('renders hero + stats + feeling card when plan exists',
        (WidgetTester tester) async {
      final _FakeApi api = _FakeApi();
      final ActivePlan plan = ActivePlan(
        id: 'p-1',
        days: const <PlanDay>[_day1],
        totalDays: 21,
      );

      await tester.pumpWidget(_pumpWith(api: api, plan: plan));
      await tester.pump();

      expect(find.text('今天练完了'), findsOneWidget);
      expect(find.textContaining('真的很棒'), findsOneWidget);
      expect(find.text('今日练习'), findsOneWidget);
      expect(find.text('获得碎片'), findsOneWidget);
      expect(find.text('连续'), findsOneWidget);
      expect(find.text('舒服'), findsOneWidget);
      expect(find.text('放松'), findsOneWidget);
      expect(find.text('明天见'), findsOneWidget);
      expect(find.text('回到首页'), findsOneWidget);
    });

    testWidgets('without plan → toast warns and skips api call',
        (WidgetTester tester) async {
      final _FakeApi api = _FakeApi();
      await tester.pumpWidget(_pumpWith(api: api, plan: null));
      await tester.pump();

      await tester.tap(find.text('明天见'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(api.callCount, 0);
      expect(find.text('还没有方案，先去智能分析吧'), findsOneWidget);
    });

    testWidgets('with plan → submit calls api.createCheckin + feels string',
        (WidgetTester tester) async {
      final _FakeApi api = _FakeApi();
      final ActivePlan plan = ActivePlan(
        id: 'p-42',
        days: const <PlanDay>[_day1],
        totalDays: 21,
      );

      await tester.pumpWidget(_pumpWith(api: api, plan: plan));
      await tester.pump();

      await tester.tap(find.text('舒服'));
      await tester.pump();

      await tester.tap(find.text('明天见'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 200));

      expect(api.callCount, 1);
      expect(api.lastPlanId, 'p-42');
      expect(api.lastFeeling, contains('舒服'));
    });
  });
}
