/// Widget tests for P02 home dashboard (SF1).
///
/// IA-REF: docs/design/ia-and-wireframe.md §4.2 P02 首页
/// 设计稿: docs/design/figma-pixso-spec/pages/03-home.html
/// 后端端点:
///   - openapi.yaml tag=[users]    operationId=getCurrentUser  GET  /users/me
///   - openapi.yaml tag=[checkins] operationId=getCheckinStats  GET  /checkins/stats
///   - openapi.yaml tag=[plans]    operationId=getActivePlan    GET  /plans/active
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/api/api_service.dart';
import 'package:selfwell_app/core/api/api_types.dart';
import 'package:selfwell_app/pages/home/home_page.dart';
import 'package:selfwell_app/pages/login/login_page.dart';

import '../widgets/fake_secure_storage.dart';

class _FakeApi implements ApiService {
  _FakeApi({
    this.me,
    this.stats,
    this.plan,
  });

  final UserProfile? me;
  final CheckinStats? stats;
  final ActivePlan? plan;

  @override
  Future<UserProfile> getMe() async =>
      me ?? const UserProfile(userId: 'u', nickName: '小鹿');
  @override
  Future<CheckinStats> getCheckinStats() async =>
      stats ?? const CheckinStats(streakDays: 7, totalDays: 21, fragments: 1);
  @override
  Future<ActivePlan?> getActivePlanOrNull() async => plan;

  @override
  dynamic noSuchMethod(Invocation i) =>
      throw UnimplementedError('not used: ${i.memberName}');
}

const PlanDay _day = PlanDay(day: 1, title: '肩颈放松 12 分钟', minutes: 12);

List<Override> _overrides(_FakeApi api) => <Override>[
      secureStorageProvider.overrideWithValue(
        FakeSecureStorage()..writeJwt('jwt'),
      ),
      apiServiceProvider.overrideWithValue(api),
    ];

void main() {
  group('HomePage SF1', () {
    testWidgets('renders greeting + progress ring + plan tasks',
        (WidgetTester tester) async {
      final _FakeApi api = _FakeApi(
        me: const UserProfile(userId: 'u', nickName: '小鹿'),
        stats: const CheckinStats(streakDays: 7, totalDays: 21, fragments: 1),
        plan: ActivePlan(
          id: 'plan-1',
          days: const <PlanDay>[_day],
          totalDays: 21,
          phaseLabel: '阶段一：缓启动',
        ),
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: _overrides(api),
          child: const MaterialApp(home: HomePage()),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('早安，小鹿'), findsOneWidget);
      expect(find.text('今天也是慢慢变好的一天'), findsOneWidget);
      expect(find.textContaining('已连续走到第'), findsOneWidget);
    });

    testWidgets('shows empty-plan card when no active plan',
        (WidgetTester tester) async {
      final _FakeApi api = _FakeApi(plan: null);

      await tester.pumpWidget(
        ProviderScope(
          overrides: _overrides(api),
          child: const MaterialApp(home: HomePage()),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('还没有开始哦'), findsOneWidget);
      expect(find.text('从智能分析开始，生成你的专属养护参考。'), findsOneWidget);
      expect(find.text('去智能分析'), findsOneWidget);
    });

    testWidgets('shows retryable error UI when snapshot throws',
        (WidgetTester tester) async {
      final _FakeApi api = _FakeApi();

      await tester.pumpWidget(
        ProviderScope(
          overrides: <Override>[
            ..._overrides(api),
            homeSnapshotProvider.overrideWith(
              (Ref ref) async => throw Exception('network down'),
            ),
          ],
          child: const MaterialApp(home: HomePage()),
        ),
      );

      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('加载失败了，明天再试试吧'), findsOneWidget);
      expect(find.text('重试'), findsOneWidget);
    });
  });
}
