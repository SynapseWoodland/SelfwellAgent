/// IA-REF: docs/design/ia-and-wireframe.md §1.2 启动流程
/// 设计稿: docs/design/figma-pixso-spec/pages/01-splash.html
/// 后端端点: — （本 Sprint 本地生成 device_id，无后端调用；M1 登录后端点 wxMpLogin 见 login_page.dart）
///
/// Token: color/primary/mint=#A8C5B5, color/primary/cream=#F5E6D3
///        color/neutral/900=#2D3436, color/neutral/500=#718096
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/storage/secure_storage.dart';

/// Riverpod entry point for the storage singleton. Kept here so splash is
/// self-contained; `main.dart` re-exports the same provider.
final Provider<SecureStorage> secureStorageProvider =
    Provider<SecureStorage>((_) => SecureStorage());

/// First page. The router's redirect pushes the user toward `/login` if
/// there's no JWT; device_id is generated eagerly in `main()` so this
/// page just renders the brand mark before go_router forwards on.
class SplashPage extends StatelessWidget {
  const SplashPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: const <Widget>[
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Selfwell', style: TextStyle(fontSize: 22)),
          ],
        ),
      ),
    );
  }
}