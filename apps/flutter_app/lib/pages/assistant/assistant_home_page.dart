/// IA-REF: docs/design/ia-and-wireframe.md §4.3 P03a 智能管家对话主页
/// 设计稿: docs/design/figma-pixso-spec/pages/07-butler-home.html
/// 后端端点:
///   - openapi.yaml tag=[assistant] operationId=assistantChat POST /assistant/chat
///   - openapi.yaml tag=[assistant] operationId=getEntryCards GET  /assistant/entry-cards
///
/// M5 spec rules (4-state FSM, 永不合规违规):
///   - warm: 完成反馈 / 正常对话
///   - neutral: 闲聊 / 不知道说什么
///   - slight_hug: 表达疲惫 / 失败
///   - medical_guarded: 触发医疗关键词 → 自动回复 + 标记
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/persona_bubble.dart';
import '../home/home_page.dart' show homeSnapshotProvider;
import '../login/login_page.dart' show apiServiceProvider;

class AssistantHomePage extends ConsumerStatefulWidget {
  const AssistantHomePage({super.key});

  @override
  ConsumerState<AssistantHomePage> createState() =>
      _AssistantHomePageState();
}

class _AssistantHomePageState extends ConsumerState<AssistantHomePage> {
  final List<AssistantMessage> _messages = <AssistantMessage>[
    const AssistantMessage(
      role: 'assistant',
      content: '我是 Selfwell。今天想做什么？',
      personaState: 'warm',
    ),
  ];
  final TextEditingController _input = TextEditingController();
  String _sessionId = 'sf1-dev-session';
  bool _busy = false;

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final String text = _input.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _messages.add(AssistantMessage(
        role: 'user',
        content: text,
        personaState: 'warm',
      ));
      _input.clear();
      _busy = true;
    });
    try {
      final AssistantChatResponse r =
          await ref.read(apiServiceProvider).assistantChat(_sessionId, text);
      _sessionId = r.sessionId;
      if (!mounted) return;
      setState(() {
        _messages.add(AssistantMessage(
          role: 'assistant',
          content: r.reply,
          personaState: r.personaState,
        ));
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _messages.add(AssistantMessage(
          role: 'assistant',
          content: '我在这里，稍等一下～',
          personaState: 'neutral',
        ));
      });
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('智能管家'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: Column(
          children: <Widget>[
            const _EntryCards(),
            const Divider(color: AppColors.neutral100, height: 1),
            Expanded(
              child: ListView.builder(
                reverse: false,
                padding: const EdgeInsets.all(AppSpacing.s4),
                itemCount: _messages.length,
                itemBuilder: (BuildContext context, int i) {
                  final AssistantMessage m = _messages[i];
                  return _MessageRow(message: m);
                },
              ),
            ),
            _Composer(input: _input, busy: _busy, onSend: _send),
          ],
        ),
      ),
    );
  }
}

class _EntryCards extends StatelessWidget {
  const _EntryCards();
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.s3),
      child: Column(
        children: <Widget>[
          _EntryCard(
            title: '智能分析',
            subtitle: '上传 3 张照片，生成你的养护参考。',
            icon: Icons.search,
            color: AppColors.bgCard,
            onTap: () => context.push('/diagnosis/upload'),
          ),
          const SizedBox(height: 8),
          _EntryCard(
            title: '心情日记',
            subtitle: '想记录今天的感受吗？',
            icon: Icons.menu_book_outlined,
            color: AppColors.primaryCream,
            onTap: () => context.push('/feedback/diary'),
          ),
          const SizedBox(height: 8),
          _EntryCard(
            title: '问过去的自己',
            subtitle: '好奇几个月前的你吗？',
            icon: Icons.chat_bubble_outline,
            color: AppColors.bgCard,
            onTap: () => context.push('/recall/compare'),
          ),
        ],
      ),
    );
  }
}

class _EntryCard extends StatelessWidget {
  const _EntryCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.color,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: AppRadius.rLg,
      onTap: onTap,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpacing.s4),
        decoration: BoxDecoration(
          color: color,
          borderRadius: AppRadius.rLg,
        ),
        child: Row(
          children: <Widget>[
            Icon(icon, color: AppColors.primaryMint),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 16,
                      color: AppColors.neutral900,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: const TextStyle(
                      fontSize: 12,
                      color: AppColors.neutral700,
                    ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.neutral500),
          ],
        ),
      ),
    );
  }
}

class _MessageRow extends StatelessWidget {
  const _MessageRow({required this.message});
  final AssistantMessage message;

  @override
  Widget build(BuildContext context) {
    final bool isUser = message.role == 'user';
    final PersonaState state = _stateFromString(message.personaState);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment:
            isUser ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          if (!isUser) ...<Widget>[
            PersonaBubble(state: state),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.all(AppSpacing.s3),
              decoration: BoxDecoration(
                color: isUser ? AppColors.primaryMint : AppColors.bgCard,
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(AppRadius.lg),
                  topRight: const Radius.circular(AppRadius.lg),
                  bottomLeft: Radius.circular(isUser ? AppRadius.lg : 4),
                  bottomRight: Radius.circular(isUser ? 4 : AppRadius.lg),
                ),
              ),
              child: Text(
                message.content,
                style: TextStyle(
                  fontSize: 14,
                  color: isUser ? Colors.white : AppColors.neutral900,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  PersonaState _stateFromString(String s) {
    switch (s) {
      case 'warm':
        return PersonaState.warm;
      case 'neutral':
        return PersonaState.neutral;
      case 'slight_hug':
        return PersonaState.slightHug;
      case 'medical_guarded':
        return PersonaState.medicalGuarded;
      default:
        return PersonaState.warm;
    }
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
                decoration: const InputDecoration(
                  hintText: '想说什么都可以…',
                  border: OutlineInputBorder(borderSide: BorderSide.none),
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
