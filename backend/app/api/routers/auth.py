"""微信小程序登录（Sprint 1 M1）。

真源：``docs/spec/SPEC-M1-wechat-login.md``。

流程：``wx.login()`` code → code2session(openid) → 查询/创建 user → JWT。

业务逻辑下沉到 ``app.services.auth.wx_login_service.login_via_wx``，
本路由只做：参数校验 + 异常 → HTTP 状态码映射 + 响应序列化。

无状态接口，所有上下文由 JWT 承载。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import SelfwellError, UserInputError
from app.core.log import logger
from app.db.session import get_session
from app.errors.codes import E_GENERAL_INTERNAL_ERROR
from app.services.auth.wx_login_service import WxLoginError, login_via_wx


# ─────────────────────────────────────────────────────────────────────────────
# §一 Schema
# ─────────────────────────────────────────────────────────────────────────────
class WxLoginRequest(BaseModel):
    """微信小程序登录请求。

    小程序前端调用 ``wx.login()`` 后，将返回的 code 发送至此接口。
    """

    code: str = Field(..., min_length=10, max_length=64, description="wx.login() 返回的 code")


class WxLoginResponse(BaseModel):
    """登录成功响应。"""

    access_token: str = Field(..., description="JWT access token")
    user_id: str = Field(..., description="用户 UUID（sub claim）")
    is_new_user: bool = Field(default=False, description="是否新注册用户")
    user_status: str = Field(default="draft", description="用户状态 draft / active")


# ─────────────────────────────────────────────────────────────────────────────
# §二 路由
# ─────────────────────────────────────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/wx-login",
    response_model=WxLoginResponse,
    summary="微信小程序登录（code 换 openid → JWT）",
)
async def wx_login(
    body: WxLoginRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> WxLoginResponse:
    """微信小程序登录。委托给 ``wx_login_service.login_via_wx``。

    Returns:
        ``WxLoginResponse`` 含 JWT 与 user_id。

    Raises:
        400: ``code`` 缺失或过短。
        401: 微信 code 无效 / unionid mismatch。
        500: 内部错误。

    """
    try:
        user_id, token, is_new, user_status, _expires_in = await login_via_wx(
            session, code=body.code, client="wx_mp"
        )
    except UserInputError as exc:
        # service 抛的 code 长度校验
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.message_zh},
        ) from exc
    except WxLoginError as exc:
        # 微信侧错误（401/502/504 等），透传 http_status
        logger.warning(
            "wx_login_service_error",
            code=body.code[:8],
            err_code=exc.code,
            http_status=exc.http_status,
        )
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    except SelfwellError as exc:
        # 兜底：service 其它业务异常
        logger.exception("wx_login_selfwell_error", code=body.code[:8])
        raise HTTPException(
            status_code=exc.http_status,
            detail={"code": exc.code, "message_zh": exc.render_zh()},
        ) from exc
    except Exception:
        logger.exception("wx_login_unexpected_error", code=body.code[:8])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": E_GENERAL_INTERNAL_ERROR,
                "message_zh": "登录失败，请稍后重试",
            },
        ) from None

    logger.info("wx_login_success", user_id=user_id, is_new=is_new)
    return WxLoginResponse(
        access_token=token,
        user_id=user_id,
        is_new_user=is_new,
        user_status=user_status,
    )


__all__ = ["router"]
