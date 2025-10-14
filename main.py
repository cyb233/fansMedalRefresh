#!/usr/bin/env python
# -*- coding: utf-8 -*-

__VERSION__ = "0.0.1"
import re
from loguru import logger

import asyncio
import os
import sys

from requests import Response

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
log = logger.bind(user="B站粉丝牌点亮助手")
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


def escape_markdown(text: str) -> str:
    """
    转义 Markdown 特殊字符
    """
    special_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special_chars)}])", r"\\\1", text)


async def push_results(messageList: list[list[str]]):
    """
    推送执行结果
    """
    title_raw = "B站粉丝牌点亮助手 - 执行结果推送"
    content_raw = "\n\n".join("\n".join(row) for row in messageList)

    log.info(f"推送内容：\n{title_raw}\n\n{content_raw}")
    for push_cfg in config.push:
        notifier = get_notifier(push_cfg.provider_name)
        if not notifier:
            log.warning(f"未知的推送提供商: {push_cfg.provider_name}")
            continue

        title = (
            f"*{escape_markdown(title_raw)}*" if push_cfg.use_markdown else title_raw
        )
        content = (
            "\n\n".join(
                (
                    "_{}_".format(escape_markdown(row[0]))
                    if row[0]
                    else row[0]
                    + "".join(f"\n> {escape_markdown(line)}" for line in row[1:])
                )
                for row in messageList
                if row
            )
            if push_cfg.use_markdown
            else content_raw
        )

        log.debug(f"使用 {push_cfg.provider_name} 推送：{title}\n\n{content}")

        try:
            res: Response = notifier.notify(
                proxies=push_cfg.proxies,
                **push_cfg._config,
                title=title,
                content=content,
            )
            log.info(f"使用 {push_cfg.provider_name} 推送结果: {res}")
            if not res.ok:
                log.warning(
                    f"推送失败：{res.status_code} {res.reason}\nurl: {res.request.url}\nbody: {res.request.body}\nresp: {res.text}"
                )
        except Exception as e:
            log.exception(f"推送 {push_cfg.provider_name} 时发生异常：{e}")


@log.catch
async def main():
    log.info("程序版本: {}".format(__VERSION__))
    log.debug("执行配置：{}", config)
    # 收集用户消息
    messageList = []
    # 执行用户相关操作
    tasks = []
    lives = []
    msgs = []
    try:
        for user_cfg in config.users:
            if not user_cfg.enabled: continue # 跳过未启用
            user = BiliUser(user_cfg, config)
            await user.check_login()
            tasks.append(user.like_and_danmaku())
            lives.append(user.watch_live())
            msgs.append(user.collect_msgs())
        await asyncio.gather(*tasks, return_exceptions=True)
        await asyncio.gather(*lives, return_exceptions=True)
    except Exception as e:
        log.exception(e)
        messageList.append([f"用户执行失败: {e}"])
    finally:
        results = await asyncio.gather(*msgs, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception):
                messageList.append([f"消息收集异常: {r}"])
            elif r:
                messageList.append(r)
    return messageList


if __name__ == "__main__":
    log.info("任务开始")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    messageList = []
    try:
        messageList = loop.run_until_complete(
            asyncio.wait_for(main(), timeout=24 * 60 * 60)
        )
    except asyncio.TimeoutError:
        log.warning("任务超时：已运行 24 小时，自动终止。")
        messageList.append(["任务超时：运行超过 24 小时"])
    finally:
        try:
            loop.run_until_complete(push_results(messageList))
        except Exception as e:
            log.exception("推送阶段出现异常：{}", e)
        finally:
            loop.close()
            log.info("任务结束")
