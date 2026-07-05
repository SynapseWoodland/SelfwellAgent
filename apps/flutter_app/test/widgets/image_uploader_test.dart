import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/widgets/image_uploader.dart';

void main() {
  testWidgets('ImageUploader renders gallery + camera buttons by default',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ImageUploader(onPicked: (_) {}),
        ),
      ),
    );

    expect(find.text('从相册选图'), findsOneWidget);
    expect(find.text('拍一张'), findsOneWidget);
  });

  testWidgets('ImageUploader can hide camera source',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ImageUploader(
            onPicked: (_) {},
            pickFromCamera: false,
          ),
        ),
      ),
    );

    expect(find.text('拍一张'), findsNothing);
    expect(find.text('从相册选图'), findsOneWidget);
  });
}