/// In-memory fake of [SecureStorage] for widget tests.
///
/// Keeps the same surface but writes to a [Map] so tests don't touch the
/// `flutter_secure_storage` platform plugin (which is unavailable in
/// the Flutter test environment).
library;

import 'package:selfwell_app/core/storage/secure_storage.dart';

class FakeSecureStorage extends SecureStorage {
  FakeSecureStorage() : super(backend: _NoopBackend());

  final Map<String, String> _store = <String, String>{};
  String? _deviceId;
  String? _lastLoginAt;

  @override
  Future<void> writeJwt(String token) async => _store['jwt'] = token;
  @override
  Future<String?> readJwt() async => _store['jwt'];
  @override
  Future<void> writeUserId(String userId) async => _store['user_id'] = userId;
  @override
  Future<String?> readUserId() async => _store['user_id'];
  @override
  Future<void> writeUserIdPseudo(String pseudo) async =>
      _store['user_id_pseudo'] = pseudo;
  @override
  Future<String?> readUserIdPseudo() async => _store['user_id_pseudo'];
  @override
  Future<String> ensureDeviceId() async =>
      _deviceId ??= 'web-test-device';
  @override
  Future<String?> readDeviceId() async => _deviceId;
  @override
  Future<void> writeLastLoginAt(DateTime when) async =>
      _lastLoginAt = when.toIso8601String();
  @override
  Future<DateTime?> readLastLoginAt() async =>
      _lastLoginAt == null ? null : DateTime.tryParse(_lastLoginAt!);
  @override
  Future<void> clearAll() async => _store.clear();
}

class _NoopBackend implements FlutterSecureStorage {
  // `SecureStorage(...)` accepts a FlutterSecureStorage; we never call
  // any of its methods because FakeSecureStorage overrides every public
  // method. This noSuchMethod silences the analyzer's "unused" warning.
  @override
  dynamic noSuchMethod(Invocation invocation) => null;
}
