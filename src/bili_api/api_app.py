import asyncio
import math
import random
import time
from urllib.parse import urlencode

from .errors import BiliApiError
from .common import BiliApiCommon
from typing import Union
from hashlib import md5
from .base import BiliApiResult
from .entity import UserInfo, FansMedal, LiveStatus, Medal, RoomInfo


class Crypto:
    APPKEY = "4409e2ce8ffd12b8"
    APPSECRET = "59b43e04ad6965f34319062b478f83dd"

    @staticmethod
    def md5(data: Union[str, bytes]) -> str:
        """generates md5 hex dump of `str` or `bytes`"""
        if isinstance(data, str):
            return md5(data.encode()).hexdigest()
        elif isinstance(data, bytes):
            return md5(data).hexdigest()
        else:
            raise TypeError("Expected str or bytes, got %s" % type(data))

    @staticmethod
    def sign(data: Union[str, dict]) -> str:
        """salted sign funtion for `dict`(converts to qs then parse) & `str`"""
        if isinstance(data, dict):
            _str = urlencode(data)
        elif isinstance(data, str):
            _str = data
        else:
            raise TypeError("Expected dict or str, got %s" % type(data))
        return Crypto.md5(_str + Crypto.APPSECRET)


class SingableDict(dict):
    @property
    def sorted(self):
        """returns a alphabetically sorted version of `self`"""
        return dict(sorted(self.items()))

    @property
    def signed(self):
        """returns our sorted self with calculated `sign` as a new key-value pair at the end"""
        _sorted = self.sorted
        return {**_sorted, "sign": Crypto.sign(_sorted)}


def randomString(length: int = 16) -> str:
    return "".join(
        random.sample(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", length
        )
    )


def get_base_params(access_key: str, **kwargs) -> dict:
    return {
        "access_key": access_key,
        "actionKey": "appkey",
        "appkey": Crypto.APPKEY,
        "ts": int(time.time()),
        **kwargs,
    }


