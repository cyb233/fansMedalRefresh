from abc import ABC, abstractmethod
from .base import BiliApiResult
from .entity import UserInfo, FansMedal, LiveStatus


class BiliApiInterface(ABC):
    """B站API接口定义"""

    """
    str: cookie / access_token
    """

    @abstractmethod
    async def refresh_login(self) -> BiliApiResult[None]: ...

    """
    UserInfo: {mid, uname}
    """

    @abstractmethod
    async def get_user_info(self) -> BiliApiResult[UserInfo]: ...

    """
    list[dict]: [{medal_id, medal_name, level, room_id, anchor_id}]
    """

    @abstractmethod
    async def get_fans_medals(self) -> BiliApiResult[list[FansMedal]]: ...

    """
    dict: {live_status, live_time, live_title}
    """

    @abstractmethod
    async def live_status(self, room_id: str) -> BiliApiResult[LiveStatus]: ...

    @abstractmethod
    async def like_medal(
        self, room_id: str, anchor_id: str, click_time: int = 30
    ) -> BiliApiResult[None]: ...

    @abstractmethod
    async def send_danmaku(self, room_id: str, msg: str) -> BiliApiResult[None]: ...

    @abstractmethod
    async def live_heartbeat(
        self, room_id: str, up_id: str, minutes: int
    ) -> BiliApiResult[None]: ...
