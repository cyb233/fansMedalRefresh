#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dataclasses import dataclass, field
from typing import List
import json
import os


@dataclass
class LogConfig:
    """日志配置"""

    enabled: bool = field(default=True)  # 是否启用日志文件
    level: str = field(default="INFO")  # 日志级别
    file: str = field(
        default="log/fansMedalRefresh_{time:YYYY-MM-DD}.log"
    )  # 日志文件路径


class ConfigError(Exception):
    """配置错误异常"""

    pass


@dataclass
class UserConfig:
    """用户配置"""

    enabled: bool = field(default=True)
    cookie: str = field(default="")  # cookie，如选择web则必填
    access_token: str = field(default="")  # access_token，如选择app则必填
    api_type: str = field(default="app")  # API类型，可选 app 或 web
    white_uids: List[str] = field(default_factory=list)  # 白名单用户ID列表
    black_uids: List[str] = field(default_factory=list)  # 黑名单用户ID列表

    def __post_init__(self):
        """验证配置"""
        self.api_type = self.api_type.lower()
        if self.api_type == "app" and not self.access_token:
            raise ConfigError("您选择的api_type是app，access_token 不能为空")
        if self.api_type == "web" and not self.cookie:
            raise ConfigError("您选择的api_type是web，cookie 不能为空")


@dataclass
class LikeConfig:
    """点赞配置"""

    enabled: bool = field(default=True)  # 是否启用点赞功能
    like_count: int = field(default=30)  # 每次点赞数量


@dataclass
class DanmakuConfig:
    """弹幕配置"""

    enabled: bool = field(default=True)  # 是否启用弹幕功能
    min_interval: int = field(default=5)  # 最小弹幕间隔，单位秒
    max_interval: int = field(default=10)  # 最大弹幕间隔，单位秒
    danmaku_count: int = field(default=10)  # 发送弹幕数量
    danmaku_list: List[str] = field(
        default_factory=lambda: [
            "(⌒▽⌒).",
            "（￣▽￣）.",
            "(=・ω・=).",
            "(｀・ω・´).",
            "(〜￣△￣)〜.",
            "(･∀･).",
            "(°∀°)ﾉ.",
            "(￣3￣).",
            "╮(￣▽￣)╭.",
            "_(:3」∠)_.",
            "(^・ω・^ ).",
            "(●￣(ｴ)￣●).",
            "ε=ε=(ノ≧∇≦)ノ.",
            "⁄(⁄ ⁄•⁄ω⁄•⁄ ⁄)⁄.",
            "←◡←.",
        ]
    )  # 默认弹幕列表
    emoji_list: List[str] = field(
        default_factory=lambda: [
            "[花]",
            "[妙]",
            "[dog]",
            "[大笑]",
            "[比心]",
            "[吃瓜]",
            "[笑哭]",
            "[哇]",
            "[爱]",
            "[惊喜]",
        ]
    )


@dataclass
class LiveConfig:
    """观看配置"""

    enabled: bool = field(default=True)  # 是否启用观看功能
    policy: int = field(default=1)  # 观看策略，1 仅点亮牌子，2 完整观看亲密度
    light_time: int = field(default=15)  # 点亮所需时长
    full_affinity_time: int = field(default=25)  # 完整观看亲密度所需时长


@dataclass
class PushConfig:
    """推送配置

    这是一个通用的推送配置类，可以存储任意的配置键值对。
    不同的推送提供商可能需要不同的配置项，所以这里使用字典来存储所有配置。
    """

    provider_name: str = field(default="")  # 推送提供商名称
    proxies: dict[str, str] | None = field(
        default=None
    )  # 代理地址，格式如：{'http': 'socks5h://127.0.0.1:7890', 'https': 'socks5h://127.0.0.1:7890'}
    use_markdown: bool = field(default=False)  # Markdown
    _config: dict = field(default_factory=dict)  # 其他配置项存储字典

    def __init__(
        self,
        provider_name: str,
        proxies: dict[str, str] | None = None,
        use_markdown: bool = False,
        **kwargs,
    ):
        """初始化推送配置

        Args:
            provider_name: 推送提供商名称
            proxies: 代理地址，格式为 {'http': 'socks5h://127.0.0.1:7890', 'https': 'socks5h://127.0.0.1:7890'}
            **kwargs: 其他配置项，可以是任意键值对
        """
        self.provider_name = provider_name
        self.proxies = proxies
        self.use_markdown = use_markdown
        self._config = kwargs

    def get(self, key: str, default=None):
        """获取配置项的值

        Args:
            key: 配置项的键
            default: 如果键不存在时返回的默认值

        Returns:
            配置项的值，如果不存在则返回默认值
        """
        return self._config.get(key, default)

    def set(self, key: str, value):
        """设置配置项的值

        Args:
            key: 配置项的键
            value: 配置项的值
        """
        self._config[key] = value

    def __getitem__(self, key: str):
        """通过字典方式获取配置项的值

        Args:
            key: 配置项的键

        Raises:
            KeyError: 如果配置项不存在
        """
        return self._config[key]

    def __setitem__(self, key: str, value):
        """通过字典方式设置配置项的值

        Args:
            key: 配置项的键
            value: 配置项的值
        """
        self._config[key] = value


