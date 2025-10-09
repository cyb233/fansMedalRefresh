from abc import ABC
from .base import BiliApiBase
from .interface import BiliApiInterface


class BiliApiCommon(BiliApiBase, BiliApiInterface, ABC):
    """联合类型：既是 BiliApiBase 子类，又实现 BiliApiInterface"""

    pass
