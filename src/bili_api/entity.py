from loguru import logger
from dataclasses import dataclass


@dataclass
class Medal:
    name: str  # 粉丝牌名称
    is_lighted: int


@dataclass
class RoomInfo:
    room_id: str
    live_status: int  # 0: 未开播 1: 直播中 2: 轮播中


@dataclass
class UserInfo:
    mid: str  # 用户id
    uname: str  # 用户名


@dataclass
class FansMedal:
    medal: Medal  # 粉丝牌信息
    room_info: RoomInfo  # 直播间信息
    anchor_info: UserInfo  # 主播信息


@dataclass
class LiveStatus:
    room_info: RoomInfo  # 直播间信息
    new_switch_info: dict[str, int]  # 直播间状态开关
