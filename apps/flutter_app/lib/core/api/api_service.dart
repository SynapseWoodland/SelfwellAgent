/// Thin typed wrapper around [Dio] for the 41 endpoints in
/// `docs/architecture/api.yaml`. Pages import this instead of Dio directly
/// so test doubles can override individual endpoints.
library;

import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api_types.dart';
import 'dio_client.dart';

/// Riverpod provider for the [ApiService] singleton. Tests override this
/// in `ProviderScope` to inject a fake.
final Provider<ApiService> apiServiceProvider =
    Provider<ApiService>((Ref ref) {
  final Dio dio = ref.watch(dioProvider);
  return ApiService(dio);
});

class ApiService {
  ApiService(this._dio);

  final Dio _dio;

  // -- M1 --
  Future<AuthToken> wxLogin(WxLoginRequest req) async {
    final Response<dynamic> r = await _dio.post<dynamic>(
      ApiPaths.authWxLogin,
      data: req.toJson(),
    );
    return AuthToken.fromJson(_asMap(r.data));
  }

  Future<UserProfile> getMe() async {
    final Response<dynamic> r = await _dio.get<dynamic>(ApiPaths.usersMe);
    return UserProfile.fromJson(_asMap(r.data));
  }

  Future<void> updatePushToken(String token, String platform) async {
    await _dio.post<dynamic>(
      ApiPaths.usersPushToken,
      data: <String, dynamic>{'token': token, 'platform': platform},
    );
  }

  // -- M2 --
  Future<DiagnosisJob> createDiagnosis(List<String> photoUrls) async {
    final Response<dynamic> r = await _dio.post<dynamic>(
      ApiPaths.diagnosis,
      data: CreateDiagnosisRequest(photoUrls: photoUrls).toJson(),
    );
    return DiagnosisJob.fromJson(_asMap(r.data));
  }

  Future<DiagnosisReport> getDiagnosis(String id) async {
    final Response<dynamic> r = await _dio.get<dynamic>(
      ApiPaths.diagnosisById(id),
    );
    return DiagnosisReport.fromJson(_asMap(r.data));
  }

  Future<DiagnosisReport?> getLatestDiagnosis() async {
    try {
      final Response<dynamic> r = await _dio.get<dynamic>(
        ApiPaths.diagnosisLatest,
      );
      return DiagnosisReport.fromJson(_asMap(r.data));
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  // -- M3 --
  Future<ActivePlan> getActivePlan() async {
    final Response<dynamic> r = await _dio.get<dynamic>(ApiPaths.plansActive);
    return ActivePlan.fromJson(_asMap(r.data));
  }

  Future<ActivePlan?> getActivePlanOrNull() async {
    try {
      return await getActivePlan();
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<ActivePlan> generatePlan() async {
    final Response<dynamic> r = await _dio.post<dynamic>(
      ApiPaths.plansGenerate,
    );
    return ActivePlan.fromJson(_asMap(r.data));
  }

  // -- M4 --
  Future<void> createCheckin(CreateCheckinRequest req) async {
    await _dio.post<dynamic>(ApiPaths.checkins, data: req.toJson());
  }

  Future<CheckinStats> getCheckinStats() async {
    final Response<dynamic> r = await _dio.get<dynamic>(ApiPaths.checkinsStats);
    return CheckinStats.fromJson(_asMap(r.data));
  }

  // -- M5 --
  Future<AssistantChatResponse> assistantChat(
    String sessionId,
    String content,
  ) async {
    final Response<dynamic> r = await _dio.post<dynamic>(
      ApiPaths.assistantChat,
      data: AssistantChatRequest(sessionId: sessionId, content: content)
          .toJson(),
    );
    return AssistantChatResponse.fromJson(_asMap(r.data));
  }

  // -- M6 --
  Future<List<CommunityPost>> listPosts({String filter = 'all'}) async {
    final Response<dynamic> r = await _dio.get<dynamic>(
      ApiPaths.communityPosts,
      queryParameters: <String, dynamic>{'filter': filter},
    );
    final List<dynamic> items = (_asMap(r.data)['items'] as List<dynamic>?) ??
        (_asMap(r.data)['posts'] as List<dynamic>?) ??
        const <dynamic>[];
    return items
        .map((dynamic e) => CommunityPost.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<CommunityPost> createPost(CreatePostRequest req) async {
    final Response<dynamic> r = await _dio.post<dynamic>(
      ApiPaths.communityPosts,
      data: req.toJson(),
    );
    return CommunityPost.fromJson(_asMap(r.data));
  }

  // -- M7 --
  Future<List<FeedbackEntry>> listFeedback({int page = 1, int size = 20}) async {
    final Response<dynamic> r = await _dio.get<dynamic>(
      ApiPaths.feedback,
      queryParameters: <String, dynamic>{'page': page, 'page_size': size},
    );
    final List<dynamic> items = (_asMap(r.data)['items'] as List<dynamic>?) ??
        const <dynamic>[];
    return items
        .map((dynamic e) => FeedbackEntry.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  // -- M8 --
  Future<RecallCompare> triggerRecall({int daysAgo = 90}) async {
    final Response<dynamic> r = await _dio.post<dynamic>(
      ApiPaths.butlerRecall,
      data: <String, dynamic>{'days_ago': daysAgo},
    );
    return RecallCompare.fromJson(_asMap(r.data));
  }

  // -- M10 --
  Future<HugCard> generateHugCard(int day) async {
    final Response<dynamic> r = await _dio.post<dynamic>(
      ApiPaths.sharePoster,
      data: <String, dynamic>{'day': day, 'template': 'hug_card'},
    );
    return HugCard.fromJson(_asMap(r.data));
  }

  // -- M9 (push subscription) --
  Future<void> subscribePush({required String templateId}) async {
    await _dio.post<dynamic>(
      ApiPaths.notificationsSubscribe,
      data: <String, dynamic>{'template_id': templateId},
    );
  }

  Map<String, dynamic> _asMap(dynamic data) {
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return data.cast<String, dynamic>();
    throw DioException(
      requestOptions: RequestOptions(path: '<unknown>'),
      response: Response<dynamic>(
        requestOptions: RequestOptions(path: '<unknown>'),
        statusCode: 500,
      ),
      type: DioExceptionType.badResponse,
      error: 'unexpected payload: $data',
    );
  }
}

/// Provides the platform tag used in push payloads (§17 #17).
String clientPlatform() {
  if (Platform.isIOS) return 'ios';
  if (Platform.isAndroid) return 'android';
  if (Platform.isMacOS) return 'macos';
  return 'unknown';
}
