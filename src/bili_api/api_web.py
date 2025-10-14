import asyncio
import math
import time
import hmac
import hashlib
from urllib.parse import urlencode

from .base import BiliApiResult
from .common import BiliApiCommon
from loguru import logger


def format_string(s: str) -> str:
    return "".join(chr(ord(c) - 1) for c in s)


def build_hexsign(ts: int) -> str:
    key_raw = "YhxToH[2q"
    key = BiliApiWeb.format_string(key_raw)
    msg = f"ts{ts}".encode("utf-8")
    hkey = key.encode("utf-8")
    return hmac.new(hkey, msg, hashlib.sha256).hexdigest()


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
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
                "Cookie": user_cfg.cookie,
            }
        )

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
        key = format_string(key_raw)
        msg = f"ts{ts}".encode("utf-8")
        hkey = key.encode("utf-8")
        return hmac.new(hkey, msg, hashlib.sha256).hexdigest()

    async def refresh_login(self) -> BiliApiResult[dict]:
        """
        刷新Cookie
        bili_ticket=ticket
        bili_ticket_expires=created_at+ttl
        """
        old_cookie = self.user_cfg.cookie
        data = None
        # 判断是否已经过期
        if time.time() > int(self.expires):
            url = "https://api.bilibili.com/bapis/bilibili.api.ticket.v1.Ticket/GenWebTicket"
            logger.warning("Cookie已过期，尝试刷新Cookie")
            ts = int(time.time())
            params = {
                "key_id": "ec02",
                "hexsign": build_hexsign(ts),
                "context[ts]": ts,
                "csrf": self.csrf,
            }
            data = await self._post(url, params=params)
            if data.success:
                ticket = data.data.get("ticket", "")
                created_at = data.data.get("created_at", 0)
                ttl = data.data.get("ttl", 0)
                self.user_cfg.cookie = self.user_cfg.cookie.replace(
                    self.get_cookie_value("bili_ticket"), ticket
                ).replace(
                    self.get_cookie_value("bili_ticket_expires"), str(created_at + ttl)
                )
                self.expires = str(created_at + ttl)
            else:
                logger.error("Cookie刷新失败")
        # 写回配置文件
        if self.user_cfg.cookie != old_cookie:
            logger.info("更新cookie")
            res = self.config.replace_cookie(old_cookie, self.user_cfg.cookie)
            logger.info(f"cookie更新 {'成功' if res else '失败'}")
        return BiliApiResult.ok(data)

    async def get_user_info(self) -> BiliApiResult[dict]:
        url = "https://api.bilibili.com/x/web-interface/nav"
        data = await self._get(url)
        self.user_info = data.data
        return data

    async def get_fans_medals(self) -> BiliApiResult[list[dict]]:
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/panel"
        params = {"page": 1, "page_size": 50}
        self.medals.clear()

        while True:
            data = await self._get(url, params=params)
            if data.data.get("special_list"):
                self.medals.extend(data.data["special_list"])
            if not data.data.get("list"):
                break
            self.medals.extend(data.data["list"])
            params["page"] += 1
            await asyncio.sleep(1)
        return BiliApiResult.ok(self.medals)

    async def live_status(self, room_id: str) -> BiliApiResult[dict]:
        url = "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom"
        return await self._get(url, params={"room_id": room_id})

    async def like_medal(
        self, room_id: str, anchor_id: str, click_time: int = 30
    ) -> BiliApiResult[dict]:
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3"
        for i in range(math.ceil(click_time / self.like_max_time)):
            part_click = min(self.like_max_time, click_time - i * self.like_max_time)
            data = {
                "click_time": part_click,
                "room_id": room_id,
                "uid": self.user_info.mid,
                "anchor_id": anchor_id,
                "csrf": self.csrf,
            }
            await self._post(
                url,
                data=urlencode(data),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        return BiliApiResult.ok()

    async def send_danmaku(self, room_id: str, msg: str) -> BiliApiResult[dict]:
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

    async def live_heartbeat(
        self, room_id: str, up_id: str, minutes: int
    ) -> BiliApiResult[dict]:
        url = "https://live-trace.bilibili.com/xlive/data-interface/v1/x25Kn/E"
        params = {
            "id": f"[0,0,{minutes},{room_id}]",
            "device": f'["{self.buvid}",""]',
            "ts": int(time.time() * 1000),
        }
        return await self._post(url, params=params)