@dataclass
class Config:
    config_path: str

    """主配置类，包含所有配置项"""

    users: List[UserConfig]  # 用户配置必须提供，没有默认值
    log: LogConfig = field(default_factory=LogConfig)  # 日志配置
    like: LikeConfig = field(default_factory=LikeConfig)  # 点赞配置
    danmaku: DanmakuConfig = field(default_factory=DanmakuConfig)  # 弹幕配置
    live: LiveConfig = field(default_factory=LiveConfig)  # 观看配置
    push: List[PushConfig] = field(default_factory=list)  # 推送配置列表

    @classmethod
    def load_config(cls, config_path: str) -> "Config":
        """
        从文件加载配置，自动填充默认值

        Args:
            config_path: 配置文件路径

        Returns:
            Config: 配置对象

        Raises:
            ConfigError: 当配置文件不存在或配置无效时抛出
        """
        # 检查配置文件是否存在
        if not os.path.exists(config_path):
            raise ConfigError(f"配置文件 {config_path} 不存在")

        try:
            # 读取配置文件
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)

            # 验证必要的配置项
            if "users" not in file_config or not file_config["users"]:
                raise ConfigError("配置文件中必须包含 users 配置项且不能为空")

            # 创建用户配置
            users = [
                UserConfig(
                    enabled=user.get("enabled", True),
                    cookie=user.get("cookie", ""),
                    access_token=user.get("access_token", ""),
                    api_type=user.get("api_type", "app"),
                    white_uids=user.get("white_uids", []),
                    black_uids=user.get("black_uids", []),
                )
                for user in file_config["users"]
            ]

            # 创建配置对象
            config = cls(config_path=config_path, users=users)

            # 更新日志配置
            if "log" in file_config:
                log_data = file_config["log"]
                config.log = LogConfig(
                    enabled=log_data.get("enabled", config.log.enabled),
                    level=log_data.get("level", config.log.level),
                    file=log_data.get("file", config.log.file),
                )

            # 更新点赞配置
            if "like" in file_config:
                like_data = file_config["like"]
                config.like = LikeConfig(
                    enabled=like_data.get("enabled", config.like.enabled),
                    like_count=like_data.get("like_count", config.like.like_count),
                )

            # 更新弹幕配置
            if "danmaku" in file_config:
                danmaku_data = file_config["danmaku"]
                config.danmaku = DanmakuConfig(
                    enabled=danmaku_data.get("enabled", config.danmaku.enabled),
                    min_interval=danmaku_data.get(
                        "min_interval", config.danmaku.min_interval
                    ),
                    max_interval=danmaku_data.get(
                        "max_interval", config.danmaku.max_interval
                    ),
                    danmaku_count=danmaku_data.get(
                        "danmaku_count", config.danmaku.danmaku_count
                    ),
                    danmaku_list=danmaku_data.get(
                        "danmaku_list", config.danmaku.danmaku_list
                    ),
                    emoji_list=danmaku_data.get(
                        "emoji_list", config.danmaku.emoji_list
                    ),
                )

            # 更新观看配置
            if "live" in file_config:
                live_data = file_config["live"]
                config.live = LiveConfig(
                    enabled=live_data.get("enabled", config.live.enabled),
                    policy=live_data.get("policy", config.live.policy),
                    light_time=live_data.get("light_time", config.live.light_time),
                    full_affinity_time=live_data.get(
                        "full_affinity_time", config.live.full_affinity_time
                    ),
                )

            # 更新推送配置
            if "push" in file_config:
                push_configs = []
                for push_data in file_config["push"]:
                    if not isinstance(push_data, dict):
                        continue

                    # 获取并移除 provider_name，其余的配置项都作为 kwargs
                    provider_name = push_data.pop("provider_name", "")
                    if not provider_name:  # 如果没有提供 provider_name，跳过这个配置
                        continue

                    proxies = push_data.pop("proxies", None)

                    use_markdown = push_data.pop("use_markdown", False)
                    # 创建 PushConfig 对象，将剩余的所有配置项作为 kwargs 传入
                    push_config = PushConfig(
                        provider_name=provider_name,
                        proxies=proxies,
                        use_markdown=use_markdown,
                        **push_data,
                    )
                    push_configs.append(push_config)

                config.push = push_configs

            return config

        except json.JSONDecodeError as e:
            raise ConfigError(f"配置文件格式错误: {str(e)}")
        except ConfigError:
            raise
        except Exception as e:
            raise ConfigError(f"加载配置文件失败: {str(e)}")

    def replace_cookie(self, old_cookie: str, new_cookie: str) -> bool:
        """直接在配置文件中用字符串替换 cookie

        Returns:
            bool: True 表示替换成功（找到并替换了旧 cookie），False 表示未找到旧 cookie 或替换失败
        """
        with open(self.config_path, "r", encoding="utf-8") as f:
            content = f.read()

        if old_cookie not in content:
            return False  # 未找到旧 cookie

        new_content = content.replace(old_cookie, new_cookie)

        with open(self.config_path, "w", encoding="utf-8") as f:
            f.write(new_content)

        # 再验证一下确实写入成功
        return new_cookie in new_content
