/// IA-REF: docs/design/ia-and-wireframe.md §4.6 P06 我的
/// 设计稿: docs/design/figma-pixso-spec/pages/11-profile.html
/// 后端端点:
///   - openapi.yaml tag=[users] operationId=getCurrentUser   GET  /users/me
///   - openapi.yaml tag=[users] operationId=updatePushToken POST /users/push-token
///
/// Token: color/primary/skyblue=#B8D4E3, color/neutral/100=#E2E8F0,
///        radius/lg=16, radius/xl=24
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'package:flutter/material.dart';

import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/progress_ring.dart';

/// Profile (P11). Skeleton for SF0; SF1 wires `getCurrentUser` +
/// `updatePushToken`. The 80px ring matches `ia-and-wireframe.md` §2.5
/// 「进度环-80」用于「我的」页面。
class ProfilePage extends StatelessWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(title: const Text('我的')),
      body: ListView(
        padding: const EdgeInsets.all(AppSpacing.s4),
        children: <Widget>[
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppSpacing.s4),
              child: Row(
                children: <Widget>[
                  const ProgressRing(
                    size: 80,
                    progress: 0.5,
                    strokeWidth: 8,
                    centerLabel: '11',
                  ),
                  const SizedBox(width: AppSpacing.s4),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: const <Widget>[
                        Text('已完成 11 天',
                            style: TextStyle(
                                fontSize: 17,
                                fontWeight: FontWeight.w500)),
                        SizedBox(height: AppSpacing.s1),
                        Text('继续为自己，慢慢走',
                            style: TextStyle(color: AppColors.neutral500)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.s4),
          _ProfileTile(icon: Icons.photo_album_outlined, label: '抱抱卡入口'),
          _ProfileTile(icon: Icons.image_outlined, label: '时光相册入口'),
          const Divider(),
          _ProfileTile(icon: Icons.person_outline, label: '用户档案'),
          _ProfileTile(icon: Icons.notifications_outlined, label: '通知设置'),
          _ProfileTile(icon: Icons.info_outline, label: '关于'),
          _ProfileTile(icon: Icons.lock_outline, label: '隐私'),
          _ProfileTile(icon: Icons.support_agent_outlined, label: '联系客服'),
        ],
      ),
    );
  }
}

class _ProfileTile extends StatelessWidget {
  const _ProfileTile({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(icon, color: AppColors.primaryMint),
      title: Text(label),
      trailing: const Icon(Icons.chevron_right, color: AppColors.neutral300),
    );
  }
}