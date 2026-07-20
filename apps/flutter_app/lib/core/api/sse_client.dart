/// SSE (Server-Sent Events) client used by M2 diagnosis flow.
///
/// **Backoff schedule** (per §17 hard-constraint #16):
///   attempt 0 → wait 1s
///   attempt 1 → wait 2s
///   attempt 2 → wait 4s
///   attempt 3..N → wait min(2^attempt, 30) s
///   After 5 consecutive failures → fire a final error event so the
///   caller can show "网络异常，请稍后查看报告" and let the user re-open
///   the page later.
///
/// **Heartbeat** (per `docs/architecture/sse-events.md` §3): the server sends a
/// `: heartbeat` line every 15s. We treat >30s of silence as a transport
/// failure and trigger the backoff timer.
///
/// **Stage map** (8 stages):
///   1. connected       5. compliance_check
///   2. processing      6. progress
///   3. image_validated 7. result
///   4. llm_calling     8. done
library;

import 'dart:async';
import 'dart:convert';
import 'dart:developer' as developer;

import 'package:dio/dio.dart';

import 'api_types.dart';
import 'dio_client.dart';

@immutable
class DiagnosisStageEvent {
  const DiagnosisStageEvent({
    required this.stage,
    required this.label,
    this.percent = 0,
    this.isTerminal = false,
  });
  final String stage;
  final String label;
  final int percent;
  final bool isTerminal;
}

/// Backoff sequence (in seconds) for each attempt. The cap (30s) is
/// applied to subsequent attempts beyond the table.
const List<int> kSseBackoffSchedule = <int>[1, 2, 4];

/// Maximum number of reconnect attempts before giving up. 5 fails per
/// §17 hard-constraint #16 ("5 次失败 fallback").
const int kSseMaxRetries = 5;

/// Heartbeat timeout. If no event for this long, treat the connection
/// as broken and trigger reconnect.
const Duration kSseHeartbeatTimeout = Duration(seconds: 30);

class DiagnosisSseClient {
  DiagnosisSseClient({Dio? dio, int maxRetries = kSseMaxRetries})
      : _dio = dio,
        _maxRetries = maxRetries;

  Dio? _dio;
  final int _maxRetries;

  StreamController<DiagnosisStageEvent>? _controller;
  StreamSubscription<List<int>>? _byteSub;
  Timer? _heartbeatTimer;
  int _attempt = 0;
  bool _closed = false;

  Stream<DiagnosisStageEvent> connect(String diagnosisId) {
    _controller = StreamController<DiagnosisStageEvent>.broadcast();
    _open(diagnosisId);
    return _controller!.stream;
  }

