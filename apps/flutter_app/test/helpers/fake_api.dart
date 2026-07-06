import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:selfwell_app/core/api/api_service.dart';
import 'package:selfwell_app/core/api/api_types.dart';
import 'package:selfwell_app/pages/login/login_page.dart' show apiServiceProvider;

/// Reusable fake [ApiService] for widget + golden tests. Replaces
/// the real [apiServiceProvider] override for any page that depends
/// on it.
class FakeApi extends ApiService {
  FakeApi() : super(Dio());

  UserProfile user = const UserProfile(userId: 'u-test', nickName: '小满');
  CheckinStats stats = const CheckinStats(
    streakDays: 3,
    totalDays: 12,
    fragments: 12,
  );
  ActivePlan? plan = const ActivePlan(
    id: 'p-test',
    totalDays: 21,
    days: <PlanDay>[
      PlanDay(day: 1, title: '呼吸放松', minutes: 5, completed: true),
      PlanDay(day: 2, title: '面部舒缓', minutes: 8),
      PlanDay(day: 3, title: '肩颈放松', minutes: 5),
    ],
  );
  DiagnosisReport diagnosisReport = const DiagnosisReport(
    id: 'r-test',
    improveDirections: <ImproveDirection>[
      ImproveDirection(
        title: '侧颈前伸',
        summary: '每 2h 做 1 次收下巴训练',
        severity: '轻度',
      ),
    ],
    tags: <String>['气色', '肩颈', '护眼'],
  );
  HugCard hugCard = const HugCard(
    id: 'h-test',
    day: 14,
    imageUrl: 'https://example.com/hug-14.png',
  );
  RecallCompare recallCompare = const RecallCompare(
    aiSummary: '我记得那时你说过最近总是疲倦；今天再看你，气色舒展了一些。',
    before: RecallSnapshot(id: 'b1', daysAgo: 90),
    now: RecallSnapshot(id: 'n1', daysAgo: 0),
  );
  List<CommunityPost> posts = <CommunityPost>[
    const CommunityPost(
      id: 'p1',
      nickName: '小明',
      body: '今天感觉特别轻松～',
      createdAt: '2026-07-06T10:00:00Z',
    ),
  ];
  List<FeedbackEntry> feedback = <FeedbackEntry>[
    const FeedbackEntry(
      id: 'f1',
      body: '今天练完感觉肩颈舒展了一些',
      createdAt: '2026-07-03T20:00:00Z',
      aiAck: '练完后身体给出的回应，总是比想象中更诚实',
    ),
  ];

  int createCheckinCalls = 0;
  int createPostCalls = 0;
  int createFeedbackCalls = 0;
  int generateHugCardCalls = 0;
  int triggerRecallCalls = 0;
  int updatePushTokenCalls = 0;

  @override
  Future<UserProfile> getMe() async => user;
  @override
  Future<CheckinStats> getCheckinStats() async => stats;
  @override
  Future<ActivePlan?> getActivePlanOrNull() async => plan;
  @override
  Future<ActivePlan> getActivePlan() async => plan ?? (throw StateError('none'));
  @override
  Future<DiagnosisReport> getDiagnosis(String id) async => diagnosisReport;
  @override
  Future<DiagnosisReport?> getLatestDiagnosis() async => diagnosisReport;
  @override
  Future<HugCard> generateHugCard(int day) async {
    generateHugCardCalls += 1;
    return HugCard(id: hugCard.id, day: day, imageUrl: hugCard.imageUrl);
  }

  @override
  Future<RecallCompare> triggerRecall({int daysAgo = 90}) async {
    triggerRecallCalls += 1;
    return recallCompare;
  }

  @override
  Future<List<CommunityPost>> listPosts({String filter = 'all'}) async => posts;
  @override
  Future<CommunityPost> createPost(CreatePostRequest req) async {
    createPostCalls += 1;
    return CommunityPost(
      id: 'p-new',
      nickName: '我',
      body: req.body,
      createdAt: DateTime.now().toIso8601String(),
    );
  }

  @override
  Future<List<FeedbackEntry>> listFeedback({
    int page = 1,
    int size = 20,
  }) async =>
      feedback;

  @override
  Future<void> createCheckin(CreateCheckinRequest req) async {
    createCheckinCalls += 1;
  }

  @override
  Future<void> updatePushToken(String token, String platform) async {
    updatePushTokenCalls += 1;
  }

  @override
  Future<AuthToken> wxLogin(WxLoginRequest req) async => const AuthToken(
        accessToken: 'jwt-test',
        userId: 'u-test',
        userIdPseudo: 'pseudo-test',
      );

  @override
  Future<AssistantChatResponse> assistantChat(
    String sessionId,
    String content,
  ) async =>
      const AssistantChatResponse(
        sessionId: 's-test',
        reply: '收到，慢慢来。',
        personaState: 'warm',
      );

  @override
  Future<ActivePlan> generatePlan() async => plan ?? (throw StateError('none'));
}

/// Returns the Riverpod overrides needed to wire [FakeApi] into
/// any page that depends on [apiServiceProvider].
List<Override> apiServiceOverrides(FakeApi api) {
  return <Override>[apiServiceProvider.overrideWithValue(api)];
}
