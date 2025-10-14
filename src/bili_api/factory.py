from .common import BiliApiCommon
from src.bili_api.api_web import BiliApiWeb
from src.bili_api.api_app import BiliApiApp


class BiliApiFactory:
    """API 工厂类"""

    _registry: dict[str, type[BiliApiCommon]] = {
        "web": BiliApiWeb,
        "app": BiliApiApp,
    }

    @staticmethod
    def create(user_cfg, config) -> BiliApiCommon:
        """根据 config.api_type 创建对应 API 实例"""
        api_type = user_cfg.api_type.lower()
        cls = BiliApiFactory._registry.get(api_type)
        if not cls:
            raise ValueError(f"未知的 API 类型: {api_type}")
        return cls(user_cfg, config)
