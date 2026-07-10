"""业务错误码常量。

真源：``docs/api/error-codes.md``（唯一人类可读字典）+ ``docs/api/openapi.yaml``
双向同步。任何新增业务码必须先在 ``error-codes.md`` 申请编号，然后同步到这里。

模块参考：``docs/spec/facts-anchor.md`` §1（M1-M11 模块，V1.3 重排）

约定：
- 以 ``E_`` 前缀标识 Error code
- UPPER_SNAKE_CASE
- ``<MODULE>_<VERB_OR_NOUN>``
- 禁止硬编码错误码字符串（CI 门禁禁止 ``app/`` 内 grep ``"E_[A-Z]"`` 除外本文件）

Sprint 0 落地：仅做骨架定义；业务模块按 Sprint 1+ 实施时增量补充。
"""

from __future__ import annotations

from enum import Enum

# ─────────────────────────────────────────────────────────────────────────────
# 1xxx 通用错误
# ─────────────────────────────────────────────────────────────────────────────
E_GENERAL_INVALID_REQUEST = "E_GENERAL_INVALID_REQUEST"
E_GENERAL_MISSING_FIELD = "E_GENERAL_MISSING_FIELD"
E_GENERAL_INVALID_FIELD = "E_GENERAL_INVALID_FIELD"
E_GENERAL_FIELD_TOO_LONG = "E_GENERAL_FIELD_TOO_LONG"
E_GENERAL_UNAUTHORIZED = "E_GENERAL_UNAUTHORIZED"
E_GENERAL_TOKEN_EXPIRED = "E_GENERAL_TOKEN_EXPIRED"
E_GENERAL_FORBIDDEN = "E_GENERAL_FORBIDDEN"
E_GENERAL_NOT_FOUND = "E_GENERAL_NOT_FOUND"
E_GENERAL_CONFLICT = "E_GENERAL_CONFLICT"
E_GENERAL_RATE_LIMIT = "E_GENERAL_RATE_LIMIT"
E_GENERAL_INTERNAL_ERROR = "E_GENERAL_INTERNAL_ERROR"
E_GENERAL_SERVICE_UNAVAILABLE = "E_GENERAL_SERVICE_UNAVAILABLE"

# ─────────────────────────────────────────────────────────────────────────────
# 2xxx 用户 / 认证错误（M1）
# ─────────────────────────────────────────────────────────────────────────────
E_USER_INVALID_INPUT = "E_USER_INVALID_INPUT"
E_USER_INVALID_ENUM = "E_USER_INVALID_ENUM"
E_AUTH_CODE_INVALID = "E_AUTH_CODE_INVALID"
E_AUTH_PHONE_CODE_INVALID = "E_AUTH_PHONE_CODE_INVALID"
E_AUTH_PHONE_CODE_EXPIRED = "E_AUTH_PHONE_CODE_EXPIRED"
E_AUTH_TOKEN_EXPIRED = "E_AUTH_TOKEN_EXPIRED"
E_AUTH_TOKEN_INVALID = "E_AUTH_TOKEN_INVALID"
E_AUTH_REFRESH_FAILED = "E_AUTH_REFRESH_FAILED"
E_USER_PUSH_CHANNEL_INVALID = "E_USER_PUSH_CHANNEL_INVALID"
E_USER_NOT_FOUND = "E_USER_NOT_FOUND"
E_USER_UNIONID_EXISTS = "E_USER_UNIONID_EXISTS"
E_AUTH_UNIONID_MISMATCH = "E_AUTH_UNIONID_MISMATCH"
E_AUTH_LOGIN_FREQUENT = "E_AUTH_LOGIN_FREQUENT"
E_USER_SMS_SEND_FREQUENT = "E_USER_SMS_SEND_FREQUENT"

