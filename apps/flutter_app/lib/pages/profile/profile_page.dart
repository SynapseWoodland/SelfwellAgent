/// IA-REF: docs/design/ia-and-wireframe.md §4.6 P06 我的
/// 设计稿: docs/design/figma-pixso-spec/pages/11-profile.html
/// 后端端点:
///   - openapi.yaml tag=[users] operationId=getCurrentUser     GET  /users/me
///   - openapi.yaml tag=[users] operationId=updatePushToken   POST /users/me/push-token
///   - openapi.yaml tag=[checkins] operationId=getCheckinStats GET /checkins/stats
///   - openapi.yaml tag=[share]  operationId=generateSharePoster POST /share/poster
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/api/dio_client.dart';
import '../../core/storage/secure_storage.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/progress_ring.dart';
import '../home/home_page.dart' show HomeSnapshot, homeSnapshotProvider, logout;
import '../login/login_page.dart' show apiServiceProvider;
import '../splash/splash_page.dart' show secureStorageProvider;

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final AsyncValue<HomeSnapshot> snap = ref.watch(homeSnapshotProvider);
    final UserProfile? user = snap.value?.user;
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('我的'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: snap.when(
          data: (HomeSnapshot s) => _ProfileBody(snapshot: s, user: user),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (Object e, _) => const Center(child: Text('加载失败')),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        backgroundColor: AppColors.bgCard,
        selectedIndex: 3,
        onDestinationSelected: (int i) {
          switch (i) {
            case 0:
              context.go('/home');
              break;
            case 1:
              context.go('/assistant/home');
              break;
            case 2:
              context.go('/community');
              break;
            case 3:
              break;
          }
        },
        destinations: const <NavigationDestination>[
          NavigationDestination(
            icon: Icon(Icons.home_outlined),
            selectedIcon: Icon(Icons.home, color: AppColors.primaryMint),
            label: '首页',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat_bubble_outline),
            selectedIcon: Icon(Icons.chat_bubble, color: AppColors.primaryMint),
            label: '智能管家',
          ),
          NavigationDestination(
            icon: Icon(Icons.forum_outlined),
            selectedIcon: Icon(Icons.forum, color: AppColors.primaryMint),
            label: '广场',
          ),
          NavigationDestination(
            icon: Icon(Icons.person),
            selectedIcon: Icon(Icons.person, color: AppColors.primaryMint),
            label: '我的',
          ),
        ],
      ),
    );
  }
}

