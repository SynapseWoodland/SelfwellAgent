import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/notification/fcm_service.dart';

/// §17 hard-constraint #17:
///   推送 payload 必含 traceparent + client_platform + user_id_pseudo
///   (3 keys; never empty).
void main() {
  group('PushPayload §17 #17 invariant', () {
    test('toJson emits traceparent + clientPlatform + userIdPseudo', () {
      const PushPayload p = PushPayload(
        fcmToken: 'fcm-abc',
        clientPlatform: 'ios',
        userIdPseudo: 'pseudo-xyz',
        traceparent: '00-trace-001',
      );
      final Map<String, dynamic> json = p.toJson();
      expect(json['token'], 'fcm-abc');
      expect(json['client_platform'], 'ios');
      expect(json['user_id_pseudo'], 'pseudo-xyz');
      expect(json['traceparent'], '00-trace-001');
    });

    test('clientPlatformTag is one of the allowed short strings', () {
      final String tag = clientPlatformTag();
      expect(
        <String>['ios', 'android', 'macos', 'web', 'win', 'linux', 'unknown'],
        contains(tag),
      );
    });

    test('PushPayloadKeys match backend field names exactly', () {
      expect(PushPayloadKeys.traceparent, 'traceparent');
      expect(PushPayloadKeys.clientPlatform, 'client_platform');
      expect(PushPayloadKeys.userIdPseudo, 'user_id_pseudo');
    });
  });
}
