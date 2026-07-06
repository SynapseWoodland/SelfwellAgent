/// Grep script for §17 strong-constraint #11: forbidden pixel colors
/// (#FF4D4F / #D32F2F / #007BFF) MUST be 0-hit anywhere in the Flutter
/// or WeChat miniprogram source.
///
/// Usage:
///   dart run tool/check_forbidden_colors.dart
///
/// Exit code 0 = pass, 1 = fail.
library;

import 'dart:io';

const List<String> _forbidden = <String>[
  '#FF4D4F',
  '#D32F2F',
  '#007BFF',
];

const List<String> _roots = <String>[
  'apps/flutter_app/lib',
  'apps/flutter_app/test',
  'apps/mp-selfwell',
];

/// Files that are *allowed* to mention the forbidden colors — by
/// design. The grep is about the *use* of those colors, not about
/// the regex that detects them.
const List<String> _allowList = <String>[
  'apps/flutter_app/tool/check_forbidden_colors.dart',
];

void main(List<String> args) {
  final List<String> hits = <String>[];
  for (final String root in _roots) {
    final Directory dir = Directory(root);
    if (!dir.existsSync()) {
      stderr.writeln('skip missing: $root');
      continue;
    }
    for (final FileSystemEntity ent in dir.listSync(recursive: true)) {
      if (ent is! File) continue;
      if (_allowList.contains(ent.path.replaceAll(r'\', '/'))) continue;
      if (!ent.path.endsWith('.dart') &&
          !ent.path.endsWith('.wxss') &&
          !ent.path.endsWith('.ts') &&
          !ent.path.endsWith('.js')) {
        continue;
      }
      final List<String> lines = ent.readAsLinesSync();
      for (int i = 0; i < lines.length; i++) {
        for (final String f in _forbidden) {
          if (lines[i].toUpperCase().contains(f.toUpperCase())) {
            hits.add('${ent.path}:${i + 1}: ${lines[i].trim()}');
          }
        }
      }
    }
  }

  if (hits.isEmpty) {
    stdout.writeln('OK: 0 forbidden-color hits across ${_roots.length} roots.');
    exit(0);
  } else {
    stderr.writeln('FAIL: ${hits.length} forbidden-color hits:');
    for (final String h in hits) {
      stderr.writeln('  $h');
    }
    exit(1);
  }
}