class _ProfileBody extends ConsumerWidget {
  const _ProfileBody({required this.snapshot, required this.user});
  final HomeSnapshot snapshot;
  final UserProfile? user;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final int streak = snapshot.stats.streakDays;
    final int total = snapshot.plan?.totalDays ?? 21;
    return ListView(
      padding: const EdgeInsets.all(AppSpacing.s4),
      children: <Widget>[
        const SizedBox(height: 16),
        Center(
          child: Column(
            children: <Widget>[
              const CircleAvatar(
                radius: 32,
                backgroundColor: AppColors.primaryMint,
                child: Icon(Icons.person, color: Colors.white, size: 32),
              ),
              const SizedBox(height: 12),
              Text(
                user?.nickName ?? '你',
                style: const TextStyle(fontSize: 18, color: AppColors.neutral900),
              ),
              const SizedBox(height: 4),
              Text(
                '已完成 ${snapshot.stats.totalDays} 天',
                style: const TextStyle(fontSize: 14, color: AppColors.neutral500),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.s6),
        Container(
          padding: const EdgeInsets.all(AppSpacing.s4),
          decoration: BoxDecoration(
            color: AppColors.primaryCream,
            borderRadius: AppRadius.rLg,
          ),
          child: Row(
            children: <Widget>[
              ProgressRing(
                size: 80,
                strokeWidth: 6,
                progress: total > 0 ? streak / total : 0,
                centerLabel: '$streak',
                centerSubLabel: '/ $total 天',
              ),
              const SizedBox(width: AppSpacing.s4),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: <Widget>[
                    Text(
                      '连续打卡 $streak 天',
                      style: const TextStyle(
                        fontSize: 14,
                        color: AppColors.neutral700,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '碎片 ${snapshot.stats.fragments}',
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
        ),
        const SizedBox(height: AppSpacing.s4),
        Container(
          padding: const EdgeInsets.all(AppSpacing.s4),
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: AppRadius.rLg,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              const Text(
                '抱抱卡 (2/3)',
                style: TextStyle(fontSize: 16, color: AppColors.neutral900),
              ),
              const SizedBox(height: 8),
              Row(
                children: <Widget>[
                  _NodeChip(label: '第 7 天', active: true),
                  const SizedBox(width: 8),
                  _NodeChip(label: '第 14 天', active: true),
                  const SizedBox(width: 8),
                  _NodeChip(label: '第 21 天', active: false),
                ],
              ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => context.push(
                  '/share/hug-card?day=14',
                ),
                child: const Text('生成海报'),
              ),
            ],
          ),
        ),
        const SizedBox(height: AppSpacing.s4),
        Container(
          decoration: BoxDecoration(
            color: AppColors.bgCard,
            borderRadius: AppRadius.rLg,
          ),
          child: Column(
            children: <Widget>[
              _MenuRow(
                label: '用户档案',
                onTap: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('用户档案 - 占位')),
                  );
                },
              ),
              const Divider(color: AppColors.neutral100, height: 1),
              _MenuRow(
                label: '通知设置',
                onTap: () => _openPushSettings(context, ref),
              ),
              const Divider(color: AppColors.neutral100, height: 1),
              _MenuRow(
                label: '关于自愈',
                onTap: () {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(content: Text('关于自愈 - 占位')),
                  );
                },
              ),
              const Divider(color: AppColors.neutral100, height: 1),
              _MenuRow(
                label: '退出登录',
                onTap: () async {
                  await logout(ref);
                  if (!context.mounted) return;
                  context.go('/login');
                },
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _openPushSettings(BuildContext context, WidgetRef ref) async {
    final String? pseudo = await ref.read(secureStorageProvider).readUserIdPseudo();
    if (!context.mounted) return;
    await showDialog<void>(
      context: context,
      builder: (BuildContext ctx) => _PushDialog(pseudo: pseudo ?? 'unknown'),
    );
  }
}

class _NodeChip extends StatelessWidget {
  const _NodeChip({required this.label, required this.active});
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: active ? AppColors.primaryMint : AppColors.neutral100,
        borderRadius: AppRadius.rSm,
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 12,
          color: active ? Colors.white : AppColors.neutral500,
        ),
      ),
    );
  }
}

class _MenuRow extends StatelessWidget {
  const _MenuRow({required this.label, required this.onTap});
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.s4,
          vertical: AppSpacing.s4,
        ),
        child: Row(
          children: <Widget>[
            Expanded(
              child: Text(
                label,
                style: const TextStyle(fontSize: 14, color: AppColors.neutral900),
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.neutral500),
          ],
        ),
      ),
    );
  }
}

class _PushDialog extends ConsumerStatefulWidget {
  const _PushDialog({required this.pseudo});
  final String pseudo;

  @override
  ConsumerState<_PushDialog> createState() => _PushDialogState();
}

class _PushDialogState extends ConsumerState<_PushDialog> {
  bool _enabled = false;
  bool _busy = false;

  Future<void> _toggle() async {
    setState(() => _busy = true);
    try {
      final ApiService api = ref.read(apiServiceProvider);
      if (_enabled) {
        await api.subscribePush(templateId: 'daily_checkin_v1');
      } else {
        await api.subscribePush(templateId: 'unsubscribe_all');
      }
      setState(() => _enabled = !_enabled);
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('设置失败：$e')),
      );
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('推送设置'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: <Widget>[
          Text(
            '推送通道：${clientPlatform().toUpperCase()}',
            style: const TextStyle(fontSize: 12, color: AppColors.neutral500),
          ),
          const SizedBox(height: 4),
          Text(
            '用户标识：${widget.pseudo}',
            style: const TextStyle(fontSize: 12, color: AppColors.neutral500),
          ),
          const SizedBox(height: 12),
          SwitchListTile(
            value: _enabled,
            onChanged: _busy ? null : (_) => _toggle(),
            title: const Text('接收打卡提醒'),
          ),
        ],
      ),
      actions: <Widget>[
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('关闭'),
        ),
      ],
    );
  }
}