# ─────────────────────────────────────────────────────────────────────────────
# 3xxx 诊断错误（M2）
# ─────────────────────────────────────────────────────────────────────────────
E_DIAGNOSIS_INVALID_INPUT = "E_DIAGNOSIS_INVALID_INPUT"
E_DIAGNOSIS_IMAGE_TOO_LARGE = "E_DIAGNOSIS_IMAGE_TOO_LARGE"
E_DIAGNOSIS_IMAGE_FORMAT_UNSUPPORTED = "E_DIAGNOSIS_IMAGE_FORMAT_UNSUPPORTED"
E_DIAGNOSIS_COMPLAINT_TOO_LONG = "E_DIAGNOSIS_COMPLAINT_TOO_LONG"
E_DIAGNOSIS_NOT_FOUND = "E_DIAGNOSIS_NOT_FOUND"
E_DIAGNOSIS_REPORT_EXPIRED = "E_DIAGNOSIS_REPORT_EXPIRED"
E_DIAGNOSIS_IN_PROGRESS = "E_DIAGNOSIS_IN_PROGRESS"
E_DIAGNOSIS_RATE_LIMIT = "E_DIAGNOSIS_RATE_LIMIT"
E_DIAGNOSIS_LLM_RATE_LIMIT = "E_DIAGNOSIS_LLM_RATE_LIMIT"
E_DIAGNOSIS_LLM_ERROR = "E_DIAGNOSIS_LLM_ERROR"
E_DIAGNOSIS_IMAGE_UPLOAD_FAILED = "E_DIAGNOSIS_IMAGE_UPLOAD_FAILED"
E_DIAGNOSIS_LLM_UNAVAILABLE = "E_DIAGNOSIS_LLM_UNAVAILABLE"
E_DIAGNOSIS_IMAGE_PROCESSING_FAILED = "E_DIAGNOSIS_IMAGE_PROCESSING_FAILED"
# PR-A1：async pipeline 状态相关错误（JobStateStore + 30min TTL + SSE keepalive）
E_DIAGNOSIS_JOB_NOT_FOUND = "E_DIAGNOSIS_JOB_NOT_FOUND"
E_DIAGNOSIS_TIMEOUT = "E_DIAGNOSIS_TIMEOUT"
E_DIAGNOSIS_PIPELINE_FAILED = "E_DIAGNOSIS_PIPELINE_FAILED"
E_DIAGNOSIS_FACE_REQUIRED = "E_DIAGNOSIS_FACE_REQUIRED"

# 4xxx 上传错误（M2 presign + 对象存储）
E_UPLOAD_INVALID_CONTENT_TYPE = "E_UPLOAD_INVALID_CONTENT_TYPE"
E_UPLOAD_INVALID_PURPOSE = "E_UPLOAD_INVALID_PURPOSE"
E_UPLOAD_PRESIGN_FAILED = "E_UPLOAD_PRESIGN_FAILED"

# ─────────────────────────────────────────────────────────────────────────────
# 4xxx 方案 / 视频错误（M3）
# ─────────────────────────────────────────────────────────────────────────────
E_PLAN_INVALID_INPUT = "E_PLAN_INVALID_INPUT"
E_PLAN_LENGTH_UNSUPPORTED = "E_PLAN_LENGTH_UNSUPPORTED"
E_PLAN_NOT_FOUND = "E_PLAN_NOT_FOUND"
E_PLAN_NO_REPORT = "E_PLAN_NO_REPORT"
E_PLAN_ALREADY_EXISTS = "E_PLAN_ALREADY_EXISTS"
E_VIDEO_INVALID_INPUT = "E_VIDEO_INVALID_INPUT"
E_VIDEO_NOT_FOUND = "E_VIDEO_NOT_FOUND"
E_PLAN_VIDEO_INACTIVE = "E_PLAN_VIDEO_INACTIVE"

