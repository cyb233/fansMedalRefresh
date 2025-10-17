#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import random
import time
from loguru import logger
from src.config import Config, UserConfig
from src.bili_api.factory import BiliApiFactory


class BiliUser:

    def __init__(self, user_cfg: UserConfig, config: Config):
        self.start_time = time.time()
        self.user_cfg = user_cfg
        self.config = config
        self.live_only_medals = []
        self.title_msg = ""
        self.msgs = []
        self.live_msgs = []
        self.end_msg = ""
        self.api = BiliApiFactory.create(user_cfg, config)
        self.login_success = False
        self.need_light = 0
        self.light_success = 0

    async def check_login(self):
        logger.info("正在检查登陆状态")
        data = await self.api.refresh_login()
        self.login_success = data.success
        logger.info(f"登陆状态: {data.success}")
        # 获取个人信息
        logger.info("正在获取用户信息")
        await self.api.get_user_info()
        self.log = logger.bind(user=self.api.user_info.uname)
        # 获取所有粉丝牌
        self.log.info("正在获取所有粉丝牌")
        await self.api.get_fans_medals()
        self.log.info(f"已获取粉丝牌{len(self.api.medals)}个")
        self.title_msg = f"处理{self.api.user_info.uname}({self.api.user_info.mid})的{len(self.api.medals)}个粉丝牌"

    async def like_and_danmaku(self):
        if not self.login_success:
            self.log.error("请先检查登陆状态")
            return
        self.log.info(
            f"点赞和弹幕 开始执行用户{self.api.user_info.uname}({self.api.user_info.mid})"
        )
        # 遍历粉丝牌
        for index in range(len(self.api.medals)):
            medal = self.api.medals[index]
            # 处理黑白名单
            ruid = medal.anchor_info.mid
            if self.user_cfg.white_uids:
                if not ruid in self.user_cfg.white_uids:
                    self.log.trace(f"粉丝牌 {medal.medal.name} 不在白名单，跳过")
                    continue
            if self.user_cfg.black_uids:
                if ruid in self.user_cfg.black_uids:
                    self.log.trace(f"粉丝牌 {medal.medal.name} 在黑名单，跳过")
                    continue
            self.log.trace(f"检查粉丝牌 {medal.medal.name}")
            # 检查粉丝牌点亮状态
            if not medal.medal.is_lighted:
                self.need_light += 1
                self.log.info(
                    f"粉丝牌 {medal.medal.name} 需要点亮({index + 1}/{len(self.api.medals)})"
                )
                # 检查是否开播
                live_status_result = await self.api.live_status(medal.room_info.room_id)
                live_status = live_status_result.data
                self.log.info(
                    f"{medal.anchor_info.uname}"
                    + (
                        "正在直播"
                        if live_status.room_info.live_status == 1
                        else "未在直播"
                    )
                )
                # 判断能否点赞或弹幕点亮
                new_switch_info = live_status.new_switch_info
                if not new_switch_info.get("room-danmaku-editor", 1):
                    self.log.info(
                        f"{medal.medal.name} 无法点赞或发送弹幕，尝试切换至观看点亮"
                    )
                    self.live_only_medals.append(medal)
                    continue
                if live_status.room_info.live_status == 1:
                    if self.config.like.enabled:
                        self.log.info(f"{medal.medal.name} 开始点赞")
                        # 开播中，使用点赞点亮，点赞次数按配置，时间间隔按配置随机秒
                        await self.api.like_medal(
                            medal.room_info.room_id,
                            ruid,
                            self.config.like.like_count,
                        )
                        self.light_success += 1
                        self.msgs.append(
                            f"点赞{self.config.like.like_count}次点亮up {medal.anchor_info.uname} 的粉丝牌 {medal.medal.name}"
                        )
                else:
                    if self.config.danmaku.enabled:
                        self.log.info(f"{medal.medal.name} 开始发送弹幕")
                        # 未开播，使用弹幕点亮，弹幕数量按配置，内容从配置列表随机
                        successTimes = 0
                        for i in range(self.config.danmaku.danmaku_count):
                            self.log.debug(f"第{i + 1}次...")
                            # 随机顺序，默认 15条弹幕+10个表情+正反顺序 可以有300个不重样的
                            danmaku = random.choice(self.config.danmaku.danmaku_list)
                            emoji = random.choice(self.config.danmaku.emoji_list)
                            order = random.randint(1, 2)
                            send_danmaku = (
                                danmaku + emoji if order == 1 else emoji + danmaku
                            )
                            res = await self.api.send_danmaku(
                                medal.room_info.room_id,
                                send_danmaku,
                            )
                            self.log.info(
                                f"{medal.medal.name} 发送 {i + 1}/{self.config.danmaku.danmaku_count} 条 {send_danmaku} {'成功' if res.success else '失败'}"
                            )
                            if res.success:
                                successTimes += 1
                            await asyncio.sleep(
                                random.randint(
                                    self.config.danmaku.min_interval,
                                    self.config.danmaku.max_interval,
                                )
                            )
                        if successTimes == self.config.danmaku.danmaku_count:
                            self.light_success += 1
                        self.msgs.append(
                            f"成功发送 {successTimes}/{self.config.danmaku.danmaku_count} 条弹幕点亮up {medal.anchor_info.uname} 的粉丝牌 {medal.medal.name}"
                        )

    async def watch_live(self):
        if not self.login_success:
            self.log.error("请先检查登陆状态")
            return
        self.log.info(
            f"观看直播 开始执行用户{self.api.user_info.uname}({self.api.user_info.mid})"
        )
        if not self.config.live.enabled:
            return
        if self.config.live.policy == 1:
            watch_time = self.config.live.light_time
            live_medals = self.live_only_medals
        elif self.config.live.policy == 2:
            watch_time = self.config.live.full_affinity_time
            live_medals = [
                *[
                    m for m in self.api.medals if m in self.live_only_medals
                ],  # 先 live_only_medals
                *[
                    m for m in self.api.medals if m not in self.live_only_medals
                ],  # 再其他的
            ]
        else:
            return
        for index in range(len(live_medals)):
            medal = live_medals[index]
            self.log.info(
                f"开始观看 {medal.anchor_info.uname} 的直播({index + 1}/{len(live_medals)})"
            )
            # 发送心跳
            for i in range(watch_time):
                await self.api.live_heartbeat(
                    medal.room_info.room_id, medal.anchor_info.mid, i
                )
                self.log.debug(
                    f"{medal.anchor_info.uname} 的粉丝牌 {medal.medal.name} 发送心跳包 {i + 1}/{watch_time}"
                )
                if i > 0 and (i + 1) % 5 == 0:
                    self.log.info(
                        f"{medal.anchor_info.uname} 的粉丝牌 {medal.medal.name} 发送心跳包 {i + 1}/{watch_time}"
                    )
                await asyncio.sleep(60)
            self.log.info(
                f"{medal.anchor_info.uname} 的粉丝牌 {medal.medal.name} 已观看{watch_time}分钟直播"
            )
            if medal in self.live_only_medals:
                self.msgs.append(
                    f"观看{self.config.danmaku.danmaku_count}分钟直播点亮up {medal.anchor_info.uname} 的粉丝牌 {medal.medal.name}"
                )
            else:
                self.live_msgs.append(
                    f"{medal.anchor_info.uname} 的粉丝牌 {medal.medal.name} 已观看{watch_time}分钟直播"
                )

    async def collect_msgs(self) -> list[str]:
        # 关闭会话
        self.log.debug("关闭会话")
        await self.api.close()
        end_time = time.time()
        total = len(self.msgs)
        if total:
            self.end_msg = f"共点亮{self.light_success + len(self.live_only_medals)}/{total}个粉丝牌"
        elif not self.login_success:
            self.end_msg = "登陆失败"
        else:
            self.end_msg = "没有需要点亮的粉丝牌"
        exec_time = time.strftime("%H:%M:%S", time.gmtime(end_time - self.start_time))
        self.log.info(f"执行完毕，{self.end_msg}，执行时间{exec_time}")
        return [
            self.title_msg,
            *self.msgs,
            self.end_msg + f"，执行时间{exec_time}",
        ]
