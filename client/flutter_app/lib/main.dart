import 'package:flutter/material.dart';

void main() {
  runApp(const SelfwellApp());
}

class SelfwellApp extends StatelessWidget {
  const SelfwellApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Selfwell 自愈',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFFA8C5B5), // design-spec §3.1 薄荷绿
          brightness: Brightness.light,
        ),
        useMaterial3: true,
      ),
      home: const _PlaceholderHome(),
    );
  }
}

class _PlaceholderHome extends StatelessWidget {
  const _PlaceholderHome();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Selfwell 自愈'),
        backgroundColor: Theme.of(context).colorScheme.primary,
        foregroundColor: Colors.white,
      ),
      body: const Center(
        child: Padding(
          padding: EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'MVP 启动中...',
                style: TextStyle(fontSize: 28, fontWeight: FontWeight.w600),
              ),
              SizedBox(height: 16),
              Text(
                'W0 占位页 — W1-D3 起按 SPEC 实现 splash/login/home',
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 16, color: Color(0xFF7F8B8E)),
              ),
            ],
          ),
        ),
      ),
    );
  }
}