/// IA-REF: docs/design/ia-and-wireframe.md §4.3 P03 智能管家 (上传子步骤)
/// 设计稿: docs/design/figma-pixso-spec/pages/04-butler-analyze-upload.html
/// 后端端点:
///   - openapi.yaml tag=[diagnosis] operationId=createDiagnosis POST /diagnosis
///   - openapi.yaml tag=[diagnosis] operationId=streamDiagnosis  GET  /diagnosis/{id}/stream (SSE 8 阶段)
///
/// Token: color/primary/lavender=#D4C5E2, color/bg/card=#FFFFFF,
///        radius/lg=16, spacing/4=16
/// 来源: docs/design/figma-pixso-spec/dist/tokens-flat.json
library;

import 'dart:typed_data';

import 'package:flutter/material.dart';

import '../../../core/theme/color_tokens.dart';
import '../../../core/theme/spacing.dart';
import '../../../widgets/image_uploader.dart';

/// Diagnosis upload page (P03 step 1/3). SF0 placeholder + image uploader.
class DiagnosisUploadPage extends StatefulWidget {
  const DiagnosisUploadPage({super.key});

  @override
  State<DiagnosisUploadPage> createState() => _DiagnosisUploadPageState();
}

class _DiagnosisUploadPageState extends State<DiagnosisUploadPage> {
  Uint8List? _preview;

  void _onPicked(Uint8List bytes) {
    setState(() => _preview = bytes);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.bgPage,
      appBar: AppBar(title: const Text('智能分析 · 上传')),
      body: Padding(
        padding: const EdgeInsets.all(AppSpacing.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            const Text(
              '请拍摄 3 张清晰肤况照片',
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.w500,
                color: AppColors.neutral900,
              ),
            ),
            const SizedBox(height: AppSpacing.s2),
            const Text(
              '建议自然光，正面 1 张 + 侧面 2 张',
              style: TextStyle(color: AppColors.neutral500),
            ),
            const SizedBox(height: AppSpacing.s6),
            AspectRatio(
              aspectRatio: 1,
              child: Container(
                decoration: BoxDecoration(
                  color: AppColors.primaryLavender,
                  borderRadius: AppRadius.rLg,
                ),
                alignment: Alignment.center,
                child: _preview == null
                    ? const Icon(Icons.image_outlined,
                        color: Colors.white, size: 56)
                    : Image.memory(_preview!, fit: BoxFit.cover),
              ),
            ),
            const SizedBox(height: AppSpacing.s4),
            ImageUploader(onPicked: _onPicked),
          ],
        ),
      ),
    );
  }
}