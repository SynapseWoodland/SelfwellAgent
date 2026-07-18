# Standalone compliance test — does NOT depend on app.llm or conftest.py
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest
import yaml


class Violation(NamedTuple):
    rule_id: str
    rule_name: str
    matched_text: str
    line_id: int | None = None

    def __str__(self) -> str:
        loc = f" (id:{self.line_id})" if self.line_id else ""
        return f"[{self.rule_id}] {self.rule_name}{loc}: 「{self.matched_text}」"


# ──────────────────────────────────────────────
# 合规红线词表（来自 PRD §3.2）
# ──────────────────────────────────────────────
class ComplianceRedLines:
    """PRD §3.2 合规红线 — 产品面向用户的话术规则"""

    # 红线#1: 医疗表述
    MEDICAL_PATTERNS = [
        re.compile(r"治疗"),
        re.compile(r"治愈"),
        re.compile(r"医生|医师"),
        re.compile(r"处方"),
        re.compile(r"(肯定|确定|能)(治|治愈|看好|解决)"),
        re.compile(r"去医院"),
        re.compile(r"看病"),
    ]

    # 红线#2: 效果承诺
    EFFECT_PATTERNS = [
        re.compile(r"会变白"),
        re.compile(r"会变小"),
        re.compile(r"会提升"),
        re.compile(r"会改善"),
        re.compile(r"会变(好|瘦|美)"),
        re.compile(r"变得(更?好|更?美|更?瘦)"),
        re.compile(r"改善.*?(皮肤|身材|体重|体型)"),
        re.compile(r"改变你"),  # "悄悄改变你" — 暗示改善效果
        re.compile(r"更好的自己"),  # 前后对比 + 效果承诺
        re.compile(r"蜕变"),  # 暗示改善/质变
    ]

    # 红线#3: 前后对比判断
    BEFORE_AFTER_PATTERNS = [
        re.compile(r"比昨天"),
        re.compile(r"比之前"),
        re.compile(r"比从前"),
        re.compile(r"比(原来|以前|过去|上次)更?"),
        re.compile(r"进步了"),
        re.compile(r"变好了"),
        re.compile(r"更有韧性"),  # PRD PM-Review-v2 §二 明确禁止
    ]

    # 红线#4: 数字量化
    QUANTIFY_PATTERNS = [
        re.compile(r"\d+天"),  # "坚持6天" — 量化打卡天数
        re.compile(r"还差\d+天"),
        re.compile(r"BMI"),
        re.compile(r"体重"),
        re.compile(r"三围"),
        re.compile(r"\d+厘米"),
        re.compile(r"\d+kg"),
        re.compile(r"\d+斤"),
    ]

    # 红线#5: 颜值/外貌评判
    APPEARANCE_PATTERNS = [
        re.compile(r"变漂亮"),
        re.compile(r"颜值高"),
        re.compile(r"变美"),
        re.compile(r"长得(好看|漂亮|美)"),
        re.compile(r"好看了"),
    ]

    # 红线#6: 强推打卡 / 隐性评判
    PUSH_PATTERNS = [
        re.compile(r"必须坚持"),
        re.compile(r"不能断"),
        re.compile(r"中断就(失败|完蛋|归零)"),
        re.compile(r"坚持(就是|才)(成功|胜利|厉害)"),
        re.compile(r"能坚持到(这里|现在)", re.IGNORECASE),  # 隐性评判坚持=好
        re.compile(r"每一步都算数"),  # 量化打卡价值，边界违规
    ]

    # 红线#6 边界词汇白名单（轻微压力感但可接受）
    # 仅在 "继续加油" 单独出现时通过；与其他压力词组合仍触发
    PUSH_WHITELIST = re.compile(r"^(?!.*(必须|不能|断了|失败|完蛋|归零))[^\n]{0,20}$")




def _scan(text: str, patterns: list[re.Pattern]) -> list[str]:
    """Return matched substrings from text using patterns."""
    return [m.group() for p in patterns for m in p.finditer(text)]


def check_line(line_id: int, text: str) -> list[Violation]:
    """Scan a single ACK line for all red-line violations."""
    violations: list[Violation] = []

    # 红线#1
    if matches := _scan(text, ComplianceRedLines.MEDICAL_PATTERNS):
        violations.append(Violation("R1", "医疗表述", ", ".join(matches), line_id))

    # 红线#2
    if matches := _scan(text, ComplianceRedLines.EFFECT_PATTERNS):
        violations.append(Violation("R2", "效果承诺", ", ".join(matches), line_id))

    # 红线#3
    if matches := _scan(text, ComplianceRedLines.BEFORE_AFTER_PATTERNS):
        violations.append(Violation("R3", "前后对比判断", ", ".join(matches), line_id))

    # 红线#4
    if matches := _scan(text, ComplianceRedLines.QUANTIFY_PATTERNS):
        violations.append(Violation("R4", "数字量化", ", ".join(matches), line_id))

    # 红线#5
    if matches := _scan(text, ComplianceRedLines.APPEARANCE_PATTERNS):
        violations.append(Violation("R5", "颜值/外貌评判", ", ".join(matches), line_id))

    # 红线#6
    # "继续加油" 单独出现时为边界通过；与其他压力词组合仍触发
    r6_matches = _scan(text, ComplianceRedLines.PUSH_PATTERNS)
    if r6_matches:
        # 白名单豁免: "继续加油" 单独出现 (id:5/27)
        if r6_matches == ["继续加油"] and len(text.strip()) < 25:
            pass  # 豁免通过
        else:
            violations.append(Violation("R6", "强推打卡/隐性评判", ", ".join(r6_matches), line_id))

    return violations


