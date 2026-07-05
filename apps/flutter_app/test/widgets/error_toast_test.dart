import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/api/exceptions.dart';
import 'package:selfwell_app/widgets/error_toast.dart';

void main() {
  Widget _host(Widget child) =>
      MaterialApp(home: Scaffold(body: child));

  testWidgets('ErrorToast.show(userError) shows SnackBar',
      (WidgetTester tester) async {
    await tester.pumpWidget(_host(
      Builder(
        builder: (BuildContext context) => ElevatedButton(
          onPressed: () => ErrorToast.show(
            context,
            ApiException(
              code: 'E_USER_INVALID_INPUT',
              message: '请检查输入',
              severity: ErrorSeverity.userError,
            ),
          ),
          child: const Text('show'),
        ),
      ),
    ));

    await tester.tap(find.text('show'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('请检查输入'), findsOneWidget);
  });

  testWidgets('ErrorToast.show(permanent) opens AlertDialog',
      (WidgetTester tester) async {
    await tester.pumpWidget(_host(
      Builder(
        builder: (BuildContext context) => ElevatedButton(
          onPressed: () => ErrorToast.show(
            context,
            ApiException(
              code: 'E_COMPLIANCE_USER_BLOCKED',
              message: '账号已被永久封禁',
              severity: ErrorSeverity.permanent,
            ),
          ),
          child: const Text('show'),
        ),
      ),
    ));

    await tester.tap(find.text('show'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 300));

    expect(find.text('账号已被永久封禁'), findsOneWidget);
    expect(find.byType(AlertDialog), findsOneWidget);
  });
}