"""ComplianceChecker — 合规检查器

位置：backend/app/services/compliance/checker.py（V1.3 重构后单一布局）

演进路线：
- W1 阶段：骨架实现，仅关键词匹配（当前）
- W2 阶段：接入 LLM 做语义级检测
- W3 阶段：接入 recall-forbidden-words.yaml + ack-pool.yaml 共享词库

实际实现后替换本文件，并确保 backend/tests/intercept/ 下的 Golden Set 100% 通过。
"""

from typing import Literal

Severity = Literal["critical", "warning", "normal"]


def check_input(text: str) -> dict[str, bool | Severity | list[str]]:
    """检查用户输入是否违规。

    Args:
        text: 用户输入文本

    Returns:
        {
            "blocked": bool,      # True = 拦截
            "severity": Severity, # critical / warning / normal
            "matches": list[str], # 命中的关键词（调试用）
        }

    """
    critical_keywords = [
        "治疗",
        "治愈",
        "治病",
        "处方",
        "医生",
        "医院",
        "开药",
        "开点药",
        "微整",
        "整形",
        "打针",
        "玻尿酸",
        "瘦脸针",
        "超声刀",
        "热玛吉",
        "几分",
        "颜值",
        "几天见效",
        "几天能见效",
        "一定",
        "一定变白",
        "保证",
        "保证有效",
        "永久",
        "复发",
        "根治",
        "瘦下来",
        "脸变小",
    ]
    matched = [kw for kw in critical_keywords if kw in text]
    if matched:
        result: dict[str, bool | Severity | list[str]] = {
            "blocked": True,
            "severity": "critical",
            "matches": matched,
        }
        return result
    return {"blocked": False, "severity": "normal", "matches": []}


def check_output(text: str) -> dict[str, bool | Severity | list[str]]:
    """检查 LLM 输出（诊断报告 / 督促话术 / 抱抱卡文案）是否违规。

    Args:
        text: LLM 生成的文本

    Returns:
        {
            "blocked": bool,
            "severity": Severity,
            "matches": list[str],
        }

    """
    critical_keywords = [
        "治疗",
        "治愈",
        "治病",
        "处方",
        "微整",
        "整形",
        "打针",
        "玻尿酸",
        "瘦脸针",
        "永久",
        "复发",
        "根治",
        "保证",
        "治好",
        "变白",
        "瘦下来",
        "脸变小",
    ]
    warning_keywords = [
        "几天见效",
        "一定变白",
        "保证有效",
        "最好",
        "唯一",
        "见效",
        "好一些",
        "同类最好",
    ]
    matched_critical = [kw for kw in critical_keywords if kw in text]
    matched_warning = [kw for kw in warning_keywords if kw in text]

    if matched_critical:
        return {"blocked": True, "severity": "critical", "matches": matched_critical}
    if matched_warning:
        return {"blocked": False, "severity": "warning", "matches": matched_warning}
    return {"blocked": False, "severity": "normal", "matches": []}
