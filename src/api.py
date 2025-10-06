#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import re
from aiohttp import ClientSession, ClientTimeout, ClientError
from loguru import logger
from urllib.parse import urlencode, urlparse
from src.config import Config, UserConfig


def retry(tries=3, interval=1):
    def decorate(func):
        async def wrapper(*args, **kwargs):
            count = 0
            func.isRetrySuccess = False
            while True:
                try:
                    result = await func(*args, **kwargs)
                except Exception as e:
                    count += 1
                    if type(e) == BiliApiError:
                        if e.code == 1011040:
                            raise e
                        elif e.code == 10030:
                            await asyncio.sleep(10)
                        elif e.code == -504:
                            pass
                        else:
                            raise e
                    if count > tries:
                        logger.error(
                            f"API {urlparse(args[1]).path} 调用出现异常: {str(e)}"
                        )
                        raise e
                    else:
                        logger.error(
                            f"API {urlparse(args[1]).path} 调用出现异常: {str(e)}，重试中，第{count}次重试"
                        )
                        await asyncio.sleep(interval)
                    func.isRetrySuccess = True
                else:
                    if func.isRetrySuccess:
                        pass
                        logger.success(f"重试成功")
                    return result

        return wrapper

    return decorate


class BiliApiError(Exception):
    def __init__(self, code: int, msg: str, e: Exception | None = None):
        self.code = code
        self.msg = msg
        self.e = e

    def __str__(self):
        return self.msg + (f":\n{self.e}" if self.e else "")


class BiliApi:
    def __init__(self, user_cfg: UserConfig, config: Config):
        self.user_cfg = user_cfg
        self.config = config
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Cookie": user_cfg.cookie,
        }
        # self.csrf是user_cfg.cookie中bili_jct开头的值
        match = re.search(r"bili_jct=([^;]+)", user_cfg.cookie)
        if not match:
            raise ValueError("未在 cookie 中找到 bili_jct（csrf token）")
        self.csrf = match.group(1)
        self.session = ClientSession(
            timeout=ClientTimeout(total=3), trust_env=True, headers=self.headers
        )
        self.medals = []

    async def close(self):
        if self.session:
            await self.session.close()

    def __check_response(self, resp: dict) -> dict:
        logger.trace(resp)
        if resp["code"] != 0 or ("mode_info" in resp["data"] and resp["message"] != ""):
            raise BiliApiError(resp["code"], resp["message"])
        return resp["data"]

    @retry()
    async def __get(self, *args, **kwargs):
        try:
            response = await self.session.get(*args, **kwargs)
            data = await response.json()
            return self.__check_response(data)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)

    @retry()
    async def __post(self, *args, **kwargs):
        try:
            async with self.session.post(*args, **kwargs) as response:
                data = await response.json(content_type=None)
                return self.__check_response(data)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)

    async def get_user_info(self):
        url = "https://api.bilibili.com/x/web-interface/nav"
        self.user_info = await self.__get(url)

    async def get_fans_medals(self):
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/panel"
        params = {
            "page": 1,
            "page_size": 50,
        }
        self.medals = []
        while True:
            data = await self.__get(url, params=params)
            # 佩戴的
            if data["special_list"]:
                self.medals.extend(data["special_list"])
            # 其他的
            if not data["list"]:
                break
            self.medals.extend(data["list"])
            await asyncio.sleep(1)
            params["page"] += 1

    async def is_up_live(self, room_id: str) -> bool:
        url = "https://api.live.bilibili.com/room/v1/Room/get_info"
        params = {
            "room_id": room_id,
        }
        data = await self.__get(url, params=params)
        return data["live_status"] == 1

    async def like_medal(self, room_id: str, anchor_id: str, click_time: int = 30):
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3"
        data = {
            "click_time": click_time,
            "room_id": room_id,
            "uid": self.user_info["mid"],
            "anchor_id": anchor_id,
            "csrf": self.csrf,
        }
        await self.__post(
            url,
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    async def send_danmaku(self, room_id: str, msg: str):
        url = "https://api.live.bilibili.com/msg/send"
        data = {
            "msg": msg,
            "roomid": room_id,
            "rnd": int(asyncio.get_event_loop().time()),
            "color": "16772431",
            "fontsize": "25",
            "csrf": self.csrf,
        }
        await self.__post(
            url,
            data=urlencode(data),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
