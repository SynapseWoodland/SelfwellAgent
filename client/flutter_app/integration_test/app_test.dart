// SF0 integration test stub. Real e2e scenarios land in Sprint SF1+
// once `/auth/wx-login` + `/users/me` + `/checkins/today` endpoints
// are stable. Keeping the file present so `integration_test/` shows
// up in repo tree scans.

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('SF0 integration harness smoke', () {
    expect(1 + 1, 2);
  });
}