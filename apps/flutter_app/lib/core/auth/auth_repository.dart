/// Auth repository — single source of truth for login state.
///
/// Backed by [SecureStorage] (JWT persistence) and the [ApiService]
/// (transport). Exposed as a Riverpod provider so login / home / checkin
/// pages share the same instance and can `ref.read(authRepositoryProvider)`
/// without prop-drilling.
///
/// **Auth flow** (per `docs/api/openapi.yaml` `wxMpLogin`):
///   1. Client (Flutter) calls `wx.login` (we simulate with a code arg in MVP)
///   2. POST /auth/wx-login with `{ code, nickName, avatarUrl }`
///   3. Server returns `{ access_token, user_id, user_id_pseudo }`
///   4. Persist all three to [SecureStorage] + update [authStateProvider]
library;

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_service.dart';
import '../api/api_types.dart';
import '../api/dio_client.dart';
import '../api/exceptions.dart';
import '../storage/secure_storage.dart';
import 'router_refresh_notifier.dart';

/// Snapshot of the current user's auth state. Used by the router redirect
/// to gate `/splash` ↔ `/login` ↔ `/home` without re-hitting the API.
@immutable
class AuthState {
  const AuthState({
    required this.isLoggedIn,
    this.userId,
    this.userIdPseudo,
  });

  const AuthState.guest()
      : isLoggedIn = false,
        userId = null,
        userIdPseudo = null;

  final bool isLoggedIn;
  final String? userId;
  final String? userIdPseudo;

  AuthState copyWith({
    bool? isLoggedIn,
    String? userId,
    String? userIdPseudo,
  }) =>
      AuthState(
        isLoggedIn: isLoggedIn ?? this.isLoggedIn,
        userId: userId ?? this.userId,
        userIdPseudo: userIdPseudo ?? this.userIdPseudo,
      );
}

/// Provider exposing the live [AuthState] as a [StateProvider]. Pages and
/// the router watch this to react to login/logout transitions.
final StateProvider<AuthState> authStateProvider =
    StateProvider<AuthState>((_) => const AuthState.guest());

/// Provider for the [AuthRepository]. Reads its dependencies from the
/// ambient [ProviderContainer] so tests can override with mocks.
final Provider<AuthRepository> authRepositoryProvider =
    Provider<AuthRepository>((Ref ref) {
  final SecureStorage storage = ref.watch(secureStorageProvider);
  final ApiService api = ref.watch(apiServiceProvider);
  return AuthRepository(
    storage: storage,
    api: api,
    onStateChange: (AuthState s) {
      ref.read(authStateProvider.notifier).state = s;
      routerRefreshNotifier.refresh();
    },
  );
});

class AuthRepository {
  AuthRepository({
    required SecureStorage storage,
    required ApiService api,
    required this.onStateChange,
  })  : _storage = storage,
        _api = api;

  final SecureStorage _storage;
  final ApiService _api;
  final void Function(AuthState) onStateChange;

  /// Reads persisted JWT and synthesises an [AuthState] for router bootstrap.
  Future<AuthState> loadFromStorage() async {
    final String? token = await _storage.readJwt();
    if (token == null || token.isEmpty) return const AuthState.guest();
    final String? userId = await _storage.readUserId();
    final String? pseudo = await _storage.readUserIdPseudo();
    final AuthState s = AuthState(
      isLoggedIn: true,
      userId: userId,
      userIdPseudo: pseudo,
    );
    onStateChange(s);
    return s;
  }

  /// Calls POST /auth/wx-login. On success persists the JWT trio and
  /// publishes the new [AuthState].
  Future<AuthToken> wxLogin({
    required String code,
    String? nickName,
    String? avatarUrl,
  }) async {
    try {
      final AuthToken token = await _api.wxLogin(
        WxLoginRequest(code: code, nickName: nickName, avatarUrl: avatarUrl),
      );
      await _storage.writeJwt(token.accessToken);
      await _storage.writeUserId(token.userId);
      await _storage.writeUserIdPseudo(token.userIdPseudo);
      await _storage.writeLastLoginAt(DateTime.now());
      onStateChange(
        AuthState(
          isLoggedIn: true,
          userId: token.userId,
          userIdPseudo: token.userIdPseudo,
        ),
      );
      return token;
    } on DioException catch (e) {
      throw mapDioError(e);
    }
  }

  /// Clears local state and notifies the router. Server-side logout is
  /// fire-and-forget; local state must clear even if the API is down.
  Future<void> logout() async {
    try {
      await _storage.clearAll();
    } finally {
      onStateChange(const AuthState.guest());
    }
  }
}
