import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/widgets/persona_bubble.dart';

void main() {
  testWidgets('PersonaBubble renders label per state',
      (WidgetTester tester) async {
    for (final PersonaState s in PersonaState.values) {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: PersonaBubbleWithLabel(state: s),
          ),
        ),
      );
      expect(find.text(s.label), findsOneWidget);
    }
  });

  test('enum extension maps warm -> mint color', () {
    expect(PersonaState.warm.bubbleColor, isA<Color>());
    expect(PersonaState.medicalGuarded.icon, Icons.shield_outlined);
  });
}