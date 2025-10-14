# src/bili_api/base.py
import json
from loguru import logger
import asyncio
from dataclasses import dataclass
import re
from typing import TypeVar, Generic
from aiohttp import (
    ClientSession,
    ClientTimeout,
    ClientError,
    ClientResponse,
    TCPConnector,
)
from loguru import logger
from urllib.parse import urlencode
from src.bili_api.errors import BiliApiError
from src.config import Config, UserConfig

T = TypeVar("T")


@dataclass
class BiliApiResult(Generic[T]):
    success: bool
    data: T

    def __init__(self, success: bool, data: T = None):
        self.success = success
        self.data = data
        logger.debug(self)

    @staticmethod
    def ok(data: T = None):
        return BiliApiResult[T](success=True, data=data)

    @staticmethod
    def fail(data: T = None):
        return BiliApiResult[T](success=False, data=data)


def retry(tries=3, interval=1):
    """异常自动重试装饰器"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            for attempt in range(1, tries + 1):
                try:
                    result = await func(*args, **kwargs)
                    if attempt > 1:
                        logger.success(f"{func.__name__} 第 {attempt} 次重试成功")
                    return result
                except BiliApiError as e:
                    if e.code in (1011040,):  # 特定错误直接抛出
                        raise e
                    elif e.code == 10030:
                        await asyncio.sleep(10)
                    elif e.code == -504:
                        pass  # 超时可重试
                    else:
                        raise e
                    if attempt < tries:
                        logger.warning(f"{func.__name__} 异常 {e}，重试 {attempt}")
                        await asyncio.sleep(interval)
                    else:
                        logger.error(f"{func.__name__} 已重试 {tries} 次失败")
                        raise
                except Exception as e:
                    if attempt < tries:
                        logger.warning(f"{func.__name__} 未知异常 {e}，重试 {attempt}")
                        await asyncio.sleep(interval)
                    else:
                        logger.error(f"{func.__name__} 未知异常重试 {tries} 次失败")
                        raise

        return wrapper

    return decorator


class BiliApiBase:
    """B站API基础类，负责会话管理与通用请求"""

    medals = []
    user_info = {}

    @property
    def like_max_time(self):
        return self._like_max_time

    def __init__(self, user_cfg: UserConfig, config: Config, timeout: int = 3):
        self._like_max_time = 30
        self.user_cfg = user_cfg
        self.config = config

        connector = TCPConnector(force_close=True)
        self.session = ClientSession(
            connector=connector,
            timeout=ClientTimeout(total=timeout),
            trust_env=True,
        )

    def get_cookie_value(self, key: str, default: str = "") -> str:
        pattern = rf"{re.escape(key)}=([^;]+)"
        match = re.search(pattern, self.user_cfg.cookie)
        return match.group(1) if match else default

    async def close(self):
        if self.session:
            await self.session.close()

    async def _check_response(self, resp: ClientResponse) -> BiliApiResult:
        try:
            data = await resp.json()
        except Exception as e:
            text = await resp.text()
            raise BiliApiError(-1, f"响应解析失败: {text}", e)
        logger.trace(resp.request_info)
        logger.trace(json.dumps(data))
        if data.get("code", 0) != 0:
            raise BiliApiError(data.get("code", -1), data.get("message", "未知错误"))
        elif "mode_info" in data["data"] and data["message"] != "":  # 发送弹幕时
            logger.warning(
                f"发送弹幕失败: {data.get('message', '未知错误') + '，是不是风控了？'}"
            )
            return BiliApiResult.fail()
        return BiliApiResult.ok(data.get("data"))

    @retry()
    async def _get(self, url: str, **kwargs) -> BiliApiResult:
        try:
            async with self.session.get(url, **kwargs) as resp:
                return await self._check_response(resp)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)

    @retry()
    async def _post(self, url: str, **kwargs) -> BiliApiResult:
        try:
            async with self.session.post(url, **kwargs) as resp:
                return await self._check_response(resp)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)
