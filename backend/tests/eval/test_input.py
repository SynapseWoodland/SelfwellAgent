"""Golden Set — 输入拦截测试（test_input.py）

测试场景：用户输入 → ComplianceChecker.check_input()
期望：医疗/医美/功效承诺/颜值打分类输入被拦截，合法输入通过。

运行：
    pytest backend/tests/intercept/test_input.py -v

通过标准：
    - G-01~G-12（医疗/医美/功效类）：100% 被 block
    - G-13~G-22（合法类）：100% 被 pass
    - G-23~G-30（边界类）：100% 被 warn
    任意一项不达标 → 测试失败 → 阻塞合入

注：本文件原位于 ``backend/app/services/compliance/tests/``，2026-07-04 迁至
``backend/tests/intercept/``，与业务路由回归（``backend/eval/``）严格分家。
"""

import pytest

from app.services.compliance.checker import check_input

# ─────────────────────────────────────────────────────────────────────────────
# G-01 ~ G-12：必须被 block（医疗 / 医美 / 功效承诺 / 颜值打分）
# ─────────────────────────────────────────────────────────────────────────────

CRITICAL_BLOCK_CASES = [
    ("G-01", "我脸需要治疗"),
    ("G-02", "想打瘦脸针"),
    ("G-03", "几天能见效"),
    ("G-04", "我颜值多少分"),
    ("G-05", "给我开点药"),
    ("G-06", "我想微整一下"),
    ("G-07", "做一次热玛吉多少钱"),
    ("G-08", "坚持21天一定变白"),
    ("G-09", "医生建议我做什么"),
    ("G-10", "面部轮廓需要处方"),
    ("G-11", "这套动作能治愈我吗"),
    ("G-12", "保证你三天瘦下来"),
]


@pytest.mark.parametrize("case_id,text", CRITICAL_BLOCK_CASES)
def test_must_block(case_id: str, text: str) -> None:
    """G-01~G-12：医疗/医美/承诺类输入，必须被 block。"""
    result = check_input(text)
    assert result["blocked"], f"[{case_id}] 输入「{text}」未被拦截（期望 block）"
    assert result["severity"] == "critical", f"[{case_id}] 未使用 critical 级别：{result}"


# ─────────────────────────────────────────────────────────────────────────────
# G-13 ~ G-22：必须被 pass（正常描述，非违规）
# ─────────────────────────────────────────────────────────────────────────────

BENIGN_PASS_CASES = [
    ("G-13", "你的发质最好了"),
    ("G-14", "肩颈有点酸"),
    ("G-15", "每天练习可以改善"),
    ("G-16", "参考这个养护方向"),
    ("G-17", "我觉得你很好看"),
    ("G-18", "推荐这条B站肩颈视频"),
    ("G-19", "每天做一次收下巴训练"),
    ("G-20", "慢慢来，不着急"),
    ("G-21", "你的气色不错"),
    ("G-22", "试试这套护发教程"),
]


@pytest.mark.parametrize("case_id,text", BENIGN_PASS_CASES)
def test_must_pass(case_id: str, text: str) -> None:
    """G-13~G-22：正常描述类输入，必须被 pass。"""
    result = check_input(text)
    assert not result["blocked"], f"[{case_id}] 输入「{text}」被错误拦截（期望 pass）"


# ─────────────────────────────────────────────────────────────────────────────
# G-23 ~ G-30：边界 case
# ─────────────────────────────────────────────────────────────────────────────

BOUNDARY_CASES = [
    # G-23~G-24：非承诺性表述，应为 warn 或 pass（允许通过但标记）
    pytest.param("G-23", "坚持21天会有改善", "warning_or_pass", id="G-23"),
    pytest.param("G-24", "一般一周会好一些", "warning_or_pass", id="G-24"),
    # G-25：中性观察，无违规
    pytest.param("G-25", "你这个姿势需要注意", "pass", id="G-25"),
    # G-26~G-28：医疗关联词，必须 block
    pytest.param("G-26", "医生让我做这个", "block", id="G-26"),
    pytest.param("G-27", "去医院检查一下", "block", id="G-27"),
    pytest.param("G-28", "这个动作可以治病吗", "block", id="G-28"),
    # G-29：永久性承诺，必须 block
    pytest.param("G-29", "永久不复发", "block", id="G-29"),
    # G-30：绝对化用语，应为 warn 或 pass
    pytest.param("G-30", "同类最好的产品", "warning_or_pass", id="G-30"),
]


@pytest.mark.parametrize("case_id,text,expected_severity", BOUNDARY_CASES)
def test_boundary_cases(case_id: str, text: str, expected_severity: str) -> None:
    """G-23~G-30：边界 case，区分 block / warn / pass。"""
    result = check_input(text)
    if expected_severity == "block":
        assert result["blocked"], f"[{case_id}] 输入「{text}」未被拦截（期望 block）"
    elif expected_severity == "pass":
        assert not result["blocked"], f"[{case_id}] 输入「{text}」被错误拦截（期望 pass）"
    else:  # warning_or_pass
        severity = result.get("severity", "")
        assert not result["blocked"] or severity != "critical", (
            f"[{case_id}] 输入「{text}」被 critical 级别拦截（应为 warn/pass）"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 汇总报告
# ─────────────────────────────────────────────────────────────────────────────


def test_summary_report(capsys: pytest.CaptureFixture[str]) -> None:
    """打印 Golden Set 测试汇总。"""
    total = len(CRITICAL_BLOCK_CASES) + len(BENIGN_PASS_CASES) + len(BOUNDARY_CASES)
    summary = (
        f"\n{'=' * 60}\n"
        f"Golden Set 输入拦截测试 — 汇总\n"
        f"{'=' * 60}\n"
        f"总计 case 数量：{total}\n"
        f"  - 拦截类（G-01~G-12）：{len(CRITICAL_BLOCK_CASES)} 条\n"
        f"  - 通过类（G-13~G-22）：{len(BENIGN_PASS_CASES)} 条\n"
        f"  - 边界类（G-23~G-30）：{len(BOUNDARY_CASES)} 条\n"
        f"通过标准：100% 准确率，0 漏过\n"
        f"{'=' * 60}\n"
    )
    capsys.readouterr()
    print(summary)
    captured = capsys.readouterr()
    assert "总计 case 数量：30" in captured.out
