/// IA-REF: docs/design/ia-and-wireframe.md §6.4 P07-A/B/C 抱抱卡海报
/// 设计稿:
///   - docs/design/figma-pixso-spec/pages/12-hug-card-day7.html
///   - docs/design/figma-pixso-spec/pages/13-hug-card-day14.html
///   - docs/design/figma-pixso-spec/pages/14-hug-card-day21.html
/// 后端端点: openapi.yaml tag=[share] operationId=generateSharePoster
///                      POST /share/poster?day={7|14|21}
///
/// 3 张海报共用 ?day=7/14/21。规格: 750×1000 px 比例，无禁用颜色。
library;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../login/login_page.dart' show apiServiceProvider;

class HugCardPage extends ConsumerStatefulWidget {
  const HugCardPage({super.key, required this.day});
  final int day;

  @override
  ConsumerState<HugCardPage> createState() => _HugCardPageState();
}

class _HugCardPageState extends ConsumerState<HugCardPage> {
  Future<HugCard>? _future;

  @override
  void initState() {
    super.initState();
    _future = ref.read(apiServiceProvider).generateHugCard(widget.day);
  }

  @override
  void didUpdateWidget(covariant HugCardPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.day != widget.day) {
      setState(() {
        _future = ref.read(apiServiceProvider).generateHugCard(widget.day);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(
        title: const Text('抱抱卡'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => context.pop(),
        ),
      ),
      body: SafeArea(
        child: Center(
          child: AspectRatio(
            aspectRatio: 750 / 1000,
            child: FutureBuilder<HugCard>(
              future: _future,
              builder: (BuildContext context, AsyncSnapshot<HugCard> snap) {
                if (snap.connectionState != ConnectionState.done) {
                  return const Center(child: CircularProgressIndicator());
                }
                return _Poster(day: widget.day, imageUrl: snap.data?.imageUrl);
              },
            ),
          ),
        ),
      ),
    );
  }
}

class _Poster extends StatelessWidget {
  const _Poster({required this.day, this.imageUrl});
  final int day;
  final String? imageUrl;

  String get _caption {
    switch (day) {
      case 7:
        return '7 天的坚持，是给自己的温柔礼物。';
      case 14:
        return '14 天，你已经在成为更好的自己。';
      case 21:
        return '21 天，一个小里程碑。你值得被抱抱。';
      default:
        return '慢慢来。';
    }
  }

  String get _subCaption {
    return 'Selfwell 自愈';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: <Color>[AppColors.primaryCream, AppColors.primaryLavender],
        ),
        borderRadius: BorderRadius.circular(AppRadius.xl),
        boxShadow: const <BoxShadow>[
          BoxShadow(
            color: Color(0x10000000),
            blurRadius: 16,
            offset: Offset(0, 6),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(AppRadius.xl),
        child: Stack(
          children: <Widget>[
            // Top brand bar
            Positioned(
              top: 32,
              left: 32,
              right: 32,
              child: Row(
                children: <Widget>[
                  Container(
                    width: 40,
                    height: 40,
                    decoration: const BoxDecoration(
                      color: AppColors.primaryMint,
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.spa_outlined,
                        color: Colors.white, size: 24),
                  ),
                  const SizedBox(width: 12),
                  Text(
                    _subCaption,
                    style: const TextStyle(
                      fontSize: 16,
                      color: AppColors.neutral900,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            // Center "Day N" + caption
            Positioned.fill(
              child: Padding(
                padding: const EdgeInsets.all(40),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Text(
                      '第 $day 天',
                      style: const TextStyle(
                        fontSize: 56,
                        color: AppColors.neutral900,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 16),
                    Container(
                      width: 120,
                      height: 120,
                      decoration: const BoxDecoration(
                        color: AppColors.primaryMint,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(Icons.favorite,
                          color: Colors.white, size: 64),
                    ),
                    const SizedBox(height: 24),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 32),
                      child: Text(
                        _caption,
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          fontSize: 22,
                          color: AppColors.neutral700,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Bottom CTA
            Positioned(
              left: 32,
              right: 32,
              bottom: 32,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: <Widget>[
                  Container(
                    width: 80,
                    height: 80,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: AppRadius.rSm,
                    ),
                    child: const Center(
                      child: Icon(Icons.qr_code_2,
                          color: AppColors.neutral900, size: 60),
                    ),
                  ),
                  ElevatedButton.icon(
                    onPressed: () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(content: Text('分享面板在 SF5 联调时接入 share_plus')),
                      );
                    },
                    icon: const Icon(Icons.share, color: Colors.white),
                    label: const Text('分享'),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
