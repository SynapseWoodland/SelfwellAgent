/// IA-REF: docs/design/ia-and-wireframe.md §4.7 P02b 今日完成页（打卡完成态）
/// 设计稿: docs/design/figma-pixso-spec/pages/08-checkin.html
/// 后端端点:
///   - openapi.yaml tag=[checkins] operationId=createCheckin POST /checkins
///   - openapi.yaml tag=[checkins] operationId=getCheckinStats GET /checkins/stats
///
/// Token: color/primary/mint=#A8C5B5, color/primary/cream=#F5E6D3,
///        color/primary/lavender=#D4C5E2, color/primary/peach=#F0D9C4,
///        color/neutral/900=#2D3436, color/neutral/700=#4A5568,
///        color/neutral/500=#718096, color/neutral/300=#A0AEC0,
///        color/neutral/100=#E2E8F0, radius/lg=16
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
///
/// §17 #15: ACK is strictly ≤ 30 chars. The "舒服" / "放松" / "有点累" / "坚持下来了"
/// tag set comes from `ack-pool.yaml` and is rendered through AckBubble.
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/api/exceptions.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/ack_bubble.dart';
import '../../widgets/error_toast.dart';

/// P02b · 今日完成页。Lets the user select a feeling tag + free-text note
/// and submit `POST /checkins`. On success returns to home with an
/// updated progress ring.
class CheckinPage extends ConsumerStatefulWidget {
  const CheckinPage({super.key});

  @override
  ConsumerState<CheckinPage> createState() => _CheckinPageState();
}

class _CheckinPageState extends ConsumerState<CheckinPage> {
  static const List<String> _feelingTags = <String>[
    '舒服',
    '放松',
    '有点累',
    '坚持下来了',
  ];
  final Set<String> _selectedTags = <String>{};
  final TextEditingController _noteController = TextEditingController();
  bool _busy = false;
  bool _submitted = false;
  int? _resultDay;
  int? _resultStreak;

  @override
  void dispose() {
    _noteController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final ApiService api = ref.read(apiServiceProvider);
      // SF1: plan id is mocked; SF2 will fetch the real active plan.
      await api.createCheckin(CreateCheckinRequest(
        planId: 'plan_active_v1',
        day: 1,
        feeling: _noteController.text,
      ));
      final CheckinStats stats = await api.getCheckinStats();
      if (!mounted) return;
      setState(() {
        _submitted = true;
        _resultDay = 1;
        _resultStreak = stats.streakDays;
      });
    } on ApiException catch (e) {
      if (!mounted) return;
      ErrorToast.show(context, e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(title: const Text('今天练完了')),
      body: SafeArea(
        child: _submitted
            ? _SuccessBody(
                day: _resultDay ?? 1,
                streak: _resultStreak ?? 1,
                onBackHome: () => context.go('/home'),
              )
            : _EditBody(
                busy: _busy,
                feelingTags: _feelingTags,
                selectedTags: _selectedTags,
                onTagToggle: (String t) => setState(() {
                  if (_selectedTags.contains(t)) {
                    _selectedTags.remove(t);
                  } else {
                    _selectedTags.add(t);
                  }
                }),
                noteController: _noteController,
                onSubmit: _submit,
              ),
      ),
    );
  }
}

class _EditBody extends StatelessWidget {
  const _EditBody({
    required this.busy,
    required this.feelingTags,
    required this.selectedTags,
    required this.onTagToggle,
    required this.noteController,
    required this.onSubmit,
  });

  final bool busy;
  final List<String> feelingTags;
  final Set<String> selectedTags;
  final void Function(String) onTagToggle;
  final TextEditingController noteController;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.s4),
      children: <Widget>[
        const Text(
          '今天练完感觉如何？（可选）',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w500,
            color: AppColors.neutral900,
          ),
        ),
        const SizedBox(height: AppSpacing.s3),
        Wrap(
          spacing: AppSpacing.s2,
          runSpacing: AppSpacing.s2,
          children: feelingTags
              .map(
                (String t) => FilterChip(
                  label: Text(t),
                  selected: selectedTags.contains(t),
                  onSelected: (_) => onTagToggle(t),
                  selectedColor: AppColors.primaryMint,
                  backgroundColor: AppColors.bgCard,
                  side: const BorderSide(color: AppColors.neutral100),
                  labelStyle: TextStyle(
                    color: selectedTags.contains(t)
                        ? Colors.white
                        : AppColors.neutral700,
                  ),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: AppSpacing.s4),
        TextField(
          controller: noteController,
          maxLines: 4,
          maxLength: 200,
          decoration: const InputDecoration(
            hintText: '想写点什么吗？',
          ),
        ),
        const SizedBox(height: AppSpacing.s4),
        ElevatedButton(
          onPressed: busy ? null : onSubmit,
          child: busy
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                  ),
                )
              : const Text('明天见'),
        ),
      ],
    );
  }
}

class _SuccessBody extends StatelessWidget {
  const _SuccessBody({
    required this.day,
    required this.streak,
    required this.onBackHome,
  });
  final int day;
  final int streak;
  final VoidCallback onBackHome;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: <Widget>[
          const SizedBox(height: AppSpacing.s8),
          const Center(child: Icon(Icons.check_circle, size: 88, color: AppColors.primaryMint)),
          const SizedBox(height: AppSpacing.s3),
          const Text(
            '今天练完了',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 24,
              fontWeight: FontWeight.w600,
              color: AppColors.neutral900,
            ),
          ),
          const Text(
            '真的很棒。我们明天见。',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppColors.neutral700),
          ),
          const SizedBox(height: AppSpacing.s6),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.s4),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: <Widget>[
                  _StatCell(label: '今日练习', value: '18 分钟'),
                  const _VDivider(),
                  _StatCell(label: '获得碎片', value: '+1'),
                  const _VDivider(),
                  _StatCell(label: '连续', value: '$streak 天'),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.s4),
          const AckBubble(text: '今天又迈出了一步，真的很棒。'),
          const Spacer(),
          Row(
            children: <Widget>[
              Expanded(
                child: OutlinedButton(
                  onPressed: onBackHome,
                  child: const Text('回到首页'),
                ),
              ),
              const SizedBox(width: AppSpacing.s3),
              Expanded(
                flex: 2,
                child: ElevatedButton(
                  onPressed: onBackHome,
                  child: const Text('明天见'),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatCell extends StatelessWidget {
  const _StatCell({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: <Widget>[
        Text(
          value,
          style: const TextStyle(
            fontSize: 20,
            fontWeight: FontWeight.w600,
            color: AppColors.neutral900,
          ),
        ),
        Text(label, style: const TextStyle(color: AppColors.neutral500, fontSize: 12)),
      ],
    );
  }
}

class _VDivider extends StatelessWidget {
  const _VDivider();
  @override
  Widget build(BuildContext context) {
    return Container(width: 1, height: 40, color: AppColors.neutral100);
  }
}
