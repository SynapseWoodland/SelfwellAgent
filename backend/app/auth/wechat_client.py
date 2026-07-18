"""微信客户端（httpx 异步实现 · Sprint 0 骨架）。

真源：``docs/spec/TDS-M1-wechat-login.md`` + ``.env`` WX_MP_APPID/SECRET。
httpx ≥ 0.27.0 已在 pyproject.toml 声明。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from app.conf.app_config import app_config
from app.core.errors import SelfwellError
from app.core.retry import async_retry

if TYPE_CHECKING:
    pass


class WeChatClientError(SelfwellError):
    """微信侧业务错误（4xx）。"""

    code: str = "E_AUTH_CODE_INVALID"
    message_zh: str = "微信授权码无效或已过期"
    message_en: str = "WeChat auth code invalid or expired"
    severity = "USER_ERROR"
    http_status = 401


# ─────────────────────────────────────────────────────────────────────────────
# §一 jscode2session（Sprint 0 仅签名）
# ─────────────────────────────────────────────────────────────────────────────
class WeChatClient:
    """微信 API 客户端（httpx）。"""

    JSC2S_URL = "https://api.weixin.qq.com/sns/jscode2session"

    def __init__(
        self,
        *,
        mp_appid: str | None = None,
        mp_secret: str | None = None,
        timeout_sec: float = 8.0,
    ) -> None:
        self._appid = mp_appid or app_config.wechat.mp_appid
        self._secret = mp_secret or app_config.wechat.mp_secret
        self._timeout = timeout_sec

    @async_retry(attempts=3)
    async def code2session(self, js_code: str) -> dict[str, str]:
        """调用 ``jscode2session`` 换取 ``openid`` + ``session_key`` + ``unionid``。

        Returns:
            ``{"openid": ..., "session_key": ..., "unionid": ...}`` —— unionid 可能缺失。

        Raises:
            WeChatClientError: 微信侧 errcode != 0。

        """
        import httpx

        params = {
            "appid": self._appid,
            "secret": self._secret,
            "js_code": js_code,
            "grant_type": "authorization_code",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(self.JSC2S_URL, params=params)
                data: dict[str, object] = resp.json()
        except httpx.TimeoutException as exc:
            raise WeChatClientError(
                "微信接口调用超时",
                code="E_AUTH_CODE_INVALID",
                http_status=504,
            ) from exc
        except httpx.HTTPError as exc:
            raise WeChatClientError(
                "微信接口调用失败",
                code="E_AUTH_CODE_INVALID",
                http_status=502,
            ) from exc

        errcode_raw = data.get("errcode")
        errcode: int | None = int(cast(int | str, errcode_raw)) if errcode_raw is not None else None
        if errcode is not None and errcode != 0:
            errmsg: str = str(data.get("errmsg", "微信授权失败"))
            raise WeChatClientError(
                f"微信授权失败：{errmsg}",
                code="E_AUTH_CODE_INVALID",
                http_status=401,
            )

        result: dict[str, str] = {}
        for key in ("openid", "session_key", "unionid"):
            if key in data:
                result[key] = str(data[key])
        return result
