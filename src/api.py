#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import re
import time
from aiohttp import (
    ClientSession,
    ClientTimeout,
    ClientError,
    ClientResponse,
    TCPConnector,
)
from loguru import logger
from urllib.parse import urlencode, urlparse
from src.config import Config, UserConfig


def retry(tries=3, interval=1):
    """
    异常自动重试装饰器
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(1, tries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 1:
                        logger.success(f"{func.__name__} 第 {attempt} 次重试成功")
                    return result
                except BiliApiError as e:
                    # 针对特定错误处理
                    if e.code == 1011040:
                        raise e
                    elif e.code == 10030:
                        await asyncio.sleep(10)
                    elif e.code == -504:
                        pass  # 超时可重试
                    else:
                        raise e
                    if attempt < tries:
                        logger.warning(
                            f"{func.__name__} 调用异常 {e}，第 {attempt} 次重试"
                        )
                        await asyncio.sleep(interval)
                    else:
                        logger.error(f"{func.__name__} 调用失败，已重试 {tries} 次")
                        raise
                except Exception as e:
                    if attempt < tries:
                        logger.warning(
                            f"{func.__name__} 未知异常 {e}，第 {attempt} 次重试"
                        )
                        await asyncio.sleep(interval)
                    else:
                        logger.error(f"{func.__name__} 未知异常，已重试 {tries} 次")
                        raise

        return wrapper

    return decorator


class BiliApiError(Exception):
    def __init__(self, code: int, msg: str, e: Exception | None = None):
        self.code = code
        self.msg = msg
        self.e = e

    def __str__(self):
        return self.msg + (f":\n{self.e}" if self.e else "")


class BiliApi:

    def __init__(self, user_cfg: UserConfig, config: Config, timeout: int = 10):
        self.user_cfg = user_cfg
        self.config = config
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            "Cookie": user_cfg.cookie,
        }
        # csrf token
        self.csrf = self.get_cookie_value("bili_jct")
        if not self.csrf:
            raise ValueError("未在 cookie 中找到 bili_jct（csrf token）")
        # buvid
        self.buvid = self.get_cookie_value("LIVE_BUVID")
        if not self.buvid:
            raise ValueError("未在 cookie 中找到 LIVE_BUVID")

        connector = TCPConnector(force_close=True)
        self.session = ClientSession(
            connector=connector,
            timeout=ClientTimeout(total=timeout),
            trust_env=True,
            headers=self.headers,
        )
        self.medals = []
        self.user_info = {}

    def get_cookie_value(self, key: str) -> str | None:
        pattern = rf"{re.escape(key)}=([^;]+)"
        match = re.search(pattern, self.user_cfg.cookie)
        return match.group(1) if match else None

    async def close(self):
        if self.session:
            await self.session.close()

    async def __check_response(self, resp: ClientResponse) -> dict:
        try:
            data = await resp.json()
        except Exception as e:
            text = await resp.text()
            raise BiliApiError(-1, f"响应解析失败: {text}", e)

        logger.trace(data)
        if data.get("code", 0) != 0:
            raise BiliApiError(data.get("code", -1), data.get("message", "未知错误"))
        elif "mode_info" in data["data"] and data["message"] != "":  # 发送弹幕时
            raise BiliApiError(
                data.get("code", -1),
                data.get("message", "未知错误") + "，是不是风控了？",
            )
        return data.get("data", {})

    @retry()
    async def __get(self, *args, **kwargs):
        try:
            async with self.session.get(*args, **kwargs) as response:
                return await self.__check_response(response)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)

    @retry()
    async def __post(self, *args, **kwargs):
        try:
            async with self.session.post(*args, **kwargs) as response:
                return await self.__check_response(response)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)

    async def get_user_info(self):
        url = "https://api.bilibili.com/x/web-interface/nav"
        self.user_info = await self.__get(url)
        return self.user_info

    async def get_fans_medals(self):
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/fansMedal/panel"
        params = {"page": 1, "page_size": 50}
        self.medals = []

        while True:
            data = await self.__get(url, params=params)
            # 佩戴的
            if data.get("special_list"):
                self.medals.extend(data["special_list"])
            if not data.get("list"):
                break
            self.medals.extend(data["list"])
            params["page"] += 1
            await asyncio.sleep(1)
        return self.medals

    async def live_status(self, room_id: str):
        url = "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom"
        params = {
            "room_id": room_id,
        }
        return await self.__get(url, params=params)

    async def like_medal(self, room_id: str, anchor_id: str, click_time: int = 30):
        url = "https://api.live.bilibili.com/xlive/app-ucenter/v1/like_info_v3/like/likeReportV3"
        data = {
            "click_time": click_time,
            "room_id": room_id,
            "uid": self.user_info["mid"],
            "anchor_id": anchor_id,
            "csrf": self.csrf,
        }
        return await self.__post(
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
        return await self.__post(
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
        return await self.__post(url, params=params)
