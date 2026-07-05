"""Golden Set — 输出检测测试（test_output.py）

测试场景：LLM 输出 → ComplianceChecker.check_output()
期望：LLM 生成的报告/话术/抱抱卡文案不出现违规内容。

运行：
    pytest backend/tests/intercept/test_output.py -v

通过标准：
    - 医疗/医美类关键词：0 出现（block）
    - 承诺效果类：0 出现（block）
    - 正常表达：通过（pass）
    任意一项不达标 → 测试失败 → 阻塞合入

注：本文件原位于 ``backend/app/services/compliance/tests/``，2026-07-04 迁至
``backend/tests/intercept/``，与业务路由回归（``backend/eval/``）严格分家。
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from backend.services.compliance.checker import check_output


# ─────────────────────────────────────────────────────────────────────────────
# Case 定义
# ─────────────────────────────────────────────────────────────────────────────

# LLM 诊断报告输出 case
REPORT_CASES = [
    pytest.param(
        "G-R-01",
        "基于你的肩颈状态，推荐每天做2-3次肩颈拉伸训练，每次5分钟。",
        "pass",
        id="G-R-01 合规报告-肩颈拉伸",
    ),
    pytest.param(
        "G-R-02",
        "你的发梢略干涩，推荐参考B站这条护发教程，每天轻柔按摩头皮1-2分钟。",
        "pass",
        id="G-R-02 合规报告-护发教程",
    ),
    pytest.param(
        "G-R-03",
        "侧颈前伸建议每2小时做1次收下巴训练，参考这个动作。",
        "pass",
        id="G-R-03 合规报告-收下巴",
    ),
    pytest.param(
        "G-R-04",
        "面部气色偏暗沉，可以尝试每天早起做5分钟面部按摩，配合良好作息。",
        "pass",
        id="G-R-04 合规报告-面部气色",
    ),
    pytest.param(
        "G-R-05",
        "久坐腰酸建议每45分钟起来活动1-2分钟，拉伸下背部。",
        "pass",
        id="G-R-05 合规报告-久坐腰酸",
    ),
    pytest.param(
        "G-R-06",
        "你的皮肤问题需要接受医学治疗才能根治。",
        "block",
        id="G-R-06 违规报告-治疗根治",
    ),
    pytest.param(
        "G-R-07",
        "坚持21天一定能让你的面部皮肤变白。",
        "block",
        id="G-R-07 违规报告-功效承诺",
    ),
    pytest.param(
        "G-R-08",
        "这套动作能彻底治愈你的肩颈问题，永不复发。",
        "block",
        id="G-R-08 违规报告-治愈承诺",
    ),
    pytest.param(
        "G-R-09",
        "建议你去医院开点药，配合微整形效果更好。",
        "block",
        id="G-R-09 违规报告-医院+医美",
    ),
    pytest.param(
        "G-R-10",
        "面部轮廓需要打瘦脸针才能达到最佳效果。",
        "block",
        id="G-R-10 违规报告-瘦脸针",
    ),
]

# AI 督促话术 case
SCRIPT_CASES = [
    pytest.param(
        "G-S-01", "今天练完了，你真的棒。我们明天见。", "pass",
        id="G-S-01 合规话术-鼓励",
    ),
    pytest.param(
        "G-S-02", "今天累了就休息，明天的你还在这里。", "pass",
        id="G-S-02 合规话术-休息",
    ),
    pytest.param(
        "G-S-03", "想休息一天也可以，先把今天的你抱抱。我们慢慢来。", "pass",
        id="G-S-03 合规话术-接纳",
    ),
    pytest.param(
        "G-S-04", "今天完成了 1 个动作，已坚持 3 天，真的很棒。", "pass",
        id="G-S-04 合规话术-坚持",
    ),
    pytest.param(
        "G-S-05", "明天见，记得照顾好自己。", "pass",
        id="G-S-05 合规话术-温柔",
    ),
    pytest.param(
        "G-S-06", "坚持 7 天保证你的肩颈问题彻底消失。", "block",
        id="G-S-06 违规话术-保证消失",
    ),
    pytest.param(
        "G-S-07", "这是最好的治愈方案，永久有效。", "block",
        id="G-S-07 违规话术-永久有效",
    ),
]

# 抱抱卡文案 case
CARD_CASES = [
    pytest.param(
        "G-C-01", "我愿意慢慢来 🌿", "pass",
        id="G-C-01 合规卡片-慢来",
    ),
    pytest.param(
        "G-C-02", "坚持了 7 天，你比自己想象的更棒。", "pass",
        id="G-C-02 合规卡片-鼓励",
    ),
    pytest.param(
        "G-C-03", "21 天的你，正在变好。", "pass",
        id="G-C-03 合规卡片-变好",
    ),
    pytest.param(
        "G-C-04", "每一天都在进步，慢慢来，比较快。", "pass",
        id="G-C-04 合规卡片-进步",
    ),
    pytest.param(
        "G-C-05", "7 天打卡完成，你的脸变小了 3 厘米！", "block",
        id="G-C-05 违规卡片-量化承诺",
    ),
    pytest.param(
        "G-C-06", "坚持 21 天保证治好你的肩颈问题！", "block",
        id="G-C-06 违规卡片-治好承诺",
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# 参数化测试
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("case_id,text,expected", REPORT_CASES + SCRIPT_CASES + CARD_CASES)
def test_llm_output_compliance(case_id: str, text: str, expected: str) -> None:
    """所有 LLM 生成的输出（报告/话术/卡片）必须合规。"""
    result = check_output(text)
    if expected == "block":
        assert result["blocked"], \
            f"[{case_id}] 输出未被拦截（期望 block）：{text}"
        assert result.get("severity") == "critical", \
            f"[{case_id}] 严重违规输出仅被 warn 而非 block：{text}"
    else:
        assert not result["blocked"], \
            f"[{case_id}] 合规输出被错误拦截（期望 pass）：{text}"


# ─────────────────────────────────────────────────────────────────────────────
# 回归测试：防止 case 被意外放行
# ─────────────────────────────────────────────────────────────────────────────

ALL_CASES: list[Any] = REPORT_CASES + SCRIPT_CASES + CARD_CASES

def test_no_regression_on_known_clean() -> None:
    """已知合规输出（expected=pass）不会被意外放行为 block 之外的状态。"""
    for entry in ALL_CASES:
        case_id, text, expected = cast(tuple[str, str, str], tuple(entry.values))
        if expected != "pass":
            continue
        result = check_output(text)
        assert not result["blocked"], \
            f"回归失败（误杀）[{case_id}]：{text}"


def test_no_regression_on_known_bad() -> None:
    """已知违规输出（expected=block）不会被漏过。"""
    for entry in ALL_CASES:
        case_id, text, expected = cast(tuple[str, str, str], tuple(entry.values))
        if expected != "block":
            continue
        result = check_output(text)
        assert result["blocked"], \
            f"回归失败（漏过）[{case_id}]：{text}"
        assert result.get("severity") == "critical", \
            f"回归失败（级别错误）[{case_id}]：{text}"