# ─────────────────────────────────────────────────────────────────────────────
# 5xxx 打卡错误（M4）
# ─────────────────────────────────────────────────────────────────────────────
E_CHECKIN_INVALID_INPUT = "E_CHECKIN_INVALID_INPUT"
E_CHECKIN_FEELING_TOO_LONG = "E_CHECKIN_FEELING_TOO_LONG"
E_CHECKIN_DAY_INVALID = "E_CHECKIN_DAY_INVALID"
E_CHECKIN_PLAN_NOT_FOUND = "E_CHECKIN_PLAN_NOT_FOUND"
E_CHECKIN_VIDEO_NOT_FOUND = "E_CHECKIN_VIDEO_NOT_FOUND"
E_CHECKIN_DUPLICATE = "E_CHECKIN_DUPLICATE"
E_CHECKIN_DAY_COMPLETED = "E_CHECKIN_DAY_COMPLETED"
E_CHECKIN_RATE_LIMIT = "E_CHECKIN_RATE_LIMIT"

# ─────────────────────────────────────────────────────────────────────────────
# 6xxx 社区错误（M6）
# ─────────────────────────────────────────────────────────────────────────────
E_COMMUNITY_INVALID_INPUT = "E_COMMUNITY_INVALID_INPUT"
E_COMMUNITY_CONTENT_TOO_LONG = "E_COMMUNITY_CONTENT_TOO_LONG"
E_COMMUNITY_IMAGES_TOO_MANY = "E_COMMUNITY_IMAGES_TOO_MANY"
E_COMMUNITY_IMAGE_TOO_LARGE = "E_COMMUNITY_IMAGE_TOO_LARGE"
E_COMMUNITY_POST_NOT_FOUND = "E_COMMUNITY_POST_NOT_FOUND"
E_COMMUNITY_POST_PENDING = "E_COMMUNITY_POST_PENDING"
E_COMMUNITY_POST_REJECTED = "E_COMMUNITY_POST_REJECTED"
E_COMMUNITY_LIKE_DUPLICATE = "E_COMMUNITY_LIKE_DUPLICATE"
E_COMMUNITY_POST_FREQUENT = "E_COMMUNITY_POST_FREQUENT"
E_COMMUNITY_RATE_LIMIT = "E_COMMUNITY_RATE_LIMIT"

# ─────────────────────────────────────────────────────────────────────────────
# 7xxx 视频错误（M3 扩展）
# ─────────────────────────────────────────────────────────────────────────────
E_VIDEO_SEARCH_PARAMS_INVALID = "E_VIDEO_SEARCH_PARAMS_INVALID"
E_VIDEO_DIFFICULTY_INVALID = "E_VIDEO_DIFFICULTY_INVALID"
E_VIDEO_INACTIVE = "E_VIDEO_INACTIVE"
E_VIDEO_RECOMMEND_FAILED = "E_VIDEO_RECOMMEND_FAILED"

# ─────────────────────────────────────────────────────────────────────────────
# 8xxx 推送 / 通知错误（M9）
# ─────────────────────────────────────────────────────────────────────────────
E_NOTIFICATION_INVALID_CHANNEL = "E_NOTIFICATION_INVALID_CHANNEL"
E_NOTIFICATION_TOKEN_INVALID = "E_NOTIFICATION_TOKEN_INVALID"
E_NOTIFICATION_TYPE_INVALID = "E_NOTIFICATION_TYPE_INVALID"
E_NOTIFICATION_NOT_FOUND = "E_NOTIFICATION_NOT_FOUND"
E_NOTIFICATION_SUBSCRIBED = "E_NOTIFICATION_SUBSCRIBED"
E_NOTIFICATION_SUBSCRIBE_FREQUENT = "E_NOTIFICATION_SUBSCRIBE_FREQUENT"
E_NOTIFICATION_WX_SUBSCRIBE_FAILED = "E_NOTIFICATION_WX_SUBSCRIBE_FAILED"
E_NOTIFICATION_APNS_FAILED = "E_NOTIFICATION_APNS_FAILED"
E_NOTIFICATION_FCM_FAILED = "E_NOTIFICATION_FCM_FAILED"
E_NOTIFICATION_EMAIL_FAILED = "E_NOTIFICATION_EMAIL_FAILED"

