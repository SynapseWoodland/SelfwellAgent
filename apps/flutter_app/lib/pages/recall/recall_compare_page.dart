/// IA-REF: docs/design/ia-and-wireframe.md §4.10 P09 对比回顾页
/// 设计稿: docs/design/figma-pixso-spec/pages/09-butler-compare.html
/// 后端端点:
///   - openapi.yaml tag=[butler] operationId=triggerRecall POST /butler/recall
///   - openapi.yaml tag=[butler] operationId=getRecallMessages
///                         GET  /butler/recall/{id}/messages
///
/// V1.3 IA rule: "没有比较，只是同一段时间的自己" — do not show numeric
/// deltas, no judgement words (变好/提升).
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../login/login_page.dart' show apiServiceProvider;

class RecallComparePage extends ConsumerStatefulWidget {
  const RecallComparePage({super.key});

  @override
  ConsumerState<RecallComparePage> createState() =>
      _RecallComparePageState();
}

class _RecallComparePageState extends ConsumerState<RecallComparePage> {
  Future<RecallCompare>? _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(apiServiceProvider).triggerRecall(daysAgo: 90);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('问问过去'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: FutureBuilder<RecallCompare>(
          future: _future,
          builder: (BuildContext context, AsyncSnapshot<RecallCompare> snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return _ErrorView(
                onRetry: () => setState(() {
                  _future = ref
                      .read(apiServiceProvider)
                      .triggerRecall(daysAgo: 90);
                }),
              );
            }
            return _CompareBody(compare: snap.data!);
          },
        ),
      ),
    );
  }
}

class _CompareBody extends StatelessWidget {
  const _CompareBody({required this.compare});
  final RecallCompare compare;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.s4),
      children: <Widget>[
        const _UserBubble(text: '三个月前的我气色怎么样？'),
        const SizedBox(height: AppSpacing.s3),
        _AiBubble(text: compare.aiSummary),
        const SizedBox(height: AppSpacing.s4),
        _CompareCard(compare: compare),
        const SizedBox(height: AppSpacing.s4),
        Row(
          children: <Widget>[
            Expanded(
              child: OutlinedButton(
                onPressed: () => context.push('/assistant/home'),
                child: const Text('继续聊聊'),
              ),
            ),
            const SizedBox(width: AppSpacing.s3),
            Expanded(
              child: ElevatedButton(
                onPressed: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('已保存到日记')),
                  );
                  context.pop();
                },
                child: const Text('保存到日记'),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _UserBubble extends StatelessWidget {
  const _UserBubble({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.s3),
        constraints: const BoxConstraints(maxWidth: 260),
        decoration: const BoxDecoration(
          color: AppColors.primaryMint,
          borderRadius: BorderRadius.only(
            topLeft: Radius.circular(AppRadius.lg),
            topRight: Radius.circular(AppRadius.lg),
            bottomLeft: Radius.circular(AppRadius.lg),
            bottomRight: Radius.circular(4),
          ),
        ),
        child: Text(
          text,
          style: const TextStyle(color: Colors.white, fontSize: 15),
        ),
      ),
    );
  }
}

class _AiBubble extends StatelessWidget {
  const _AiBubble({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Container(
        width: double.infinity,
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
        child: Text(
          text,
          style: const TextStyle(fontSize: 15, color: AppColors.neutral900, height: 1.6),
        ),
      ),
    );
  }
}

class _CompareCard extends StatelessWidget {
  const _CompareCard({required this.compare});
  final RecallCompare compare;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: AppRadius.rLg,
        border: Border.all(color: AppColors.neutral100),
      ),
      child: Column(
        children: <Widget>[
          const Text(
            '4 月 vs 现在',
            style: TextStyle(fontSize: 17, color: AppColors.neutral900),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: <Widget>[
              _Snapshot(photoUrl: compare.before.photoUrl, label: '4 月'),
              _Snapshot(photoUrl: compare.now.photoUrl, label: '现在'),
            ],
          ),
          const SizedBox(height: 16),
          const Text(
            '没有比较，只是同一段时间的自己。',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 12, color: AppColors.neutral500),
          ),
        ],
      ),
    );
  }
}

class _Snapshot extends StatelessWidget {
  const _Snapshot({this.photoUrl, required this.label});
  final String? photoUrl;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Container(
          width: 100,
          height: 100,
          decoration: BoxDecoration(
            color: AppColors.bgPage,
            borderRadius: AppRadius.rMd,
          ),
          child: photoUrl == null
              ? const Icon(Icons.image_outlined, color: AppColors.neutral300)
              : null,
        ),
        const SizedBox(height: 6),
        Text(label, style: const TextStyle(fontSize: 12, color: AppColors.neutral500)),
      ],
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.onRetry});
  final VoidCallback onRetry;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.s6),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          const Icon(Icons.error_outline, size: 48, color: AppColors.neutral500),
          const SizedBox(height: 12),
          const Text('加载失败'),
          const SizedBox(height: 16),
          OutlinedButton(onPressed: onRetry, child: const Text('重试')),
        ],
      ),
    );
  }
}
