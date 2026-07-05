import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/widgets/task_card.dart';

void main() {
  testWidgets('TaskCard renders title + subtitle + CTA', (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TaskCard(
            title: '今日小动作',
            subtitle: '建议时段：晚间',
            ctaLabel: '开始',
            icon: Icons.self_improvement,
            onTap: () {},
          ),
        ),
      ),
    );

    expect(find.text('今日小动作'), findsOneWidget);
    expect(find.text('建议时段：晚间'), findsOneWidget);
    expect(find.text('开始'), findsOneWidget);
    expect(find.byIcon(Icons.self_improvement), findsOneWidget);
  });

  testWidgets('completed TaskCard flips palette to primaryMint',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: TaskCard(
            title: '已完成',
            subtitle: '已练 12 分钟',
            ctaLabel: '查看',
            completed: true,
          ),
        ),
      ),
    );

    expect(find.text('已完成'), findsOneWidget);
    expect(find.text('查看'), findsOneWidget);
  });
}