"""微信订阅消息通道（Sprint 1 M4）。

真源：``docs/spec/facts-anchor.md`` §8 + ``.env`` WX_MP_TEMPLATE_ID。
接入微信 ``cgi-bin/message/template/send`` 接口。
"""

from __future__ import annotations

from typing import cast

from app.notification.base import NotificationChannel


class WxSubscribeChannel(NotificationChannel):
    """微信小程序订阅消息（``wx.requestSubscribeMessage`` 后端落地）。

    Keyword 映射规则（MVP）：
        target      → touser（用户 openid）
        title       → keyword1（打卡名称）
        body        → keyword2（任务说明）  # 格式：time1|time2|thing1|phrase1
        trace_id    → 日志 trace 关联

    注意：发送前需要用户已在小程序内授权订阅（前端调 wx.requestSubscribeMessage），
    后端只负责发送，不负责拉起授权弹窗。
    """

    channel_name = "wx_subscribe"

    def __init__(
        self,
        mp_appid: str = "",
        mp_secret: str = "",
        template_id: str = "",
        template_keywords: str = "",
    ) -> None:
        self._mp_appid = mp_appid
        self._mp_secret = mp_secret
        self._template_id = template_id
        self._template_keywords = template_keywords.split("|") if template_keywords else []

    async def send(
        self,
        *,
        target: str,
        title: str,
        body: str,
        trace_id: str | None = None,
    ) -> bool:
        """发送微信订阅消息。

        Args:
            target: 用户 openid（touser）
            title: 模板关键词 1 值（如「每日自我关怀打卡」）
            body: 后续关键词值，格式 ``value1|value2|value3``（与 WX_MP_TEMPLATE_KEYWORDS 对齐）
            trace_id: 日志 trace 关联

        Returns:
            True = 发送成功（微信返回 errcode == 0）
            False = 发送失败

        Raises:
            NotImplementedError: 内部配置未就绪时。

        """
        import httpx

        from app.conf.app_config import app_config
        from app.core.log import logger

        # 配置优先级：构造参数 > app_config
        appid = self._mp_appid or app_config.wechat.mp_appid
        secret = self._mp_secret or app_config.wechat.mp_secret
        template_id = self._template_id or app_config.wechat.mp_template_id
        keywords = self._template_keywords

        if not all([appid, secret, template_id]):
            logger.error(
                "wx_subscribe_config_incomplete",
                has_appid=bool(appid),
                has_secret=bool(secret),
                has_template=bool(template_id),
            )
            raise NotImplementedError(
                "WxSubscribeChannel.send：WX_MP 配置未就绪（APPID/SECRET/TEMPLATE_ID）"
            )

        # 1. 获取 access_token
        token = await _get_access_token(appid, secret)
        if not token:
            logger.error("wx_subscribe_token_failed", target=target[:12] if target else "")
            return False

        # 2. 构建 data 字段（按关键词顺序填充）
        parts = body.split("|") if body else []
        data: dict[str, dict[str, str]] = {}
        for i, kw in enumerate(keywords[:4]):  # 最多 4 个关键词
            value = parts[i] if i < len(parts) else ""
            data[kw] = {"value": value}

        # keyword1 用 title 填充（打卡名称）
        if keywords and title:
            data[keywords[0]] = {"value": title}

        # 3. 调用发送接口
        send_url = "https://api.weixin.qq.com/cgi-bin/message/template/send"
        payload: dict[str, object] = {
            "touser": target,
            "template_id": template_id,
            "data": data,
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"{send_url}?access_token={token}",
                    json=payload,
                )
                result: dict[str, object] = resp.json()
        except httpx.HTTPError:
            logger.exception(
                "wx_subscribe_send_http_error",
                target=target[:12],
                trace_id=trace_id,
            )
            return False

        errcode_raw = result.get("errcode")
        errcode: int | None = int(cast(int | str, errcode_raw)) if errcode_raw is not None else None
        if errcode == 0:
            logger.info(
                "wx_subscribe_sent",
                target=target[:12],
                msgid=result.get("msgid"),
                trace_id=trace_id,
            )
            return True
        logger.warning(
            "wx_subscribe_send_failed",
            errcode=errcode,
            errmsg=result.get("errmsg", ""),
            target=target[:12],
            trace_id=trace_id,
        )
        return False


async def _get_access_token(appid: str, secret: str) -> str | None:
    """调用微信接口获取 access_token（有效期 2 小时）。

    内部维护一个简单缓存（TODO：生产环境应替换为 Redis 缓存，TTL=7200s）。
    """
    import httpx

    from app.core.log import logger

    url = "https://api.weixin.qq.com/cgi-bin/token"
    params = {"appid": appid, "secret": secret, "grant_type": "client_credential"}
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            data: dict[str, object] = resp.json()
    except httpx.HTTPError:
        logger.exception("wx_access_token_http_error")
        return None

    errcode_raw = data.get("errcode")
    errcode: int | None = int(cast(str, errcode_raw)) if errcode_raw is not None else None
    if errcode is not None and errcode != 0:
        logger.warning(
            "wx_access_token_failed",
            errcode=errcode,
            errmsg=str(data.get("errmsg", "")),
        )
        return None

    access_token_raw = data.get("access_token")
    access_token: str | None = access_token_raw if isinstance(access_token_raw, str) else None
    return access_token


__all__ = ["WxSubscribeChannel"]
