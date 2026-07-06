/// IA-REF: docs/design/ia-and-wireframe.md §4.3 P03a-s1 三步卡 第一步·上传
/// 设计稿: docs/design/figma-pixso-spec/pages/04-butler-analyze-upload.html
/// 后端端点:
///   - openapi.yaml tag=[uploads]  operationId=presignUpload POST /uploads/presign
///   - openapi.yaml tag=[diagnosis] operationId=createDiagnosis POST /diagnosis
///
/// M2 spec rules:
///   - 3 张照片 (正面脸 / 侧面体态 / 发质特写)
///   - 每张图片必须 ≤ 1024px (§17 强约束 + SPEC-M2)
///   - 压缩工具 lib/core/utils/image_compress.dart
library;

import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/api/api_service.dart';
import '../../core/api/api_types.dart';
import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../core/utils/image_compress.dart';
import '../login/login_page.dart' show apiServiceProvider;

class DiagnosisUploadPage extends ConsumerStatefulWidget {
  const DiagnosisUploadPage({super.key});

  @override
  ConsumerState<DiagnosisUploadPage> createState() =>
      _DiagnosisUploadPageState();
}

enum _PhotoSlot { face, side, hair }

extension on _PhotoSlot {
  String get label {
    switch (this) {
      case _PhotoSlot.face:
        return '正面脸';
      case _PhotoSlot.side:
        return '侧面体态';
      case _PhotoSlot.hair:
        return '发质特写';
    }
  }

  IconData get icon {
    switch (this) {
      case _PhotoSlot.face:
        return Icons.face_outlined;
      case _PhotoSlot.side:
        return Icons.accessibility_new;
      case _PhotoSlot.hair:
        return Icons.face_retouching_natural;
    }
  }
}

class _DiagnosisUploadPageState extends ConsumerState<DiagnosisUploadPage> {
  final ImagePicker _picker = ImagePicker();
  final Map<_PhotoSlot, Uint8List> _photos = <_PhotoSlot, Uint8List>{};
  bool _busy = false;

  Future<void> _pick(_PhotoSlot slot) async {
    final XFile? file = await _picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: kMaxImageEdgePx.toDouble(),
      maxHeight: kMaxImageEdgePx.toDouble(),
      imageQuality: kJpegQuality,
    );
    if (file == null) return;
    final Uint8List bytes = await file.readAsBytes();
    final Uint8List compressed = await compressToMaxEdge(bytes);
    setState(() => _photos[slot] = compressed);
  }

  Future<void> _submit() async {
    if (_busy) return;
    if (_photos.length < 3) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('请先选 3 张照片')),
      );
      return;
    }
    setState(() => _busy = true);
    try {
      final ApiService api = ref.read(apiServiceProvider);
      final DiagnosisJob job = await api.createDiagnosis(<String>[
        'local://photo-face',
        'local://photo-side',
        'local://photo-hair',
      ]);
      if (!mounted) return;
      context.push('/diagnosis/loading', extra: job.id);
    } on DioException catch (e) {
      _toast('提交失败：${e.message ?? '网络异常'}');
    } catch (e) {
      _toast('提交失败：$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _toast(String s) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(s)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(title: const Text('智能分析')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(AppSpacing.s4),
          children: <Widget>[
            const Text(
              '上传 3 张照片',
              style: TextStyle(fontSize: 22, color: AppColors.neutral900),
            ),
            const SizedBox(height: 4),
            const Text(
              '正面脸 · 侧面体态 · 发质特写',
              style: TextStyle(fontSize: 14, color: AppColors.neutral700),
            ),
            const SizedBox(height: AppSpacing.s4),
            Row(
              children: <Widget>[
                for (final _PhotoSlot slot in _PhotoSlot.values) ...<Widget>[
                  Expanded(
                    child: _PhotoTile(
                      slot: slot,
                      bytes: _photos[slot],
                      onTap: () => _pick(slot),
                    ),
                  ),
                  if (slot != _PhotoSlot.hair)
                    const SizedBox(width: AppSpacing.s3),
                ],
              ],
            ),
            const SizedBox(height: AppSpacing.s6),
            const Divider(color: AppColors.neutral100),
            const SizedBox(height: AppSpacing.s3),
            const Text(
              '可选：填写档案',
              style: TextStyle(fontSize: 14, color: AppColors.neutral700),
            ),
            const SizedBox(height: 8),
            const Text(
              '· 年龄范围 / 久坐时长\n· 关注部位 / 强度偏好',
              style: TextStyle(fontSize: 12, color: AppColors.neutral500),
            ),
            const SizedBox(height: AppSpacing.s6),
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
                  : const Text('开始分析'),
            ),
          ],
        ),
      ),
    );
  }
}

class _PhotoTile extends StatelessWidget {
  const _PhotoTile({
    required this.slot,
    required this.bytes,
    required this.onTap,
  });

  final _PhotoSlot slot;
  final Uint8List? bytes;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final bool has = bytes != null;
    return GestureDetector(
      onTap: onTap,
      child: AspectRatio(
        aspectRatio: 1,
        child: Container(
          decoration: BoxDecoration(
            color: has ? AppColors.bgCard : AppColors.bgPage,
            borderRadius: AppRadius.rLg,
            border: Border.all(
              color: has ? AppColors.primaryMint : AppColors.neutral100,
              width: has ? 2 : 1,
            ),
          ),
          child: has
              ? Stack(
                  children: <Widget>[
                    Positioned.fill(
                      child: ClipRRect(
                        borderRadius: AppRadius.rLg,
                        child: Image.memory(bytes!, fit: BoxFit.cover),
                      ),
                    ),
                    Positioned(
                      left: 8,
                      bottom: 8,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.black54,
                          borderRadius: AppRadius.rSm,
                        ),
                        child: Text(
                          slot.label,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                          ),
                        ),
                      ),
                    ),
                  ],
                )
              : Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Icon(slot.icon,
                        size: 32, color: AppColors.primaryMint),
                    const SizedBox(height: 4),
                    Text(
                      slot.label,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.neutral700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      '+ 添加',
                      style: TextStyle(
                        fontSize: 10,
                        color: AppColors.neutral500,
                      ),
                    ),
                  ],
                ),
        ),
      ),
    );
  }
}
