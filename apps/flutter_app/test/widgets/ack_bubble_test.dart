import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/widgets/ack_bubble.dart';

void main() {
  group('AckBubble §17 #15 (≤ 30 chars strict)', () {
    testWidgets('short ACK renders as-is without tooltip',
        (WidgetTester tester) async {
      const String text = '今天也辛苦你了';
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: AckBubble(text: text)),
        ),
      );
      expect(find.text(text), findsOneWidget);
      expect(find.byType(Tooltip), findsNothing);
    });

    testWidgets('over-long ACK is truncated to 30 chars + ellipsis',
        (WidgetTester tester) async {
      const String text =
          '这是一段超过三十个字符的心情日记回应文案用以验证截断逻辑是否生效';
      final AckBubble bubble = const AckBubble(text: text);
      expect(bubble.isTruncated, isTrue);
      expect(bubble.displayText.length, lessThanOrEqualTo(31)); // 30 + ellipsis
      expect(bubble.displayText.endsWith('…'), isTrue);

      await tester.pumpWidget(
        MaterialApp(home: Scaffold(body: bubble)),
      );
      // The full text is hidden inside the Tooltip, not directly in the tree.
      expect(find.byType(Tooltip), findsOneWidget);
      expect(find.text(bubble.displayText), findsOneWidget);
    });

    testWidgets('exactly 30 chars stays untruncated',
        (WidgetTester tester) async {
      const String text = '一二三四五六七八九十一二三四五六七八九十一二三四五六七八九十';
      expect(text.length, equals(30));
      final AckBubble bubble = const AckBubble(text: text);
      expect(bubble.isTruncated, isFalse);
      expect(bubble.displayText, text);
    });
  });
}