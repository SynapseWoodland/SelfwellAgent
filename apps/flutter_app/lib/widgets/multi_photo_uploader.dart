/// 3-slot photo uploader for M2 diagnosis.
///
/// §17 strong-constraint #8: each photo is compressed to ≤ 1024px by
/// the [compressToMaxEdge] util. The widget exposes a [ValueListenable]
/// of the picked [Uint8List]s so the page can wire them to the create
/// endpoint on submit.
library;

import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/theme/color_tokens.dart';
import '../../core/theme/spacing.dart';
import '../../core/utils/image_compress.dart';

class MultiPhotoUploader extends StatefulWidget {
  const MultiPhotoUploader({
    required this.onChanged,
    super.key,
    this.maxSlots = 3,
    this.maxEdge = kMaxImageEdgePx,
  });

  final void Function(List<Uint8List> photos) onChanged;
  final int maxSlots;
  final int maxEdge;

  @override
  State<MultiPhotoUploader> createState() => _MultiPhotoUploaderState();
}

class _MultiPhotoUploaderState extends State<MultiPhotoUploader> {
  final ImagePicker _picker = ImagePicker();
  final List<Uint8List> _photos = <Uint8List>[];
  bool _busy = false;

  Future<void> _add() async {
    if (_busy) return;
    if (_photos.length >= widget.maxSlots) return;
    setState(() => _busy = true);
    try {
      final XFile? picked = await _picker.pickImage(
        source: ImageSource.gallery,
        maxWidth: widget.maxEdge.toDouble(),
        maxHeight: widget.maxEdge.toDouble(),
        imageQuality: 85,
      );
      if (picked == null) return;
      final Uint8List bytes = await picked.readAsBytes();
      final Uint8List compressed = await compressToMaxEdge(bytes, maxEdge: widget.maxEdge);
      if (!mounted) return;
      setState(() => _photos.add(compressed));
      widget.onChanged(List<Uint8List>.unmodifiable(_photos));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _remove(int index) {
    setState(() => _photos.removeAt(index));
    widget.onChanged(List<Uint8List>.unmodifiable(_photos));
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: <Widget>[
        const Text(
          '请上传 3 张照片（正面 + 侧面 + 体态）',
          style: TextStyle(color: AppColors.neutral700),
        ),
        const SizedBox(height: AppSpacing.s3),
        Row(
          children: List<Widget>.generate(widget.maxSlots, (int i) {
            final bool filled = i < _photos.length;
            return Expanded(
              child: Padding(
                padding: EdgeInsets.only(
                  right: i < widget.maxSlots - 1 ? AppSpacing.s2 : 0,
                ),
                child: AspectRatio(
                  aspectRatio: 1,
                  child: GestureDetector(
                    onTap: filled ? () => _remove(i) : _add,
                    child: Container(
                      decoration: BoxDecoration(
                        color: AppColors.bgCardWarm,
                        borderRadius: AppRadius.rLg,
                      ),
                      alignment: Alignment.center,
                      child: filled
                          ? Stack(
                              fit: StackFit.expand,
                              children: <Widget>[
                                ClipRRect(
                                  borderRadius: AppRadius.rLg,
                                  child: Image.memory(_photos[i], fit: BoxFit.cover),
                                ),
                                const Positioned(
                                  right: 4,
                                  top: 4,
                                  child: Icon(
                                    Icons.cancel,
                                    color: Colors.white,
                                  ),
                                ),
                              ],
                            )
                          : Icon(
                              _busy ? Icons.hourglass_top : Icons.add_a_photo,
                              color: AppColors.neutral500,
                              size: 32,
                            ),
                    ),
                  ),
                ),
              ),
            );
          }),
        ),
      ],
    );
  }
}
