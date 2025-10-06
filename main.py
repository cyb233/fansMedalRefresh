#!/usr/bin/env python
# -*- coding: utf-8 -*-

__VERSION__ = "0.0.1"
from loguru import logger

import asyncio
import os
import sys

from src.config import Config
from src.user import BiliUser
from onepush import get_notifier

# 加载配置
config = Config.load_config("config.json")

# 配置日志
log_format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
logger.remove()
logger.add(
    sys.stdout,
    format=log_format,
    backtrace=True,
    diagnose=True,
    level=config.log.level.upper(),
)
log = logger.bind(user="B站粉丝牌助手")
# 添加日志文件
if config.log.enabled:
    log_file = os.path.join(os.path.dirname(__file__), config.log.file)
    logger.add(
        log_file,
        format=log_format,
        backtrace=True,
        diagnose=True,
        rotation="00:00",
        retention="30 days",
        level=config.log.level.upper(),
    )


@log.catch
async def main():
    log.info("程序版本: {}".format(__VERSION__))
    log.debug("执行配置", config)
    # 收集用户消息
    messageList = []
    # 执行用户相关操作
    tasks = []
    for user_cfg in config.users:
        user = BiliUser(user_cfg, config)
        tasks.append(user.start())
    try:
        messageList.extend(await asyncio.gather(*tasks))
    except Exception as e:
        log.exception(e)
        messageList.append(f"用户执行失败: {e}")
    title = "点亮B站粉丝牌-执行结果推送"
    content = "\n\n".join(messageList)
    # 推送
    log.info(f"推送内容：\n{title}\n\n{content}")
    for push_cfg in config.push:
        notifier = get_notifier(push_cfg.provider_name)
        if notifier:
            res = notifier.notify(
                proxies=push_cfg.proxies,
                **push_cfg._config,
                title=title,
                content=content,
            )
            log.info(f"使用 {push_cfg.provider_name} 推送结果: {res}")
        else:
            log.warning(f"未知的推送提供商: {push_cfg.provider_name}")


if __name__ == "__main__":
    log.info("任务开始")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
    loop.close()
    log.info("任务结束")
