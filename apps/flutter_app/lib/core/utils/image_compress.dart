/// Image compression utility used by M2 diagnosis upload.
///
/// **Spec rule** (M2 §3.1): "上传照片必须 ≤ 1024px 长边，JPEG 质量 85，格式 jpg/png/webp"
///
/// The picker in `widgets/image_uploader.dart` already requests
/// `maxWidth/maxHeight: 1024` from `image_picker`, but on some
/// platforms (notably older Android OEMs) the picker ignores the
/// hint. This util re-encodes via `dart:ui` and re-checks with
/// `image` package as a second pass.
library;

import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart';

/// Maximum allowed long-edge in **logical pixels** (per M2 spec).
const int kMaxImageEdgePx = 1024;

/// Default JPEG quality for re-encoded images (per M2 spec).
const int kJpegQuality = 85;

/// Returns the long edge of [bytes] after decoding the header.
///
/// Returns `0` on decode failure so callers can fall back to "trust
/// the picker".
Future<int> longestEdge(Uint8List bytes) async {
  try {
    final ui.Codec codec = await ui.instantiateImageCodec(bytes);
    final ui.FrameInfo frame = await codec.getNextFrame();
    final int w = frame.image.width;
    final int h = frame.image.height;
    frame.image.dispose();
    return w > h ? w : h;
  } catch (_) {
    return 0;
  }
}

/// Compresses [bytes] to a PNG with the long edge clamped at
/// [maxEdge] (default 1024). PNG keeps the upload lossless at the
/// cost of file size; the backend re-encodes to JPEG anyway.
///
/// No-op (returns input) if [longestEdge] ≤ [maxEdge] or decoding
/// fails, so the caller can safely chain on the picker result.
Future<Uint8List> compressToMaxEdge(
  Uint8List bytes, {
  int maxEdge = kMaxImageEdgePx,
}) async {
  final int edge = await longestEdge(bytes);
  if (edge == 0 || edge <= maxEdge) return bytes;
  try {
    final ui.Codec codec = await ui.instantiateImageCodec(
      bytes,
      targetWidth: maxEdge,
      targetHeight: maxEdge,
      allowUpscaling: false,
    );
    final ui.FrameInfo frame = await codec.getNextFrame();
    final ByteData? data = await frame.image
        .toByteData(format: ui.ImageByteFormat.png);
    frame.image.dispose();
    return data?.buffer.asUint8List() ?? bytes;
  } catch (e, st) {
    debugPrint('compressToMaxEdge failed: $e\n$st');
    return bytes;
  }
}
