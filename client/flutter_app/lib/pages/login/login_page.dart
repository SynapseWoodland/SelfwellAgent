/// IA-REF: docs/design/ia-and-wireframe.md §4.1 P01 启动页
/// 设计稿: docs/design/figma-pixso-spec/pages/02-login.html
/// 后端端点: openapi.yaml tag=[auth] operationId=wxMpLogin POST /auth/wx-login
///
/// Token: color/primary/mint=#A8C5B5, color/neutral/700=#4A5568,
///        color/neutral/900=#2D3436, color/neutral/500=#718096,
///        color/neutral/300=#A0AEC0, radius/xl=24
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'package:flutter/material.dart';

import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';

/// Login screen (P01). The actual `wx.login` → POST /auth/wx-login flow
/// lands in Sprint SF1; this SF0 placeholder renders the design surface.
class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s6),
          child: Column(
            children: <Widget>[
              const Spacer(),
              const Text(
                'Selfwell',
                style: TextStyle(
                  fontSize: 22,
                  color: AppColors.neutral700,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const SizedBox(height: AppSpacing.s12),
              const Text(
                '慢慢自律，慢慢健康',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.w600,
                  color: AppColors.neutral900,
                ),
              ),
              const SizedBox(height: AppSpacing.s2),
              const Text(
                '慢慢成为更好的自己',
                style: TextStyle(
                  fontSize: 22,
                  color: AppColors.neutral500,
                ),
              ),
              const Spacer(),
              ElevatedButton(
                onPressed: null, // wired in SF1
                child: const Text('微信一键登录'),
              ),
              const SizedBox(height: AppSpacing.s3),
              OutlinedButton(
                onPressed: null,
                child: const Text('手机号登录'),
              ),
              const SizedBox(height: AppSpacing.s6),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: const <Widget>[
                  Text('隐私政策',
                      style: TextStyle(color: AppColors.neutral300)),
                  Text('用户协议',
                      style: TextStyle(color: AppColors.neutral300)),
                ],
              ),
              const SizedBox(height: AppSpacing.s6),
            ],
          ),
        ),
      ),
    );
  }
}