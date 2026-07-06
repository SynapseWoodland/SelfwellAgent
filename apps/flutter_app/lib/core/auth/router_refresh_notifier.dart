/// Re-fires router redirects when the auth token changes. Exposed as a
/// public class so other layers (login flow, logout button) can call
/// [refresh] after writing to / clearing `SecureStorage`.
///
/// Lives in `core/auth/` (not `core/router/`) so `auth_repository.dart`
/// and `app_router.dart` can both depend on it without creating a
/// `router → auth → router` import cycle.
library;

import 'package:flutter/foundation.dart';

class RouterRefreshNotifier extends ChangeNotifier {
  /// Public alias used by `buildAppRouter`.
  void refresh() => notifyListeners();
}

/// Singleton instance shared by the auth repository and the router.
final RouterRefreshNotifier routerRefreshNotifier = RouterRefreshNotifier();
