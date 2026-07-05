import 'package:flutter/material.dart';

import '../core/theme/color_tokens.dart';
import '../core/theme/spacing.dart';

/// M5 persona 4-state FSM widget — maps to the backend
/// `assistant.persona_state` field. See `docs/spec/SPEC-M5-*.md`.
enum PersonaState { warm, neutral, slightHug, medicalGuarded }

extension PersonaStateX on PersonaState {
  Color get bubbleColor {
    switch (this) {
      case PersonaState.warm:
        return AppColors.personaWarm;
      case PersonaState.neutral:
        return AppColors.personaNeutral;
      case PersonaState.slightHug:
        return AppColors.personaSlightHug;
      case PersonaState.medicalGuarded:
        return AppColors.personaMedicalGuarded;
    }
  }

  IconData get icon {
    switch (this) {
      case PersonaState.warm:
        return Icons.favorite_border;
      case PersonaState.neutral:
        return Icons.chat_bubble_outline;
      case PersonaState.slightHug:
        return Icons.self_improvement;
      case PersonaState.medicalGuarded:
        return Icons.shield_outlined;
    }
  }

  String get label {
    switch (this) {
      case PersonaState.warm:
        return '温暖陪伴';
      case PersonaState.neutral:
        return '中立观察';
      case PersonaState.slightHug:
        return '轻拥抱';
      case PersonaState.medicalGuarded:
        return '医学守门';
    }
  }
}

/// Pill-shaped persona bubble with state-specific color + icon.
class PersonaBubble extends StatelessWidget {
  const PersonaBubble({
    required this.state,
    super.key,
    this.size = 40,
  });

  final PersonaState state;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: state.bubbleColor,
        shape: BoxShape.circle,
      ),
      child: Icon(state.icon, color: Colors.white, size: size * 0.55),
    );
  }
}

/// Wrapping row used in chat messages — bubble + label.
class PersonaBubbleWithLabel extends StatelessWidget {
  const PersonaBubbleWithLabel({required this.state, super.key});

  final PersonaState state;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.s2),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: <Widget>[
          PersonaBubble(state: state),
          const SizedBox(width: AppSpacing.s2),
          Text(state.label, style: const TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}