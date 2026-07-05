import 'dart:developer' as developer;
import 'dart:math' as math;

import 'package:dio/dio.dart';

import 'exceptions.dart';

/// Header constants — single source of truth.
class ApiHeaders {
  ApiHeaders._();

  /// W3C TraceContext header — see §17 hard-constraint #17.
  static const String traceparent = 'traceparent';

  /// Legacy / alternative request id header.
  static const String requestId = 'X-Request-ID';

  /// Auth header.
  static const String authorization = 'Authorization';
}

/// Resolves the JWT for outgoing requests. Implemented by the storage layer.
typedef TokenProvider = Future<String?> Function();

/// Resolves the trace id for outgoing requests. Used by the trace middleware.
typedef TraceIdProvider = String Function();

class AuthInterceptor extends Interceptor {
  AuthInterceptor({required this.tokenProvider});

  final TokenProvider tokenProvider;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final String? token = await tokenProvider();
    if (token != null && token.isNotEmpty) {
      options.headers[ApiHeaders.authorization] = 'Bearer $token';
    }
    handler.next(options);
  }
}

class TraceparentInterceptor extends Interceptor {
  TraceparentInterceptor({required this.traceIdProvider});

  final TraceIdProvider traceIdProvider;

  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
    final String traceId = traceIdProvider();
    if (traceId.isNotEmpty) {
      options.headers[ApiHeaders.traceparent] = traceId;
      options.headers[ApiHeaders.requestId] = traceId;
    }
    handler.next(options);
  }
}

/// Lightweight structured logger; format mirrors the backend
/// `logger.info("event", k=v)` shape so log aggregation can pivot.
class LogInterceptor extends Interceptor {
  @override
  void onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) {
    developer.log(
      'api.request',
      name: 'selfwell.api',
      error: null,
      stackTrace: null,
    );
    developer.log(
      'method=${options.method} path=${options.path} '
      'traceparent=${options.headers[ApiHeaders.traceparent] ?? ""}',
      name: 'selfwell.api',
    );
    handler.next(options);
  }

  @override
  void onResponse(
    Response<dynamic> response,
    ResponseInterceptorHandler handler,
  ) {
    developer.log(
      'api.response status=${response.statusCode} '
      'path=${response.requestOptions.path}',
      name: 'selfwell.api',
    );
    handler.next(response);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final dynamic data = err.response?.data;
    final String? code = (data is Map)
        ? (data['error'] is Map
            ? (data['error'] as Map)['code'] as String?
            : null)
        : null;
    developer.log(
      'api.error status=${err.response?.statusCode} '
      'code=$code path=${err.requestOptions.path}',
      name: 'selfwell.api',
      error: err,
    );
    handler.next(err);
  }
}

class _Bootstrap {
  static String _traceId() {
    final int ms = DateTime.now().millisecondsSinceEpoch;
    final int rand = math.Random().nextInt(1 << 24);
    return '${ms.toRadixString(16)}-${rand.toRadixString(16).padLeft(6, '0')}';
  }
}

/// Default trace id provider for the app lifetime.
String defaultTraceIdProvider() => _Bootstrap._traceId();

/// Builds the singleton [Dio] used throughout the app.
///
/// Place `dioClient` behind a Riverpod provider in `main.dart` and inject
/// [tokenProvider]. Interceptor order matters:
///   traceparent → auth → log   (auth can read traceparent set above)
Dio buildDio({
  required String baseUrl,
  required TokenProvider tokenProvider,
  TraceIdProvider? traceIdProvider,
  Duration connectTimeout = const Duration(seconds: 8),
  Duration receiveTimeout = const Duration(seconds: 30),
}) {
  final Dio dio = Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: connectTimeout,
      receiveTimeout: receiveTimeout,
      responseType: ResponseType.json,
      headers: <String, dynamic>{
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
    ),
  );

  dio.interceptors.addAll(<Interceptor>[
    TraceparentInterceptor(
      traceIdProvider: traceIdProvider ?? defaultTraceIdProvider,
    ),
    AuthInterceptor(tokenProvider: tokenProvider),
    LogInterceptor(),
  ]);

  return dio;
}

/// Translates a Dio failure into an [ApiException].
///
/// Fallback error codes use the `E_GENERAL_*` family defined in
/// `docs/api/error-codes.md`. They're listed here as constants so a
/// single grep surfaces every hard-coded fallback and so a future linter
/// can refuse any inline `E_*` literals (mirrors §13 backend rule).
class _FallbackCodes {
  _FallbackCodes._();

  static const String network = 'E_GENERAL_NETWORK_ERROR';
  static const String timeout = 'E_GENERAL_TIMEOUT';
  static const String offline = 'E_GENERAL_OFFLINE';
}

ApiException mapDioError(DioException err) {
  final dynamic data = err.response?.data;
  String code = _FallbackCodes.network;
  String message = err.message ?? '网络异常，请稍后重试';
  String? messageEn;
  int? status = err.response?.statusCode;

  if (data is Map && data['error'] is Map) {
    final Map<dynamic, dynamic> error =
        (data['error'] as Map).cast<dynamic, dynamic>();
    code = (error['code'] as String?) ?? code;
    message = (error['message_zh'] as String?) ?? message;
    messageEn = error['message_en'] as String?;
  } else if (err.type == DioExceptionType.connectionTimeout ||
      err.type == DioExceptionType.receiveTimeout ||
      err.type == DioExceptionType.sendTimeout) {
    code = _FallbackCodes.timeout;
    message = '网络连接超时，请稍后重试';
  } else if (err.type == DioExceptionType.connectionError) {
    code = _FallbackCodes.offline;
    message = '当前网络不可用';
  }

  return ApiException(
    code: code,
    message: message,
    messageEn: messageEn,
    httpStatus: status,
    severity: severityFromHttp(status),
    cause: err,
  );
}