# ─────────────────────────────────────────────────────────────────────────────
# 9xxx 合规 / 安全错误
# ─────────────────────────────────────────────────────────────────────────────
E_COMPLIANCE_CONTENT_BLOCKED = "E_COMPLIANCE_CONTENT_BLOCKED"
E_COMPLIANCE_MEDICAL_CLAIM = "E_COMPLIANCE_MEDICAL_CLAIM"
E_COMPLIANCE_EFFICACY_CLAIM = "E_COMPLIANCE_EFFICACY_CLAIM"
E_COMPLIANCE_APPEARANCE_ANXIETY = "E_COMPLIANCE_APPEARANCE_ANXIETY"
E_COMPLIANCE_USER_BLOCKED = "E_COMPLIANCE_USER_BLOCKED"
E_COMPLIANCE_IP_BLOCKED = "E_COMPLIANCE_IP_BLOCKED"
E_COMPLIANCE_RATE_LIMIT = "E_COMPLIANCE_RATE_LIMIT"
E_COMPLIANCE_CHECK_FAILED = "E_COMPLIANCE_CHECK_FAILED"
E_COMPLIANCE_ENGINE_ERROR = "E_COMPLIANCE_ENGINE_ERROR"

# ─────────────────────────────────────────────────────────────────────────────
# 10xxx 智能管家助理错误（M5）
# ─────────────────────────────────────────────────────────────────────────────
E_ASSISTANT_MESSAGE_INVALID = "E_ASSISTANT_MESSAGE_INVALID"
E_ASSISTANT_MESSAGE_TOO_LONG = "E_ASSISTANT_MESSAGE_TOO_LONG"
E_ASSISTANT_FORBIDDEN_CALLER = "E_ASSISTANT_FORBIDDEN_CALLER"
E_ASSISTANT_RATE_LIMIT = "E_ASSISTANT_RATE_LIMIT"
E_ASSISTANT_MEDICAL_REJECT = "E_ASSISTANT_MEDICAL_REJECT"
E_ASSISTANT_LLM_ERROR = "E_ASSISTANT_LLM_ERROR"
E_ASSISTANT_SESSION_NOT_FOUND = "E_ASSISTANT_SESSION_NOT_FOUND"
E_ASSISTANT_SESSION_CLOSED = "E_ASSISTANT_SESSION_CLOSED"

# ─────────────────────────────────────────────────────────────────────────────
# 11xxx 反馈错误（M7 · 心情日记 / 多部位反馈）
# ─────────────────────────────────────────────────────────────────────────────
E_FEEDBACK_INVALID_TYPE = "E_FEEDBACK_INVALID_TYPE"
E_FEEDBACK_TEXT_TOO_LONG = "E_FEEDBACK_TEXT_TOO_LONG"
E_FEEDBACK_PHOTO_URL_REQUIRED = "E_FEEDBACK_PHOTO_URL_REQUIRED"
E_FEEDBACK_BODY_PART_REQUIRED = "E_FEEDBACK_BODY_PART_REQUIRED"
E_FEEDBACK_PAYLOAD_MISMATCH = "E_FEEDBACK_PAYLOAD_MISMATCH"
E_FEEDBACK_PHOTO_TOO_LARGE = "E_FEEDBACK_PHOTO_TOO_LARGE"
E_FEEDBACK_DAILY_LIMIT = "E_FEEDBACK_DAILY_LIMIT"

# ─────────────────────────────────────────────────────────────────────────────
# 12xxx 主动回忆错误（M8）
# ─────────────────────────────────────────────────────────────────────────────
E_RECALL_EMPTY = "E_RECALL_EMPTY"
E_RECALL_LLM_ERROR = "E_RECALL_LLM_ERROR"
E_RECALL_NOT_FOUND = "E_RECALL_NOT_FOUND"
E_RECALL_SAFETY_BLOCKED = "E_RECALL_SAFETY_BLOCKED"
E_RECALL_DAILY_LIMIT = "E_RECALL_DAILY_LIMIT"

# ─────────────────────────────────────────────────────────────────────────────
# 13xxx 分享错误（M10 · 抱抱卡 / 分享海报）
# ─────────────────────────────────────────────────────────────────────────────
E_SHARE_TEMPLATE_INVALID = "E_SHARE_TEMPLATE_INVALID"
E_SHARE_RENDER_FAILED = "E_SHARE_RENDER_FAILED"
E_SHARE_PLAN_NOT_FOUND = "E_SHARE_PLAN_NOT_FOUND"


