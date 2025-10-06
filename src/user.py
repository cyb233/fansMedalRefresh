#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import random
from loguru import logger
from src.config import Config, UserConfig
from .api import BiliApi


class BiliUser:
    def __init__(self, user_cfg: UserConfig, config: Config):
        self.user_cfg = user_cfg
        self.config = config
        self.api = BiliApi(user_cfg, config)

    async def start(self):
        msgs = []
        # 获取个人信息
        await self.api.get_user_info()
        logger.info(
            f"开始执行用户{self.api.user_info['uname']}({self.api.user_info['mid']})"
        )
        # 获取所有粉丝牌
        await self.api.get_fans_medals()
        logger.info(f"已获取粉丝牌{len(self.api.medals)}个")
        msgs.append(
            f"处理{self.api.user_info['uname']}({self.api.user_info['mid']})的{len(self.api.medals)}个粉丝牌"
        )
        # 遍历粉丝牌
        for medal in self.api.medals:
            # 处理黑白名单
            ruid = medal["uinfo_medal"]["ruid"]
            if self.user_cfg.white_uids:
                if not ruid in self.user_cfg.white_uids:
                    logger.trace(
                        f"粉丝牌 {medal['uinfo_medal']['name']} 不在白名单，跳过"
                    )
                    continue
            if self.user_cfg.black_uids:
                if ruid in self.user_cfg.black_uids:
                    logger.trace(
                        f"粉丝牌 {medal['uinfo_medal']['name']} 在黑名单，跳过"
                    )
                    continue
            logger.trace(f"检查粉丝牌 {medal['uinfo_medal']['name']}")
            # 检查粉丝牌点亮状态
            if not medal["medal"]["is_lighted"]:
                logger.info(f"粉丝牌 {medal['uinfo_medal']['name']} 需要点亮")
                # 检查是否开播
                is_live = await self.api.is_up_live(medal["room_info"]["room_id"])
                logger.info(
                    f"{medal['uinfo_medal']['name']}"
                    + ("正在直播" if is_live else "未在直播")
                )
                if is_live:
                    if self.config.like.enabled:
                        logger.info(f"{medal['uinfo_medal']['name']} 开始点赞")
                        # 开播中，使用点赞点亮，点赞次数按配置，时间间隔按配置随机秒
                        await self.api.like_medal(
                            medal["room_info"]["room_id"],
                            ruid,
                            self.config.like.like_count,
                        )
                        msgs.append(
                            f"通过点赞{self.config.like.like_count}次点亮up {medal['anchor_info']['nick_name']} 的粉丝牌 {medal['uinfo_medal']['name']}"
                        )
                else:
                    if self.config.danmaku.enabled:
                        logger.info(f"{medal['uinfo_medal']['name']} 开始发送弹幕")
                        # 未开播，使用弹幕点亮，弹幕数量按配置，内容从配置列表随机
                        for i in range(self.config.danmaku.danmaku_count):
                            logger.debug(f"第{i}次...")
                            await self.api.send_danmaku(
                                medal["room_info"]["room_id"],
                                random.choice(self.config.danmaku.danmaku_list),
                            )
                            await asyncio.sleep(
                                random.randint(
                                    self.config.danmaku.min_interval,
                                    self.config.danmaku.max_interval,
                                )
                            )
                        msgs.append(
                            f"通过发送{self.config.danmaku.danmaku_count}条弹幕点亮up {medal['anchor_info']['nick_name']} 的粉丝牌 {medal['uinfo_medal']['name']}"
                        )
        # 关闭会话
        await self.api.close()
        # 构造结果消息
        res = "\n".join(msgs)
        logger.debug(f"执行结果为\n\n{res}")
        return res