# ──────────────────────────────────────────────
# Test fixtures
# ──────────────────────────────────────────────

@pytest.fixture(scope="module")
def ack_pool() -> dict:
    """Load ack-pool.yaml — standalone fixture, no app dependencies."""
    pool_path = Path(__file__).parents[3] / "docs" / "data" / "ack-pool.yaml"
    if not pool_path.exists():
        pytest.skip(f"ack-pool.yaml not found at {pool_path}")
    with pool_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ──────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────

class TestAckPoolCompliance:
    """PRD §3.2 合规红线 — 每次修改 ack-pool.yaml 必须全量通过"""

    def test_pool_exists(self, ack_pool: dict) -> None:
        assert "pool" in ack_pool, "ack-pool.yaml must have 'pool' key"
        assert len(ack_pool["pool"]) == 30, "Pool must contain exactly 30 entries"

    def test_all_lines_valid(self, ack_pool: dict) -> None:
        """所有 valid=true 的行都必须通过红线扫描"""
        all_violations: list[Violation] = []
        skipped: list[int] = []

        for entry in ack_pool["pool"]:
            line_id = entry.get("id")
            text = entry.get("text", "")
            valid = entry.get("valid", True)

            if not valid:
                skipped.append(line_id)
                continue

            violations = check_line(line_id, text)
            all_violations.extend(violations)

        if skipped:
            print(f"\n[INFO] Skipped invalid entries: {skipped}")

        if all_violations:
            lines = "\n".join(f"  - {v}" for v in all_violations)
            pytest.fail(
                f"ACK 池发现 {len(all_violations)} 个合规违规:\n{lines}\n\n"
                f"请修复 docs/data/ack-pool.yaml 后重新提交。\n"
                f"合规依据: PRD V1.1 §3.2 合规红线"
            )

    def test_no_digit_days_in_ack(self, ack_pool: dict) -> None:
        """
        硬性检查: ACK 文本中禁止出现 "N天" 形式的量化打卡天数。
        这是一条明确的产品承诺。
        """
        violations: list[Violation] = []
        day_pattern = re.compile(r"\d+\s*天")

        for entry in ack_pool["pool"]:
            if not entry.get("valid", True):
                continue
            text = entry.get("text", "")
            if matches := day_pattern.findall(text):
                violations.append(
                    Violation("R4", "数字量化(天数)", ", ".join(matches), entry.get("id"))
                )

        assert not violations, (
            f"发现 {len(violations)} 处天数量化: "
            + "; ".join(str(v) for v in violations)
        )

    def test_no_comparison_words(self, ack_pool: dict) -> None:
        """
        硬性检查: ACK 文本中禁止出现明确的前后对比语言。
        PRD §3.2 红线#3: 禁止前后对比判断。
        """
        violations: list[Violation] = []
        comparison_patterns = [
            re.compile(r"比昨天"),
            re.compile(r"比之前"),
            re.compile(r"更好的自己"),
            re.compile(r"进步了"),
        ]

        for entry in ack_pool["pool"]:
            if not entry.get("valid", True):
                continue
            text = entry.get("text", "")
            for p in comparison_patterns:
                if m := p.search(text):
                    violations.append(
                        Violation("R3", "前后对比判断", m.group(), entry.get("id"))
                    )

        assert not violations, (
            f"发现 {len(violations)} 处前后对比: "
            + "; ".join(str(v) for v in violations)
        )

    def test_version_bumped(self, ack_pool: dict) -> None:
        """ACK 池版本必须 ≥ 1.1（v1.1 修复了 5 条红线违规）"""
        version = ack_pool.get("version", "unknown")
        assert version >= "1.1", (
            f"ack-pool.yaml 版本应为 ≥ 1.1，当前为 {version}。"
            f"请在 header 更新 version 字段。"
        )

    def test_last_verified_recent(self, ack_pool: dict) -> None:
        """last_verified 日期不应超过 90 天"""
        from datetime import date, timedelta

        last_verified_str = ack_pool.get("last_verified", "")
        if not last_verified_str:
            pytest.fail("ack-pool.yaml 必须有 last_verified 字段")

        try:
            last_verified = date.fromisoformat(last_verified_str)
        except ValueError:
            pytest.fail(f"last_verified 格式错误: {last_verified_str}，应为 YYYY-MM-DD")

        age_days = (date.today() - last_verified).days
        assert age_days <= 90, (
            f"ack-pool.yaml 未在 90 天内审查。"
            f"last_verified={last_verified_str}（{age_days} 天前），请更新。"
        )
