import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_types.dart';
import '../../pages/assistant/assistant_home_page.dart';
import '../../pages/checkin/checkin_page.dart';
import '../../pages/community/community_page.dart';
import '../../pages/diagnosis/loading/diagnosis_loading_page.dart';
import '../../pages/diagnosis/report/diagnosis_report_page.dart';
import '../../pages/diagnosis/upload/diagnosis_upload_page.dart';
import '../../pages/feedback/feedback_diary_page.dart';
import '../../pages/home/home_page.dart';
import '../../pages/login/login_page.dart';
import '../../pages/plan/plan_page.dart';
import '../../pages/profile/profile_page.dart';
import '../../pages/recall/recall_compare_page.dart';
import '../../pages/share/hug_card_page.dart';
import '../../pages/splash/splash_page.dart';
import '../auth/router_refresh_notifier.dart';
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
    refreshListenable: routerRefreshNotifier,
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
        builder: (BuildContext context, GoRouterState state) {
          final Object? extra = state.extra;
          final String diagnosisId = extra is String
              ? extra
              : (extra is DiagnosisJob ? extra.id : 'sf1-dev-diagnosis');
          return DiagnosisLoadingPage(diagnosisId: diagnosisId);
        },
      ),
      GoRoute(
        path: '/diagnosis/report',
        name: AppRoutes.diagnosisReport,
        builder: (BuildContext context, GoRouterState state) {
          final Object? extra = state.extra;
          final String id = extra is String
              ? extra
              : (extra is DiagnosisReport
                  ? extra.id
                  : 'sf1-dev-diagnosis');
          return DiagnosisReportPage(diagnosisId: id);
        },
      ),
      GoRoute(
        path: '/plan',
        name: AppRoutes.plan,
        builder: (BuildContext _, __) => const PlanPage(),
      ),
      GoRoute(
        path: '/checkin',
        name: AppRoutes.checkin,
        builder: (BuildContext _, __) => const CheckinPage(),
      ),
      GoRoute(
        path: '/assistant/home',
        name: AppRoutes.assistantHome,
        builder: (BuildContext _, __) => const AssistantHomePage(),
      ),
      GoRoute(
        path: '/feedback/diary',
        name: AppRoutes.feedbackDiary,
        builder: (BuildContext _, __) => const FeedbackDiaryPage(),
      ),
      GoRoute(
        path: '/recall/compare',
        name: AppRoutes.recallCompare,
        builder: (BuildContext _, __) => const RecallComparePage(),
      ),
      GoRoute(
        path: '/community',
        name: AppRoutes.community,
        builder: (BuildContext _, __) => const CommunityPage(),
      ),
      GoRoute(
        path: '/profile',
        name: AppRoutes.profile,
        builder: (BuildContext _, __) => const ProfilePage(),
      ),
      GoRoute(
        path: '/share/hug-card',
        name: AppRoutes.shareHugCard,
        builder: (BuildContext context, GoRouterState state) {
          final String? dayParam = state.uri.queryParameters['day'];
          final int day = int.tryParse(dayParam ?? '') ?? 14;
          return HugCardPage(day: day);
        },
      ),
    ],
  );
}
