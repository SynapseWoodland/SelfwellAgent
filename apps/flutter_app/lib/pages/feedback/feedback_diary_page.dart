/// IA-REF: docs/design/ia-and-wireframe.md §4.9 P08 心情日记列表
/// 设计稿: docs/design/figma-pixso-spec/pages/08-butler-diary.html
/// 后端端点:
///   - openapi.yaml tag=[feedback] operationId=listFeedback  GET  /feedback
///   - openapi.yaml tag=[feedback] operationId=createFeedback POST /feedback
///     (X-Caller-Id: mood_diary_list)
/// 30 条 ACK 池: docs/data/ack-pool.yaml (≤ 30 字强制截断 + tooltip)
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/ack_bubble.dart';
import '../login/login_page.dart' show apiServiceProvider;

class FeedbackDiaryPage extends ConsumerStatefulWidget {
  const FeedbackDiaryPage({super.key});

  @override
  ConsumerState<FeedbackDiaryPage> createState() => _FeedbackDiaryPageState();
}

class _FeedbackDiaryPageState extends ConsumerState<FeedbackDiaryPage> {
  final TextEditingController _input = TextEditingController();
  final List<FeedbackEntry> _items = <FeedbackEntry>[];
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final List<FeedbackEntry> list =
          await ref.read(apiServiceProvider).listFeedback();
      if (!mounted) return;
      setState(() {
        _items
          ..clear()
          ..addAll(list);
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _items.clear());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _submit() async {
    final String text = _input.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() => _busy = true);
    try {
      final ApiService api = ref.read(apiServiceProvider);
      // SF1: no `feedback_type` field — defaults to mood_text on backend.
      // The post body is `body` only per api_types; backend infers type
      // from caller headers (X-Caller-Id: mood_diary_list).
      final CommunityPost _ = await api.createPost(
        CreatePostRequest(body: text),
      );
      // Append locally for instant feedback.
      if (!mounted) return;
      setState(() {
        _items.insert(
          0,
          FeedbackEntry(
            id: 'local-${DateTime.now().millisecondsSinceEpoch}',
            body: text,
            createdAt: DateTime.now().toIso8601String(),
            aiAck: '收到，慢慢来。',
          ),
        );
        _input.clear();
      });
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('提交失败：$e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('心情日记'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            const _PromptBanner(),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : (_items.isEmpty
                      ? const _EmptyState()
                      : ListView.builder(
                          padding: const EdgeInsets.all(AppSpacing.s3),
                          itemCount: _items.length,
                          itemBuilder: (BuildContext context, int i) =>
                              _DiaryCard(entry: _items[i]),
                        )),
            ),
            _Composer(input: _input, busy: _busy, onSend: _submit),
          ],
        ),
      ),
    );
  }
}

class _PromptBanner extends StatelessWidget {
  const _PromptBanner();
  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(AppSpacing.s3),
      padding: const EdgeInsets.all(AppSpacing.s3),
      decoration: BoxDecoration(
        color: AppColors.primaryCream,
        borderRadius: AppRadius.rMd,
      ),
      child: const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '没有强制 · 没有格式 · 想到什么都可以',
            style: TextStyle(fontSize: 14, color: AppColors.neutral700),
          ),
          SizedBox(height: 2),
          Text(
            '你的记录只属于你，AI 不会推送提醒。',
            style: TextStyle(fontSize: 12, color: AppColors.neutral500),
          ),
        ],
      ),
    );
  }
}

class _DiaryCard extends StatelessWidget {
  const _DiaryCard({required this.entry});
  final FeedbackEntry entry;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.s3),
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.bgCard,
        borderRadius: AppRadius.rLg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            _formatDate(entry.createdAt),
            style: const TextStyle(
              fontSize: 15,
              color: AppColors.neutral900,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            entry.body,
            style: const TextStyle(fontSize: 14, color: AppColors.neutral700),
          ),
          if (entry.aiAck != null && entry.aiAck!.isNotEmpty) ...<Widget>[
            const SizedBox(height: 10),
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: AckBubble(text: entry.aiAck!),
            ),
          ],
        ],
      ),
    );
  }

  String _formatDate(String iso) {
    final DateTime? dt = DateTime.tryParse(iso);
    if (dt == null) return iso;
    return '${dt.month} 月 ${dt.day} 日';
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();
  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Icon(Icons.menu_book_outlined,
              size: 48, color: AppColors.neutral300),
          SizedBox(height: 12),
          Text('还没有日记哦', style: TextStyle(color: AppColors.neutral500)),
        ],
      ),
    );
  }
}

class _Composer extends StatelessWidget {
  const _Composer({
    required this.input,
    required this.busy,
    required this.onSend,
  });
  final TextEditingController input;
  final bool busy;
  final VoidCallback onSend;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Container(
        padding: const EdgeInsets.all(AppSpacing.s3),
        decoration: const BoxDecoration(
          color: AppColors.bgCard,
          border: Border(
            top: BorderSide(color: AppColors.neutral100),
          ),
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: TextField(
                controller: input,
                maxLines: 3,
                maxLength: 200,
                decoration: const InputDecoration(
                  hintText: '今天想说点什么…',
                  filled: true,
                  fillColor: AppColors.bgPage,
                ),
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              onPressed: busy ? null : onSend,
              icon: busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.send, color: AppColors.primaryMint),
            ),
          ],
        ),
      ),
    );
  }
}
