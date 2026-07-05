/// 4-level error severity model used by [ApiException].
///
/// Mirrors the backend's `ErrorSeverity` enum
/// (`docs/spec/facts-anchor.md` §4.3) so the Flutter client can drive
/// toast/modal/dismiss UX from a single field.
///
/// Mapping rules (see `error_toast.dart` widget for visuals):
/// - [permanent]   → modal (e.g. E_GENERAL_FORBIDDEN / E_COMPLIANCE_USER_BLOCKED)
/// - [transient]   → orange toast + retry (e.g. E_*_RATE_LIMIT / 502/503)
/// - [userError]   → yellow toast (e.g. E_*_INVALID_INPUT, 400/401/404/409/413)
/// - [degraded]    → grey non-blocking banner (e.g. 200 soft-tip)
enum ErrorSeverity { permanent, transient, userError, degraded }

/// Thin exception surface carrying the backend `error.code` (E_*_*) +
/// the localized message + computed severity.
class ApiException implements Exception {
  ApiException({
    required this.code,
    required this.message,
    this.messageEn,
    this.httpStatus,
    this.severity = ErrorSeverity.userError,
    this.cause,
  });

  /// Backend error code, e.g. `E_USER_INVALID_INPUT`. See `docs/api/error-codes.md`.
  final String code;

  /// Localized message (zh by default).
  final String message;

  /// Optional English fallback. Flutter may switch locales and re-render.
  final String? messageEn;

  /// HTTP status code from `docs/api/openapi.yaml`.
  final int? httpStatus;

  /// Computed client-side severity. Drives toast vs modal.
  final ErrorSeverity severity;

  /// Underlying Dio/network error, if any.
  final Object? cause;

  /// True if the error is recoverable with a retry (5xx or 429).
  bool get isRetryable => severity == ErrorSeverity.transient;

  @override
  String toString() =>
      'ApiException(code=$code, http=$httpStatus, severity=$severity, msg=$message)';
}

/// Derives a severity from an HTTP status code when backend doesn't ship
/// one. Per `docs/api/error-codes.md` §3 the mapping is stable.
ErrorSeverity severityFromHttp(int? status) {
  if (status == null) return ErrorSeverity.transient;
  if (status >= 500 && status < 600) {
    // 502/503 may be retryable; 500 not. Keep coarse: transient.
    return ErrorSeverity.transient;
  }
  if (status == 429) return ErrorSeverity.transient;
  if (status == 401 || status == 403) return ErrorSeverity.userError;
  if (status == 400 ||
      status == 404 ||
      status == 409 ||
      status == 413) {
    return ErrorSeverity.userError;
  }
  return ErrorSeverity.userError;
}