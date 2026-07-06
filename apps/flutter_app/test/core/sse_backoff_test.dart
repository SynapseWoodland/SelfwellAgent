import 'package:flutter_test/flutter_test.dart';
import 'package:selfwell_app/core/api/sse_client.dart';

/// §17 hard-constraint #16:
///   SSE 客户端必须支持断线重连 (1s → 2s → 4s → 8s → 16s 上限 30s,
///   5 次失败后展示 "网络异常，请稍后查看报告").
void main() {
  group('SseClient backoff policy', () {
    test('attempt 1 → 1s', () {
      final DiagnosisSseClient c = DiagnosisSseClient();
      expect(c.backoffFor(1), const Duration(seconds: 1));
    });
    test('attempt 2 → 2s', () {
      final DiagnosisSseClient c = DiagnosisSseClient();
      expect(c.backoffFor(2), const Duration(seconds: 2));
    });
    test('attempt 3 → 4s', () {
      final DiagnosisSseClient c = DiagnosisSseClient();
      expect(c.backoffFor(3), const Duration(seconds: 4));
    });
    test('attempt 4 → 8s', () {
      final DiagnosisSseClient c = DiagnosisSseClient();
      expect(c.backoffFor(4), const Duration(seconds: 8));
    });
    test('attempt 5 → 16s (still under 30s cap)', () {
      final DiagnosisSseClient c = DiagnosisSseClient();
      expect(c.backoffFor(5), const Duration(seconds: 16));
    });
    test('attempt 6 → 30s (cap)', () {
      final DiagnosisSseClient c = DiagnosisSseClient();
      expect(c.backoffFor(6), const Duration(seconds: 30));
    });
    test('attempt 7 → 30s (cap holds)', () {
      final DiagnosisSseClient c = DiagnosisSseClient();
      expect(c.backoffFor(7), const Duration(seconds: 30));
    });
  });
}
