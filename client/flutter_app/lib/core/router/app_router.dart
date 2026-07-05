import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../pages/diagnosis/upload/diagnosis_upload_page.dart';
import '../../pages/home/home_page.dart';
import '../../pages/login/login_page.dart';
import '../../pages/profile/profile_page.dart';
import '../../pages/splash/splash_page.dart';
import '../storage/secure_storage.dart';

/// Route names — exported as constants to avoid magic strings.
class AppRoutes {
  AppRoutes._();

  static const String splash = 'splash';
  static const String login = 'login';
  static const String home = 'home';
  static const String diagnosisUpload = 'diagnosis_upload';
  static const String diagnosisLoading = 'diagnosis_loading';
  static const String diagnosisReport = 'diagnosis_report';
  static const String plan = 'plan';
  static const String checkin = 'checkin';
  static const String assistantHome = 'assistant_home';
  static const String feedbackDiary = 'feedback_diary';
  static const String recallCompare = 'recall_compare';
  static const String community = 'community';
  static const String profile = 'profile';
  static const String shareHugCard = 'share_hug_card';
}

/// Builds the singleton [GoRouter]. Accepts the storage so the
/// `redirect` guard can decide between `/splash` and `/login` /
/// `/home` without an extra round-trip.
GoRouter buildAppRouter({required SecureStorage storage}) {
  return GoRouter(
    initialLocation: '/splash',
    debugLogDiagnostics: false,
    refreshListenable: RouterRefreshNotifier(),
    redirect: (BuildContext context, GoRouterState state) async {
      final String? token = await storage.readJwt();
      final String location = state.matchedLocation;

      if (token == null || token.isEmpty) {
        if (location == '/login' || location == '/splash') return null;
        return '/login';
      }

      if (location == '/splash' || location == '/login') return '/home';
      return null;
    },
    routes: <RouteBase>[
      GoRoute(
        path: '/splash',
        name: AppRoutes.splash,
        builder: (BuildContext _, __) => const SplashPage(),
      ),
      GoRoute(
        path: '/login',
        name: AppRoutes.login,
        builder: (BuildContext _, __) => const LoginPage(),
      ),
      GoRoute(
        path: '/home',
        name: AppRoutes.home,
        builder: (BuildContext _, __) => const HomePage(),
      ),
      GoRoute(
        path: '/diagnosis/upload',
        name: AppRoutes.diagnosisUpload,
        builder: (BuildContext _, __) => const DiagnosisUploadPage(),
      ),
      GoRoute(
        path: '/diagnosis/loading',
        name: AppRoutes.diagnosisLoading,
        builder: (BuildContext _, __) => const _SprintPlaceholder(
          pageName: 'diagnosis/loading',
        ),
      ),
      GoRoute(
        path: '/diagnosis/report',
        name: AppRoutes.diagnosisReport,
        builder: (BuildContext _, __) => const _SprintPlaceholder(
          pageName: 'diagnosis/report',
        ),
      ),
      GoRoute(
        path: '/plan',
        name: AppRoutes.plan,
        builder: (BuildContext _, __) => const _SprintPlaceholder(pageName: 'plan'),
      ),
      GoRoute(
        path: '/checkin',
        name: AppRoutes.checkin,
        builder: (BuildContext _, __) =>
            const _SprintPlaceholder(pageName: 'checkin'),
      ),
      GoRoute(
        path: '/assistant/home',
        name: AppRoutes.assistantHome,
        builder: (BuildContext _, __) =>
            const _SprintPlaceholder(pageName: 'assistant/home'),
      ),
      GoRoute(
        path: '/feedback/diary',
        name: AppRoutes.feedbackDiary,
        builder: (BuildContext _, __) =>
            const _SprintPlaceholder(pageName: 'feedback/diary'),
      ),
      GoRoute(
        path: '/recall/compare',
        name: AppRoutes.recallCompare,
        builder: (BuildContext _, __) =>
            const _SprintPlaceholder(pageName: 'recall/compare'),
      ),
      GoRoute(
        path: '/community',
        name: AppRoutes.community,
        builder: (BuildContext _, __) =>
            const _SprintPlaceholder(pageName: 'community'),
      ),
      GoRoute(
        path: '/profile',
        name: AppRoutes.profile,
        builder: (BuildContext _, __) => const ProfilePage(),
      ),
      GoRoute(
        path: '/share/hug-card',
        name: AppRoutes.shareHugCard,
        builder: (BuildContext _, __) =>
            const _SprintPlaceholder(pageName: 'share/hug_card'),
      ),
    ],
  );
}

/// Re-fires router redirects when the auth token changes. Exposed as a
/// public class so other layers (login flow, logout button) can call
/// [refresh] after writing to / clearing `SecureStorage`.
class RouterRefreshNotifier extends ChangeNotifier {
  /// Public alias used by `buildAppRouter`.
  // ignore: unused_element
  void refresh() => notifyListeners();
}

/// Tiny placeholder for pages not yet implemented in SF0. Keeps the
/// route table honest so go_router resolves every path today.
class _SprintPlaceholder extends StatelessWidget {
  const _SprintPlaceholder({required this.pageName});

  final String pageName;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Text('$pageName — placeholder (SF1+)'),
    );
  }
}