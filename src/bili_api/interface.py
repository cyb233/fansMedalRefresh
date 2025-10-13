from abc import ABC, abstractmethod


class BiliApiInterface(ABC):
    """B站API接口定义"""

    @abstractmethod
    async def refresh_cookie(self) -> str: ...

    @abstractmethod
    async def get_user_info(self) -> dict: ...

    @abstractmethod
    async def get_fans_medals(self) -> list: ...

    @abstractmethod
    async def live_status(self, room_id: str) -> dict: ...

    @abstractmethod
    async def like_medal(
        self, room_id: str, anchor_id: str, click_time: int = 30
    ) -> dict: ...

    @abstractmethod
    async def send_danmaku(self, room_id: str, msg: str) -> dict: ...

    @abstractmethod
    async def live_heartbeat(self, room_id: str, minutes: int) -> dict: ...
