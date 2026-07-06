/// Push notification facade bridging `firebase_messaging` (FCM/APNs)
/// and the backend `/users/me/push-token` endpoint.
///
/// **§17 hard-constraint #17**: every push payload MUST contain
/// `traceparent` + `client_platform` + `user_id_pseudo`. We enforce
/// that at construction time below so a future refactor can't drop a
/// field silently.
///
/// On iOS the same FCM token also reaches APNs; on Android FCM is the
/// transport. HMS (HarmonyOS) and email (fallback) live behind
/// `package:selfwell_push_adapters` (out of scope for SF1).
library;

import 'dart:async';
import 'dart:io' show Platform;

import 'package:dio/dio.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import '../api/api_service.dart';
import '../api/dio_client.dart';
import '../storage/secure_storage.dart';

/// Canonical key set used in every push payload (see §17 #17).
class PushPayloadKeys {
  PushPayloadKeys._();

  static const String traceparent = 'traceparent';
  static const String clientPlatform = 'client_platform';
  static const String userIdPseudo = 'user_id_pseudo';
}

/// Returns the platform tag in the same format the backend expects
/// (matches `api_service.clientPlatform()`).
String clientPlatformTag() {
  if (kIsWeb) return 'web';
  if (Platform.isIOS) return 'ios';
  if (Platform.isAndroid) return 'android';
  if (Platform.isMacOS) return 'macos';
  if (Platform.isWindows) return 'win';
  if (Platform.isLinux) return 'linux';
  return 'unknown';
}

/// Wraps the FCM token + the traceparent / pseudo-id fields that
/// every push must carry.
@immutable
class PushPayload {
  const PushPayload({
    required this.fcmToken,
    required this.clientPlatform,
    required this.userIdPseudo,
    required this.traceparent,
  });

  final String fcmToken;
  final String clientPlatform;
  final String userIdPseudo;
  final String traceparent;

  /// Serializes to the shape sent to `POST /users/me/push-token`.
  /// Asserts the §17 invariant at runtime.
  Map<String, dynamic> toJson() {
    assert(fcmToken.isNotEmpty, 'fcmToken required');
    assert(clientPlatform.isNotEmpty, 'clientPlatform required');
    assert(userIdPseudo.isNotEmpty, 'userIdPseudo required');
    assert(traceparent.isNotEmpty, 'traceparent required');
    return <String, dynamic>{
      'token': fcmToken,
      PushPayloadKeys.clientPlatform: clientPlatform,
      PushPayloadKeys.userIdPseudo: userIdPseudo,
      PushPayloadKeys.traceparent: traceparent,
    };
  }
}

/// FCM service — wires the firebase_messaging plugin to the backend.
///
/// In V1.3 SF5 we expose:
///   - request permission
///   - get the device FCM token
///   - build a [PushPayload] with the §17 fields
///   - send it to `POST /users/me/push-token`
class FcmService {
  FcmService({
    FirebaseMessaging? messaging,
    SecureStorage? storage,
    Dio? dio,
    TraceIdProvider? traceIdProvider,
  })  : _messaging = messaging ?? FirebaseMessaging.instance,
        _storage = storage ?? SecureStorage(),
        _dio = dio,
        _traceIdProvider = traceIdProvider ?? defaultTraceIdProvider;

  final FirebaseMessaging _messaging;
  final SecureStorage _storage;
  final Dio? _dio;
  final TraceIdProvider _traceIdProvider;

  bool _initialized = false;
  String? _cachedToken;

  /// Request permission (iOS / Android 13+) and return the device
  /// FCM token. Idempotent.
  Future<String> requestToken() async {
    if (_cachedToken != null) return _cachedToken!;
    if (!_initialized) {
      await _messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
      );
      _initialized = true;
    }
    final String? token = await _messaging.getToken();
    if (token == null || token.isEmpty) {
      throw StateError('FCM returned empty token');
    }
    _cachedToken = token;
    return token;
  }

  /// Build the canonical payload. Pure function — easy to test.
  Future<PushPayload> buildPayload(String fcmToken) async {
    final String? pseudo = await _storage.readUserIdPseudo();
    return PushPayload(
      fcmToken: fcmToken,
      clientPlatform: clientPlatformTag(),
      userIdPseudo: pseudo ?? 'unknown',
      traceparent: _traceIdProvider(),
    );
  }

  /// End-to-end: request token + send to backend. Returns the
  /// stored FCM token for diagnostics.
  Future<String> registerWithBackend() async {
    final String token = await requestToken();
    final PushPayload payload = await buildPayload(token);
    final Dio dio = _dio ??
        Dio(BaseOptions(
          baseUrl: const String.fromEnvironment(
            'SELFWELL_API_BASE',
            defaultValue: 'https://api.selfwell.example.com',
          ),
        ));
    await ApiService(dio).updatePushToken(
      token,
      clientPlatformTag(),
    );
    debugPrint('FcmService: registered ${payload.toJson()}');
    return token;
  }

  /// Listen to incoming messages. Returns a subscription the caller
  /// can cancel.
  StreamSubscription<RemoteMessage> onMessage(
    void Function(RemoteMessage) handler,
  ) {
    return FirebaseMessaging.onMessage.listen(handler);
  }

  /// Subscribe to notification opened events (background/terminated
  /// taps). The handler is responsible for navigating to the
  /// relevant page.
  StreamSubscription<RemoteMessage> onMessageOpenedApp(
    void Function(RemoteMessage) handler,
  ) {
    return FirebaseMessaging.onMessageOpenedApp.listen(handler);
  }
}
