import 'dart:async';
import 'dart:developer' as developer;
import 'dart:io' show Platform;

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';

import '../storage/secure_storage.dart';

/// Client-platform tag used in push payloads (§17 hard-constraint #17).
/// iOS P0 in V1.3; Android/HMS deferred.
enum ClientPlatform { flutterIos, flutterAndroid, flutterHarmony }

extension ClientPlatformX on ClientPlatform {
  String get wireValue {
    switch (this) {
      case ClientPlatform.flutterIos:
        return 'flutter_ios';
      case ClientPlatform.flutterAndroid:
        return 'flutter_android';
      case ClientPlatform.flutterHarmony:
        return 'flutter_harmony';
    }
  }
}

ClientPlatform _detectPlatform() {
  if (kIsWeb) return ClientPlatform.flutterAndroid;
  try {
    if (Platform.isIOS) return ClientPlatform.flutterIos;
    if (Platform.isAndroid) return ClientPlatform.flutterAndroid;
  } on UnsupportedError {
    // ignore — fall back to android
  }
  return ClientPlatform.flutterAndroid;
}

/// Initializes Firebase + FCM and produces FCM payloads whose shape matches
/// §17 hard-constraint #17:
///   `{ traceparent, client_platform, user_id_pseudo, ... }`
///
/// The class does not own lifecycle of FCM tokens — the backend
/// `users.updatePushToken` endpoint is called by `app_router` /
/// `NotificationCenter` after the user logs in.
class FcmService {
  FcmService({
    required this.storage,
    FirebaseMessaging? messaging,
    ClientPlatform? platform,
  })  : _messaging = messaging ?? FirebaseMessaging.instance,
        _platform = platform ?? _detectPlatform();

  final SecureStorage storage;
  final FirebaseMessaging _messaging;
  final ClientPlatform _platform;

  bool _initialized = false;

  Future<void> initialize() async {
    if (_initialized) return;
    await Firebase.initializeApp();

    // iOS: ask for permission. Android 13+ also requires POST_NOTIFICATIONS.
    final NotificationSettings settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: false,
    );
    if (kDebugMode) {
      developer.log(
        'fcm.permission=${settings.authorizationStatus}',
        name: 'selfwell.fcm',
      );
    }
    _initialized = true;
  }

  Future<String?> fetchToken() => _messaging.getToken();

  /// Subscribes to foreground messages. The returned [Stream] yields
  /// payloads that already include `traceparent`, `client_platform`, and
  /// `user_id_pseudo` (see [buildEnvelope]).
  Stream<PushPayload> onMessage() {
    final StreamController<PushPayload> controller =
        StreamController<PushPayload>.broadcast();

    FirebaseMessaging.onMessage.listen((RemoteMessage msg) {
      controller.add(_envelopeFromRemote(msg));
    });
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage msg) {
      controller.add(_envelopeFromRemote(msg));
    });

    return controller.stream;
  }

  /// Builds the standard 4-end payload envelope. Used by tests.
  Future<PushPayload> buildEnvelope({
    required String traceparent,
    required Map<String, dynamic> data,
  }) async {
    final String? pseudo = await storage.readUserIdPseudo();
    return PushPayload(
      traceparent: traceparent,
      clientPlatform: _platform,
      userIdPseudo: pseudo,
      data: data,
    );
  }

  PushPayload _envelopeFromRemote(RemoteMessage msg) {
    final String pseudo =
        (msg.data['user_id_pseudo'] as String?) ?? 'unknown';
    final String tp =
        (msg.data['traceparent'] as String?) ?? '00-0-0-00';
    return PushPayload(
      traceparent: tp,
      clientPlatform: _platform,
      userIdPseudo: pseudo,
      data: msg.data,
    );
  }
}

/// Standard push payload envelope. Mirrors §17 hard-constraint #17 fields.
@immutable
class PushPayload {
  const PushPayload({
    required this.traceparent,
    required this.clientPlatform,
    required this.userIdPseudo,
    required this.data,
  });

  final String traceparent;
  final ClientPlatform clientPlatform;
  final String? userIdPseudo;
  final Map<String, dynamic> data;

  String get clientPlatformValue => clientPlatform.wireValue;

  Map<String, dynamic> toMap() => <String, dynamic>{
        'traceparent': traceparent,
        'client_platform': clientPlatformValue,
        'user_id_pseudo': userIdPseudo,
        ...data,
      };
}