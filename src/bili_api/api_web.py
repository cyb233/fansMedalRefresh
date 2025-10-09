import asyncio
import time
from urllib.parse import urlencode

from .errors import BiliApiError
from .common import BiliApiCommon
from loguru import logger


class BiliApiWeb(BiliApiCommon):
    """B站 Web API 实现"""

    def __init__(self, user_cfg, config):
        super().__init__(user_cfg, config)
        # 提取关键字段
        self.csrf = self.get_cookie_value("bili_jct")
        self.buvid = self.get_cookie_value("LIVE_BUVID")

        if not self.csrf or not self.buvid:
            raise ValueError("Cookie中缺少必要字段 bili_jct 或 LIVE_BUVID")

        self.session.headers.update({"Cookie": user_cfg.cookie})

        expires = self.get_cookie_value("bili_ticket_expires", "0")
        # 10位时间戳转时间
        cookie_expire_time = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(int(expires))
        )
        logger.info(f"Cookie 预计过期时间：{cookie_expire_time}")
        # 判断是否已经过期
        if time.time() > int(expires):
            logger.error("Cookie已过期，请重新登录")
            raise BiliApiError(-1, "Cookie已过期，请重新登录")

    async def refresh_cookie(self):
        """刷新Cookie"""
        pass  # todo

    async def get_user_info(self):
        url = "https://api.bilibili.com/x/web-interface/nav"
        data = await self._get(url)
        logger.debug(f"获取用户信息: {data}")
        self.user_info = data.get("data", {})
        return self.user_info

    async def get_fans_medals(self):
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/panel"
        params = {"page": 1, "page_size": 50}
        self.medals = []

        while True:
            data = await self._get(url, params=params)
            if data["data"].get("special_list"):
                self.medals.extend(data["data"]["special_list"])
            if not data["data"].get("list"):
                break
            self.medals.extend(data["data"]["list"])
            params["page"] += 1
            await asyncio.sleep(1)
        return self.medals

    async def live_status(self, room_id: str):
        url = "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom"
        return await self._get(url, params={"room_id": room_id})

    async def like_medal(self, room_id: str, anchor_id: str, click_time: int = 30):
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3"
        data = {
            "click_time": click_time,
            "room_id": room_id,
            "uid": self.user_info.get("mid"),
            "anchor_id": anchor_id,
            "csrf": self.csrf,
        }
        return await self._post(
            url,
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def send_danmaku(self, room_id: str, msg: str):
        url = "https://api.live.bilibili.com/msg/send"
        data = {
            "msg": msg,
            "roomid": room_id,
            "rnd": int(time.time() * 1000),
            "color": "16772431",
            "fontsize": "25",
            "csrf": self.csrf,
        }
        return await self._post(
            url,
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def live_heartbeat(self, room_id: str, minutes: int):
        url = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E"
        params = {
            "id": f"[0,0,{minutes},{room_id}]",
            "device": f'["{self.buvid}",""]',
            "ts": int(time.time() * 1000),
        }
        return await self._post(url, params=params)