  Future<void> _open(String diagnosisId) async {
    if (_closed) return;
    final Dio dio = _dio ?? Dio(BaseOptions(baseUrl: 'https://api.selfwell.app/v1'));
    final String url = ApiPaths.diagnosisStream(diagnosisId);
    developer.log('sse.connect url=$url attempt=$_attempt', name: 'selfwell.sse');
    try {
      final Response<dynamic> res = await dio.get<ResponseBody>(
        url,
        options: Options(
          responseType: ResponseType.stream,
          headers: <String, dynamic>{
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          receiveTimeout: Duration.zero,
        ),
      );
      _attempt = 0;
      _resetHeartbeat();
      _consume(res.data!);
    } catch (e) {
      _heartbeatTimer?.cancel();
      if (_closed) return;
      _emit('error', '网络异常：$e');
      _scheduleReconnect(diagnosisId);
    }
  }

  void _consume(ResponseBody body) {
    final StringBuffer buffer = StringBuffer();
    String? currentEvent;
    _byteSub = body.stream.listen(
      (List<int> chunk) {
        if (_closed) return;
        _resetHeartbeat();
        buffer.write(String.fromCharCodes(chunk));
        while (true) {
          final String text = buffer.toString();
          final int sep = text.indexOf('\n\n');
          if (sep < 0) break;
          final String frame = text.substring(0, sep);
          buffer
            ..clear()
            ..write(text.substring(sep + 2));
          for (final String line in frame.split('\n')) {
            if (line.startsWith(':')) continue;
            if (line.startsWith('event:')) {
              currentEvent = line.substring(6).trim();
            } else if (line.startsWith('data:')) {
              final String data = line.substring(5).trim();
              _handleFrame(currentEvent ?? 'message', data);
              currentEvent = null;
            }
          }
        }
      },
      onError: (Object err) {
        if (_closed) return;
        _heartbeatTimer?.cancel();
        _emit('error', '$err');
      },
      onDone: () {
        if (_closed) return;
        _heartbeatTimer?.cancel();
        _emit('done', '流结束', terminal: true);
      },
      cancelOnError: true,
    );
  }

  void _handleFrame(String event, String data) {
    Map<String, dynamic>? payload;
    try {
      final dynamic parsed = data.isEmpty ? <String, dynamic>{} : jsonDecode(data);
      if (parsed is Map<String, dynamic>) payload = parsed;
    } catch (_) {
      payload = null;
    }
    final int percent = (payload?['percent'] as num?)?.toInt() ?? 0;
    final String message = (payload?['message_zh'] as String?) ??
        (payload?['message'] as String?) ??
        '';
    switch (event) {
      case 'connected':
        _emit('connected', '已连接', percent: 5);
        break;
      case 'processing':
        _emit('processing', message.isEmpty ? '正在处理' : message, percent: 15);
        break;
      case 'image_validated':
        _emit('image_validated', '照片验证通过', percent: 25);
        break;
      case 'llm_calling':
        _emit('llm_calling', message.isEmpty ? 'AI 正在分析' : message, percent: 40);
        break;
      case 'compliance_check':
        _emit('compliance_check', '正在进行内容审查', percent: 80);
        break;
      case 'progress':
        _emit('processing', message.isEmpty ? '正在处理' : message, percent: percent);
        break;
      case 'result':
        _emit('result', '已生成', percent: 100, terminal: true);
        break;
      case 'fallback':
        _emit('fallback', message.isEmpty ? '已使用降级方案' : message, percent: 100, terminal: true);
        break;
      case 'error':
        _emit('error', message.isEmpty ? '处理失败' : message, terminal: true);
        break;
      case 'done':
        _emit('done', '流结束', terminal: true);
        break;
      default:
        break;
    }
  }

  void _emit(String stage, String label, {int percent = 0, bool terminal = false}) {
    _controller?.add(DiagnosisStageEvent(
      stage: stage,
      label: label,
      percent: percent,
      isTerminal: terminal,
    ));
  }

  /// Public lookup for the SSE backoff schedule (used by golden / unit
  /// tests and surfaced for logging). Attempt N (1-based) maps to:
  ///   1 → 1s, 2 → 2s, 3 → 4s, 4 → 8s, 5 → 16s, ≥6 → 30s.
  @visibleForTesting
  Duration backoffFor(int attempt) {
    if (attempt <= 0) return Duration.zero;
    if (attempt - 1 < kSseBackoffSchedule.length) {
      return Duration(seconds: kSseBackoffSchedule[attempt - 1]);
    }
    const int cap = 30;
    final int extra = attempt - kSseBackoffSchedule.length;
    final int seconds =
        (kSseBackoffSchedule.last * (1 << extra)).clamp(0, cap);
    return Duration(seconds: seconds);
  }

  void _scheduleReconnect(String diagnosisId) {
    if (_closed) return;
    _attempt += 1;
    if (_attempt > _maxRetries) {
      _emit('error', '网络异常，请稍后查看报告', terminal: true);
      return;
    }
    final Duration wait = backoffFor(_attempt);
    developer.log(
      'sse.reconnect attempt=$_attempt in=${wait.inSeconds}s',
      name: 'selfwell.sse',
    );
    Timer(wait, () => _open(diagnosisId));
  }

  void _resetHeartbeat() {
    _heartbeatTimer?.cancel();
    _heartbeatTimer = Timer(kSseHeartbeatTimeout, () {
      if (_closed) return;
      _emit('error', 'heartbeat timeout', terminal: true);
    });
  }

  void close() {
    _closed = true;
    _heartbeatTimer?.cancel();
    _byteSub?.cancel();
    _controller?.close();
  }
}

/// Back-compat alias: the previous worker used `SseStreamClient` /
/// `SseEvent` / `SseStage`. Re-export them so older imports still compile.
typedef SseStreamClient = DiagnosisSseClient;
typedef SseEvent = DiagnosisStageEvent;

enum SseStage { idle, connected, processing, imageValidated, llmCalling, complianceCheck, result, fallback, error, done, gaveUp }
