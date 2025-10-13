import asyncio
import time
import hmac
import hashlib
from urllib.parse import urlencode

from .common import BiliApiCommon
from loguru import logger


class BiliApiWeb(BiliApiCommon):
    """B站 Web API 实现"""

    def __init__(self, user_cfg, config):
        super().__init__(user_cfg, config)
        # 提取关键字段
        self.csrf = self.get_cookie_value("bili_jct")
        self.buvid = self.get_cookie_value("LIVE_BUVID")
        self.expires = self.get_cookie_value("bili_ticket_expires", "0")

        if not self.csrf or not self.buvid:
            raise ValueError("Cookie中缺少必要字段 bili_jct 或 LIVE_BUVID")

        self.session.headers.update({"Cookie": user_cfg.cookie})

        # 10位时间戳转时间
        cookie_expire_time = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(int(self.expires))
        )
        logger.info(f"Cookie 预计过期时间：{cookie_expire_time}")

    @staticmethod
    def format_string(s: str) -> str:
        return "".join(chr(ord(c) - 1) for c in s)

    @staticmethod
    def build_hexsign(ts: int) -> str:
        key_raw = "YhxToH[2q"
        key = BiliApiWeb.format_string(key_raw)
        msg = f"ts{ts}".encode("utf-8")
        hkey = key.encode("utf-8")
        return hmac.new(hkey, msg, hashlib.sha256).hexdigest()

    async def refresh_cookie(self):
        """
        刷新Cookie
        bili_ticket=ticket
        bili_ticket_expires=created_at+ttl
        """
        url = (
            "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"
        )
        # 判断是否已经过期
        if time.time() > int(self.expires):
            logger.warning("Cookie已过期，尝试刷新Cookie")
            ts = int(time.time())
            params = {
                "key_id": "ec02",
                "hexsign": BiliApiWeb.build_hexsign(ts),
                "context[ts]": ts,
                "csrf": self.csrf,
            }
            data = await self._post(url, params=params)
            if data.get("success"):
                ticket = data.get("data", {}).get("ticket", "")
                created_at = data.get("data", {}).get("created_at", 0)
                ttl = data.get("data", {}).get("ttl", 0)
                self.user_cfg.cookie.replace(
                    self.get_cookie_value("bili_ticket"), ticket
                )
                self.user_cfg.cookie.replace(
                    self.get_cookie_value("bili_ticket_expires"), str(created_at + ttl)
                )
                self.expires = str(created_at + ttl)
        return self.user_cfg.cookie

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
