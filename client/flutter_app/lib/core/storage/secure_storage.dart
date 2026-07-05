import 'dart:io' show Platform;
import 'dart:math' as math;

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Keys used across the storage layer. Centralized to avoid magic strings.
class _Keys {
  _Keys._();

  static const String jwt = 'selfwell.jwt';
  static const String userId = 'selfwell.user_id';
  static const String userIdPseudo = 'selfwell.user_id_pseudo';
  static const String deviceId = 'selfwell.device_id';
  static const String lastLoginAt = 'selfwell.last_login_at';
}

/// Wraps `flutter_secure_storage` to hide platform knobs and provide a
/// single entry point for JWT / user_id / device_id / pseudo-id.
///
/// On Android the secure storage backend is EncryptedSharedPreferences,
/// on iOS it's the Keychain. The factory pattern (rather than a singleton)
/// keeps the dependency easy to mock in widget tests.
class SecureStorage {
  SecureStorage({FlutterSecureStorage? backend})
      : _storage = backend ?? _defaultBackend();

  final FlutterSecureStorage _storage;

  static FlutterSecureStorage _defaultBackend() {
    const AndroidOptions androidOpts =
        AndroidOptions(encryptedSharedPreferences: true);
    const IOSOptions iosOpts = IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
    );
    return const FlutterSecureStorage(
      aOptions: androidOpts,
      iOptions: iosOpts,
    );
  }

  Future<void> writeJwt(String token) => _storage.write(key: _Keys.jwt, value: token);

  Future<String?> readJwt() => _storage.read(key: _Keys.jwt);

  Future<void> writeUserId(String userId) =>
      _storage.write(key: _Keys.userId, value: userId);

  Future<String?> readUserId() => _storage.read(key: _Keys.userId);

  Future<void> writeUserIdPseudo(String pseudo) =>
      _storage.write(key: _Keys.userIdPseudo, value: pseudo);

  Future<String?> readUserIdPseudo() => _storage.read(key: _Keys.userIdPseudo);

  Future<String> ensureDeviceId() async {
    final String? existing = await _storage.read(key: _Keys.deviceId);
    if (existing != null && existing.isNotEmpty) return existing;
    final String generated = _generateDeviceId();
    await _storage.write(key: _Keys.deviceId, value: generated);
    return generated;
  }

  Future<String?> readDeviceId() => _storage.read(key: _Keys.deviceId);

  Future<void> writeLastLoginAt(DateTime when) => _storage.write(
        key: _Keys.lastLoginAt,
        value: when.toIso8601String(),
      );

  Future<DateTime?> readLastLoginAt() async {
    final String? raw = await _storage.read(key: _Keys.lastLoginAt);
    if (raw == null) return null;
    return DateTime.tryParse(raw);
  }

  Future<void> clearAll() => _storage.deleteAll();

  /// Generates a stable per-install pseudo-id. Format: `<platform>-<rand32hex>`.
  /// See §17 hard-constraint #17 (push payload `user_id_pseudo` requirement).
  static String _generateDeviceId() {
    final String platform = _platformTag();
    final math.Random rng = math.Random.secure();
    final String hex = List<int>.generate(16, (_) => rng.nextInt(256))
        .map((int b) => b.toRadixString(16).padLeft(2, '0'))
        .join();
    return '$platform-$hex';
  }

  static String _platformTag() {
    if (kIsWeb) return 'web';
    try {
      if (Platform.isIOS) return 'ios';
      if (Platform.isAndroid) return 'android';
      if (Platform.isMacOS) return 'macos';
      if (Platform.isWindows) return 'win';
      if (Platform.isLinux) return 'linux';
    } on UnsupportedError {
      // ignore — fall through
    }
    return 'unknown';
  }
}