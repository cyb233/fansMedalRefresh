import asyncio
import time
from urllib.parse import urlencode
from .common import BiliApiCommon


# todo
class BiliApiApp(BiliApiCommon):
    """B站 APP API 实现"""

    def __init__(self, user_cfg, config):
        super().__init__(user_cfg, config)

    async def get_user_info(self):
        return {}

    async def get_fans_medals(self):
        return []

    async def live_status(self, room_id: str):
        return {}

    async def like_medal(self, room_id: str, anchor_id: str, click_time: int = 30):
        return {}

    async def send_danmaku(self, room_id: str, msg: str):
        return {}

    async def live_heartbeat(self, room_id: str, minutes: int):
        return {}
