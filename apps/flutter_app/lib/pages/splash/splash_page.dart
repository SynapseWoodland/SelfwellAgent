/// IA-REF: docs/design/ia-and-wireframe.md §1.2 启动流程 (P01)
/// 设计稿: docs/design/figma-pixso-spec/pages/01-splash.html
/// 后端端点: — (本 Sprint 本地生成 device_id，无后端调用)
/// 推送 payload: §17 #17 — traceparent + client_platform + user_id_pseudo
///
/// Token: color/primary/mint=#A8C5B5, color/primary/cream=#F5E6D3
///        color/neutral/900=#2D3436, color/neutral/500=#718096
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/storage/secure_storage.dart';

// Re-export so historical `import '.../splash_page.dart' show secureStorageProvider`
// imports keep compiling. The canonical provider lives in
// `core/storage/secure_storage.dart` now.
export '../../core/storage/secure_storage.dart' show secureStorageProvider;

/// First page. The router's redirect pushes the user toward `/login` if
/// there's no JWT; device_id is generated eagerly in `main()` so this
/// page just renders the brand mark before go_router forwards on.
class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});

  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      final SecureStorage storage = ref.read(secureStorageProvider);
      final String? token = await storage.readJwt();
      if (!mounted) return;
      if (token != null && token.isNotEmpty) {
        context.go('/home');
      } else {
        context.go('/login');
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFFAFBFC),
      body: SafeArea(
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: const <Widget>[
              _BrandLogo(),
              SizedBox(height: 12),
              Text(
                'Selfwell',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w500,
                  color: Color(0xFF4A5568),
                ),
              ),
              SizedBox(height: 32),
              SizedBox(
                width: 28,
                height: 28,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BrandLogo extends StatelessWidget {
  const _BrandLogo();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 80,
      height: 80,
      decoration: const BoxDecoration(
        color: Color(0xFFA8C5B5),
        shape: BoxShape.circle,
      ),
      child: const Center(
        child: Icon(Icons.spa_outlined, color: Colors.white, size: 40),
      ),
    );
  }
}
