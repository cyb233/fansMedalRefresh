# src/bili_api/base.py
import asyncio
import re
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

    def __init__(self, user_cfg, config, timeout: int = 10):
        self.user_cfg = user_cfg
        self.config = config
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
        }

        connector = TCPConnector(force_close=True)
        self.session = ClientSession(
            connector=connector,
            timeout=ClientTimeout(total=timeout),
            trust_env=True,
            headers=self.headers,
        )

    def get_cookie_value(self, key: str) -> str | None:
        pattern = rf"{re.escape(key)}=([^;]+)"
        match = re.search(pattern, self.user_cfg.cookie)
        return match.group(1) if match else None

    async def close(self):
        if self.session:
            await self.session.close()

    async def _check_response(self, resp: ClientResponse) -> dict:
        try:
            data = await resp.json()
        except Exception as e:
            text = await resp.text()
            raise BiliApiError(-1, f"响应解析失败: {text}", e)

        logger.trace(data)
        if data.get("code", 0) != 0:
            raise BiliApiError(data.get("code", -1), data.get("message", "未知错误"))
        elif "mode_info" in data["data"] and data["message"] != "":  # 发送弹幕时
            logger.warning(
                f"发送弹幕失败: {data.get('message', '未知错误') + '，是不是风控了？'}"
            )
            return {"success": False}
        return {"data": data.get("data"), "success": True}

    @retry()
    async def _get(self, url: str, **kwargs) -> dict:
        try:
            async with self.session.get(url, **kwargs) as resp:
                return await self._check_response(resp)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)

    @retry()
    async def _post(self, url: str, **kwargs) -> dict:
        try:
            async with self.session.post(url, **kwargs) as resp:
                return await self._check_response(resp)
        except ClientError as e:
            raise BiliApiError(-1, str(e), e)
