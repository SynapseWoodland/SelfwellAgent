/// IA-REF: docs/design/ia-and-wireframe.md §4.1 P01 启动页（P01b 子页：手机号登录）
/// 设计稿: docs/design/figma-pixso-spec/pages/02-login.html
/// 后端端点: openapi.yaml tag=[auth] operationId=wxMpLogin POST /auth/wx-login
///
/// Token: color/primary/mint=#A8C5B5, color/neutral/700=#4A5568,
///        color/neutral/900=#2D3436, color/neutral/500=#718096,
///        color/neutral/300=#A0AEC0, radius/xl=24
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/exceptions.dart';
import '../../core/auth/auth_repository.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../widgets/error_toast.dart';

// Back-compat re-exports so historical pages that imported `apiServiceProvider`
// from this file keep compiling. The canonical provider now lives in
// `core/api/api_service.dart`.
export '../../core/api/api_service.dart' show apiServiceProvider;

/// Login screen (P01). Wires the [AuthRepository] to the wx-login endpoint.
/// In V1.3 the WeChat OAuth flow is provided by the WeChat SDK; in
/// widget tests we accept an injected code to skip the platform call.
class LoginPage extends ConsumerStatefulWidget {
  const LoginPage({super.key});

  @override
  ConsumerState<LoginPage> createState() => _LoginPageState();
}

class _LoginPageState extends ConsumerState<LoginPage> {
  bool _busy = false;

  /// Wires the WeChat login flow. In a real build the [code] comes from
  /// `Wechat.instance.auth(scope: 'snsapi_userinfo')`; tests pass a stub.
  Future<void> _doWxLogin({String code = 'mock_wx_code_001'}) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final AuthRepository repo = ref.read(authRepositoryProvider);
      await repo.wxLogin(
        code: code,
        nickName: '小满',
        avatarUrl: null,
      );
      if (!mounted) return;
      context.go('/home');
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
                key: const Key('login.wechat'),
                onPressed: _busy ? null : _doWxLogin,
                child: _busy
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          valueColor:
                              AlwaysStoppedAnimation<Color>(Colors.white),
                        ),
                      )
                    : const Text('微信一键登录'),
              ),
              const SizedBox(height: AppSpacing.s3),
              OutlinedButton(
                key: const Key('login.phone'),
                onPressed: _busy ? null : () => _doWxLogin(code: 'mock_phone_001'),
                child: const Text('手机号登录'),
              ),
              const SizedBox(height: AppSpacing.s6),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: const <Widget>[
                  Text('隐私政策', style: TextStyle(color: AppColors.neutral300)),
                  Text('用户协议', style: TextStyle(color: AppColors.neutral300)),
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

// Re-export so historical `import '.../login_page.dart' show apiServiceProvider`
// imports keep compiling. The canonical provider lives in
// `core/api/api_service.dart`.
export '../../core/api/api_service.dart' show apiServiceProvider;
