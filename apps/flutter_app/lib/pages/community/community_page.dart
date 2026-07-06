/// IA-REF: docs/design/ia-and-wireframe.md §4.5 P05 蜕变广场
/// 设计稿: docs/design/figma-pixso-spec/pages/09-plaza.html
/// 后端端点:
///   - openapi.yaml tag=[community] operationId=listPosts  GET  /community/posts
///   - openapi.yaml tag=[community] operationId=createPost POST /community/posts
///
/// V1.3 IA rules:
///   - 字数 ≤ 200
///   - 图片 ≤ 9
///   - 审核: AI 拦截 + 人工 1-4h, 失败展示 "换个表达试试"
///   - 文案禁止颜值打分 / 拉踩 / 医美
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../login/login_page.dart' show apiServiceProvider;

class CommunityPage extends ConsumerStatefulWidget {
  const CommunityPage({super.key});

  @override
  ConsumerState<CommunityPage> createState() => _CommunityPageState();
}

class _CommunityPageState extends ConsumerState<CommunityPage> {
  Future<List<CommunityPost>>? _future;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    setState(() {
      _future = ref.read(apiServiceProvider).listPosts(filter: _filter);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(title: const Text('蜕变广场')),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            _FilterBar(
              current: _filter,
              onChange: (String v) {
                _filter = v;
                _load();
              },
            ),
            Expanded(
              child: FutureBuilder<List<CommunityPost>>(
                future: _future,
                builder: (BuildContext context,
                    AsyncSnapshot<List<CommunityPost>> snap) {
                  if (snap.connectionState != ConnectionState.done) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  final List<CommunityPost> items = snap.data ?? <CommunityPost>[];
                  if (items.isEmpty) {
                    return const _Empty();
                  }
                  return ListView.builder(
                    padding: const EdgeInsets.all(AppSpacing.s3),
                    itemCount: items.length,
                    itemBuilder: (BuildContext context, int i) =>
                        _PostCard(post: items[i]),
                  );
                },
              ),
            ),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.primaryMint,
        onPressed: () => _openEditor(context),
        child: const Icon(Icons.add, color: Colors.white),
      ),
    );
  }

  Future<void> _openEditor(BuildContext context) async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (BuildContext ctx) => const _PostEditor(),
    );
  }
}

class _FilterBar extends StatelessWidget {
  const _FilterBar({required this.current, required this.onChange});
  final String current;
  final ValueChanged<String> onChange;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s4),
      child: Row(
        children: <Widget>[
          _Tab(label: '全部', active: current == 'all', onTap: () => onChange('all')),
          const SizedBox(width: 16),
          _Tab(label: '我的', active: current == 'following', onTap: () => onChange('following')),
        ],
      ),
    );
  }
}

class _Tab extends StatelessWidget {
  const _Tab({required this.label, required this.active, required this.onTap});
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: active ? AppColors.primaryMint : Colors.transparent,
              width: 2,
            ),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 14,
            color: active ? AppColors.primaryMint : AppColors.neutral500,
            fontWeight: active ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }
}

class _PostCard extends StatelessWidget {
  const _PostCard({required this.post});
  final CommunityPost post;

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
          Row(
            children: <Widget>[
              const CircleAvatar(
                radius: 20,
                backgroundColor: AppColors.primaryMint,
                child: Icon(Icons.person, color: Colors.white),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      post.nickName,
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.neutral900,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    Text(
                      _formatDate(post.createdAt),
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.neutral500,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            post.body,
            style: const TextStyle(fontSize: 14, color: AppColors.neutral700),
          ),
          if (post.aiComment != null && post.aiComment!.isNotEmpty) ...<Widget>[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(AppSpacing.s3),
              decoration: BoxDecoration(
                color: AppColors.bgPage,
                borderRadius: AppRadius.rMd,
                border: Border.all(color: AppColors.primaryLavender),
              ),
              child: Row(
                children: <Widget>[
                  const Icon(Icons.chat_bubble_outline,
                      size: 16, color: AppColors.neutral500),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      post.aiComment!,
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.neutral500,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  String _formatDate(String iso) {
    final DateTime? dt = DateTime.tryParse(iso);
    if (dt == null) return iso;
    return '${dt.month}/${dt.day}';
  }
}

class _Empty extends StatelessWidget {
  const _Empty();
  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: <Widget>[
          Icon(Icons.forum_outlined, size: 48, color: AppColors.neutral300),
          SizedBox(height: 12),
          Text('还没有动态哦', style: TextStyle(color: AppColors.neutral500)),
        ],
      ),
    );
  }
}

class _PostEditor extends ConsumerStatefulWidget {
  const _PostEditor();

  @override
  ConsumerState<_PostEditor> createState() => _PostEditorState();
}

class _PostEditorState extends ConsumerState<_PostEditor> {
  final TextEditingController _body = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _body.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final String text = _body.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() => _busy = true);
    try {
      await ref
          .read(apiServiceProvider)
          .createPost(CreatePostRequest(body: text));
      if (!mounted) return;
      Navigator.of(context).pop();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('我们换个表达试试？')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
        left: AppSpacing.s4,
        right: AppSpacing.s4,
        top: AppSpacing.s4,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const Text(
            '发布动态',
            style: TextStyle(fontSize: 18, color: AppColors.neutral900),
          ),
          const SizedBox(height: AppSpacing.s3),
          TextField(
            controller: _body,
            maxLines: 6,
            maxLength: 200,
            decoration: const InputDecoration(
              hintText: '在这里记录今天的小美好…',
            ),
          ),
          const SizedBox(height: AppSpacing.s3),
          ElevatedButton(
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: Colors.white,
                    ),
                  )
                : const Text('发布'),
          ),
          const SizedBox(height: AppSpacing.s4),
        ],
      ),
    );
  }
}
