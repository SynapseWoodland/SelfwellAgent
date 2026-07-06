/// IA-REF: docs/design/ia-and-wireframe.md §4.3 P03a-s2 三步卡 第二步·分析中
/// 设计稿: docs/design/figma-pixso-spec/pages/05-butler-analyze-loading.html
/// 后端端点: openapi.yaml tag=[diagnosis] operationId=streamDiagnosis
///                       GET  /diagnosis/{id}/stream  (SSE 8 阶段)
///
/// SSE reconnect (§17 #16): 1s → 2s → 4s → 8s → 16s 上限 30s,
/// 5 次失败后展示 "网络异常，请稍后查看报告"。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/sse_client.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/sse_progress.dart';

class DiagnosisLoadingPage extends ConsumerStatefulWidget {
  const DiagnosisLoadingPage({super.key, required this.diagnosisId});
  final String diagnosisId;

  @override
  ConsumerState<DiagnosisLoadingPage> createState() =>
      _DiagnosisLoadingPageState();
}

class _DiagnosisLoadingPageState
    extends ConsumerState<DiagnosisLoadingPage> {
  int _stage = 0;
  String _label = '正在建立连接…';
  bool _error = false;

  static const int _totalStages = 8;

  @override
  void initState() {
    super.initState();
    _consume();
  }

  Future<void> _consume() async {
    final DiagnosisSseClient client = DiagnosisSseClient();
    await for (final DiagnosisStageEvent ev
        in client.connect(widget.diagnosisId)) {
      if (!mounted) return;
      setState(() {
        _stage = (_stage + 1).clamp(1, _totalStages);
        _label = ev.label;
        _error = ev.stage == 'error' && ev.label.contains('网络');
      });
      if (ev.isTerminal) {
        if (ev.stage == 'result' || ev.stage == 'fallback') {
          if (!mounted) return;
          context.go('/diagnosis/report', extra: widget.diagnosisId);
        } else if (_error) {
          // Stay on page with error banner; user can hit "back".
        }
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('分析中'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.s6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const _AiBubble(),
              const SizedBox(height: AppSpacing.s6),
              SseProgress(
                current: _stage,
                total: _totalStages,
                label: _label,
              ),
              if (_error) ...<Widget>[
                const SizedBox(height: AppSpacing.s6),
                const _ErrorBanner(),
              ],
              const Spacer(),
              const Center(
                child: Text(
                  '你的照片我看完了，正在整理适合你的养护参考。',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    fontSize: 14,
                    color: AppColors.neutral500,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AiBubble extends StatelessWidget {
  const _AiBubble();
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(AppRadius.lg),
          topRight: Radius.circular(AppRadius.lg),
          bottomRight: Radius.circular(AppRadius.lg),
          bottomLeft: Radius.circular(4),
        ),
        border: Border.all(color: AppColors.neutral100),
      ),
      child: const Row(
        children: <Widget>[
          Icon(Icons.chat_bubble_outline, color: AppColors.primaryMint),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              '正在整合照片信息，整理适合你的养护参考。',
              style: TextStyle(fontSize: 14, color: AppColors.neutral700),
            ),
          ),
        ],
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner();
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s3),
      decoration: BoxDecoration(
        color: AppColors.bgCardWarm,
        borderRadius: AppRadius.rMd,
      ),
      child: const Row(
        children: <Widget>[
          Icon(Icons.info_outline, color: AppColors.neutral700),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              '网络异常，请稍后查看报告。',
              style: TextStyle(fontSize: 14, color: AppColors.neutral900),
            ),
          ),
        ],
      ),
    );
  }
}
