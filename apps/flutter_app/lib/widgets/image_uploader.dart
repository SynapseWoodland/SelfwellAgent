import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../core/theme/color_tokens.dart';
import '../core/theme/spacing.dart';

/// Image uploader with built-in compression to <= 1024px max-edge.
///
/// Wraps `image_picker` so the parent page just receives a `Uint8List`.
/// Per `docs/spec/SPEC-M2-multimodal-diagnosis.md`, uploaded images
/// must be <= 1024px (server-side validator in `services/diagnosis/image_validator.py`).
class ImageUploader extends StatefulWidget {
  const ImageUploader({
    required this.onPicked,
    super.key,
    this.maxEdge = 1024,
    this.pickFromCamera = true,
    this.pickFromGallery = true,
  });

  final ValueChanged<Uint8List> onPicked;
  final int maxEdge;

  final bool pickFromCamera;
  final bool pickFromGallery;

  @override
  State<ImageUploader> createState() => _ImageUploaderState();
}

class _ImageUploaderState extends State<ImageUploader> {
  final ImagePicker _picker = ImagePicker();
  bool _busy = false;

  Future<void> _pick(ImageSource source) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final XFile? picked = await _picker.pickImage(
        source: source,
        maxWidth: widget.maxEdge.toDouble(),
        maxHeight: widget.maxEdge.toDouble(),
        imageQuality: 85,
      );
      if (picked == null) return;
      final Uint8List bytes = await picked.readAsBytes();
      final Uint8List compressed = await _ensureMaxEdge(bytes);
      widget.onPicked(compressed);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Belt-and-braces clamp: re-encodes via dart:ui if the picker
  /// ignored the max-edge hint (some platforms do).
  Future<Uint8List> _ensureMaxEdge(Uint8List bytes) async {
    final ui.Codec codec = await ui.instantiateImageCodec(
      bytes,
      targetWidth: widget.maxEdge,
      targetHeight: widget.maxEdge,
      allowUpscaling: false,
    );
    final ui.FrameInfo frame = await codec.getNextFrame();
    final ByteData? data =
        await frame.image.toByteData(format: ui.ImageByteFormat.png);
    return data?.buffer.asUint8List() ?? bytes;
  }

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: AppSpacing.s3,
      children: <Widget>[
        if (widget.pickFromGallery)
          _SourceButton(
            label: _busy ? '处理中…' : '从相册选图',
            icon: Icons.photo_library_outlined,
            onPressed: _busy ? null : () => _pick(ImageSource.gallery),
          ),
        if (widget.pickFromCamera)
          _SourceButton(
            label: _busy ? '处理中…' : '拍一张',
            icon: Icons.photo_camera_outlined,
            onPressed: _busy ? null : () => _pick(ImageSource.camera),
          ),
      ],
    );
  }
}

class _SourceButton extends StatelessWidget {
  const _SourceButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: onPressed,
      icon: Icon(icon, color: AppColors.primaryMint),
      label: Text(label, style: const TextStyle(color: AppColors.primaryMint)),
      style: OutlinedButton.styleFrom(
        side: const BorderSide(color: AppColors.primaryMint),
        shape: const RoundedRectangleBorder(borderRadius: AppRadius.rXl),
      ),
    );
  }
}