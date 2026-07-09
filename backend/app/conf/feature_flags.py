"""Feature Flag 配置。

用于控制功能灰度开关，所有 flag 默认关闭以保证安全性。
"""

from __future__ import annotations

import hashlib


class FeatureFlags:
    """Selfwell 功能开关（所有开关默认 False / 0）。"""

    # ── 智能管家 ──────────────────────────────────────────────
    # assistant_vision_enabled: 全局开关（即使 sample_rate > 0 也必须此为 True）
    assistant_vision_enabled: bool = True
    # assistant_vision_sample_rate: 0.0-1.0，真实 vision LLM 流量比例
    # Sprint 1 → 0（全部走 rule_engine mock）
    # Sprint 3 → 0.01（1% 真实流量）
    # Sprint 4 → 1.0（全量）
    assistant_vision_sample_rate: float = 1.0

    def should_use_vision(self, user_id: str) -> bool:
        """一致性哈希抽样：同一 user_id 永远落在同一 bucket。"""
        if not self.assistant_vision_enabled:
            return False
        bucket = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16) % 1000
        return bucket < self.assistant_vision_sample_rate * 1000


# 全局单例（FastAPI 依赖注入或直接导入）
feature_flags = FeatureFlags()

__all__ = ["FeatureFlags", "feature_flags"]