# ─────────────────────────────────────────────────────────────────────────────
# §类别枚举（v4.1-prep 子任务 4 · envelope 分级)
# ─────────────────────────────────────────────────────────────────────────────
class CodeCategory(str, Enum):
    """业务码分级枚举（与 error-codes.md 段落标识对齐）。

    设计要点：
    - 字符串值与字典前缀一致，便于 O(1) 字符串映射
    - 与 envelope 集成：``GROUP_BY_CATEGORY[category]`` 可直接喂给测试做参数化
    """

    GENERAL = "1xxx"        # 通用错误
    USER_AUTH = "2xxx"      # 用户 / 认证
    DIAGNOSIS = "3xxx"      # 诊断
    UPLOAD = "4xxx-up"      # 上传 / presign
    PLAN_VIDEO = "4xxx-pv"  # 方案 / 视频（4xxx 段共用）
    CHECKIN = "5xxx"        # 打卡
    COMMUNITY = "6xxx"      # 社区
    VIDEO = "7xxx"          # 视频推荐
    NOTIFICATION = "8xxx"   # 推送 / 通知
    COMPLIANCE = "9xxx"     # 合规 / 安全
    ASSISTANT = "10xxx"     # 智能管家助理
    FEEDBACK = "11xxx"      # 反馈
    RECALL = "12xxx"        # 主动回忆
    SHARE = "13xxx"         # 分享


def _category_of(code: str) -> CodeCategory:
    """根据 E_CODE 字符串前缀决定分类（详情见 v4.1-prep/04-error-envelope.md §4）。"""
    if code.startswith("E_UPLOAD_"):
        return CodeCategory.UPLOAD
    if code.startswith("E_PLAN_") or code.startswith("E_VIDEO_"):
        return CodeCategory.PLAN_VIDEO
    bucket = code.split("_", 1)[1][:4] if "_" in code else ""
    return {
        "GENE": CodeCategory.GENERAL,
        "USER": CodeCategory.USER_AUTH,
        "AUTH": CodeCategory.USER_AUTH,
        "DIAG": CodeCategory.DIAGNOSIS,
        "CHEC": CodeCategory.CHECKIN,
        "COMM": CodeCategory.COMMUNITY,
        "VIDE": CodeCategory.VIDEO,
        "NOTI": CodeCategory.NOTIFICATION,
        "COMP": CodeCategory.COMPLIANCE,
        "ASSI": CodeCategory.ASSISTANT,
        "FEED": CodeCategory.FEEDBACK,
        "RECA": CodeCategory.RECALL,
        "SHAR": CodeCategory.SHARE,
    }.get(bucket, CodeCategory.GENERAL)


def build_group_by_category() -> dict[CodeCategory, list[str]]:
    """扫描模块内所有 ``E_*`` 字符串常量并按 ``CodeCategory`` 分组。

    出参：``{CodeCategory: [code1, code2, ...]}``；不含空分类。
    使用样例：``>>> GROUP_BY_CATEGORY[CodeCategory.GENERAL][0] == 'E_GENERAL_INVALID_REQUEST'``。
    实现要点：直接扫描``globals()``，避免对``__all__``的循环依赖。
    """
    out: dict[CodeCategory, list[str]] = {}
    for _name, value in globals().items():
        if not (isinstance(value, str) and value.startswith("E_")):
            continue
        cat = _category_of(value)
        out.setdefault(cat, []).append(value)
    return {k: v for k, v in out.items() if v}


# 启动期一次性算好，避免每次枚举重复扫描
GROUP_BY_CATEGORY: dict[CodeCategory, list[str]] = build_group_by_category()


__all__: list[str] = [
    name
    for name, value in globals().items()
    if not name.startswith("_") and isinstance(value, str) and value.startswith("E_")
] + ["CodeCategory", "GROUP_BY_CATEGORY", "build_group_by_category", "_category_of"]