class BiliApiApp(BiliApiCommon):
    """
    B站 APP API 实现
    参考了 https://github.com/XiaoMiku01/fansMedalHelper/blob/master/src/api.py
    """

    def __init__(self, user_cfg, config):
        super().__init__(user_cfg, config)
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 BiliDroid/6.73.1 (bbcallen@gmail.com) os/android model/Mi 10 Pro mobi_app/android build/6731100 channel/xiaomi innerVer/6731110 osVer/12 network/2"
            }
        )
        self.x_www_form_urlencoded = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

    async def refresh_login(self) -> BiliApiResult[None]:
        """
        登录验证
        """
        url = "https://app.bilibili.com/x/v2/account/mine"
        params = get_base_params(self.user_cfg.access_token)
        data = await self._get(url, params=SingableDict(params).signed)
        self.user_info = UserInfo(mid=data.data["mid"], uname=data.data["name"])
        if int(self.user_info.mid) == 0:
            data.success = False
        return BiliApiResult(data.success)

    async def get_user_info(self) -> BiliApiResult[UserInfo]:
        return BiliApiResult.ok(self.user_info)

    async def get_fans_medals(self) -> BiliApiResult[list[FansMedal]]:
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/panel"
        params = get_base_params(self.user_cfg.access_token, page=1, page_size=50)
        self.medals.clear()
        medals: list[dict] = []
        while True:
            data = await self._get(url, params=SingableDict(params).signed)
            if data.data.get("special_list"):
                medals.extend(data.data["special_list"])
            if not data.data.get("list"):
                break
            medals.extend(data.data["list"])
            params["page"] += 1
            await asyncio.sleep(1)
        self.medals = [
            FansMedal(
                medal=Medal(
                    name=m["medal"]["medal_name"], is_lighted=m["medal"]["is_lighted"]
                ),
                room_info=RoomInfo(
                    room_id=m["room_info"]["room_id"],
                    live_status=m["room_info"]["living_status"],
                ),
                anchor_info=UserInfo(
                    mid=m["medal"]["target_id"], uname=m["anchor_info"]["nick_name"]
                ),
            )
            for m in medals
        ]
        return BiliApiResult.ok(self.medals)

    async def live_status(self, room_id: str) -> BiliApiResult[LiveStatus]:
        url = "https://api.live.bilibili.com/xlive/app-room/v1/index/getInfoByRoom"
        params = get_base_params(self.user_cfg.access_token)
        live_status_result = await self._get(url, params=SingableDict(params).signed)
        live_status = LiveStatus(
            room_info=RoomInfo(
                room_id=live_status_result.data["room_info"]["room_id"],
                live_status=live_status_result.data["room_info"]["live_status"],
            ),
            new_switch_info=live_status_result.data["new_switch_info"],
        )
        return BiliApiResult.ok(live_status)

    async def like_medal(
        self, room_id: str, anchor_id: str, click_time: int = 30
    ) -> BiliApiResult[None]:
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3"
        for i in range(math.ceil(click_time / self.like_max_time)):
            part_click = min(self.like_max_time, click_time - i * self.like_max_time)
            params = get_base_params(
                self.user_cfg.access_token,
                roomid=room_id,
                click_time=part_click,
                anchor_id=anchor_id,
                uid=anchor_id,
            )
            await self._post(
                url,
                data=SingableDict(params).signed,
                headers={**self.session.headers, **self.x_www_form_urlencoded},
            )
        return BiliApiResult.ok()

    async def send_danmaku(self, room_id: str, msg: str) -> BiliApiResult[None]:
        url = "https://api.live.bilibili.com/xlive/app-room/v1/dM/sendmsg"
        params = get_base_params(self.user_cfg.access_token)
        data = {
            "cid": room_id,
            "msg": msg,
            "rnd": int(time.time()),
            "color": "16777215",
            "fontsize": "25",
        }
        return await self._get(
            url,
            params=SingableDict(params).signed,
            data=data,
            headers={**self.session.headers, **self.x_www_form_urlencoded},
        )

    async def live_heartbeat(
        self, room_id: str, up_id: str, minutes: int
    ) -> BiliApiResult[None]:
        url = "https://live-trace.bilibili.com/xlive/data-interface/v1/heartbeat/mobileHeartBeat"
        today_timestamp = int(
            time.mktime(
                time.strptime(
                    f"{time.strftime('%Y-%m-%d', time.localtime(time.time()))} 00:00:00",
                    "%Y-%m-%d %H:%M:%S",
                )
            )
        )
        now_timestamp = int(time.time())
        timestamp = (
            now_timestamp - 60
            if now_timestamp - 60 > today_timestamp
            else today_timestamp
        )
        params = get_base_params(self.user_cfg.access_token)
        params.update(
            data={
                "platform": "android",
                "uuid": self.uuids[0],
                "buvid": randomString(37).upper(),
                "seq_id": "1",
                "room_id": f"{room_id}",
                "parent_id": "6",
                "area_id": "283",
                "timestamp": f"{timestamp}",
                "secret_key": "axoaadsffcazxksectbbb",
                "watch_time": f"{now_timestamp - timestamp}",
                "up_id": f"{up_id}",
                "up_level": "40",
                "jump_from": "30000",
                "gu_id": randomString(43).lower(),
                "play_type": "0",
                "play_url": "",
                "s_time": "0",
                "data_behavior_id": "",
                "data_source_id": "",
                "up_session": f"l:one:live:record:{room_id}:{int(time.time())-88888}",
                "visit_id": randomString(32).lower(),
                "watch_status": "%7B%22pk_id%22%3A0%2C%22screen_status%22%3A1%7D",
                "click_id": self.uuids[1],
                "session_id": "",
                "player_type": "0",
                "client_ts": f"{now_timestamp}",
            }
        )
        return await self._get(
            url,
            data=SingableDict(params).signed,
            headers={**self.session.headers, **self.x_www_form_urlencoded},
        )
