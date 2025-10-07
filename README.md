# B 站粉丝牌点亮助手

> 🎯 自动点亮 B 站粉丝牌，支持弹幕与点赞两种方式，可多用户运行并支持多平台推送。

- [x] 允许配置多个用户
- [x] 仅未开播时弹幕点亮，开播后采用点赞点亮，避免影响主播
- [x] 多平台推送支持，具体参考[onepush](https://github.com/y1ndan/onepush)
- [x] 观看直播任务（测试性，未验证功能有效性，不过 30 亲密度太少了意义不大）

# 使用说明

1. 使用[Git](https://git-scm.com/downloads)克隆或直接[下载](https://github.com/cyb233/fansMedalRefresh/archive/refs/heads/main.zip)本项目

   ```bash
   git clone https://github.com/cyb233/fansMedalRefresh.git
   ```

2. 安装[Python](https://www.python.org/downloads/)（建议 3.x，未在 2.x 中进行过测试）
3. 复制配置文件示例`config.example.json`并重命名为`config.json`
4. 根据[配置说明](#配置说明)正确修改`config.json`
5. 安装依赖

   ```bash
   pip install -r requirements.txt
   ```

6. 运行项目

   ```bash
   python main.py
   ```

7. 如需定时运行，请选择：
   > 通常建议运行间隔为 24 小时，因为脚本设计至多运行 24 小时
   - **Windows**：任务计划程序
   - **Linux / macOS**：`cron` 定时任务等

# 配置说明

## log — 日志配置

| 字段      | 类型   | 默认值                                         | 说明                                                                                                                                                                                                                                                                                                           |
| --------- | ------ | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `enabled` | `bool` | `true`                                         | 是否启用日志文件输出                                                                                                                                                                                                                                                                                           |
| `level`   | `str`  | `"INFO"`                                       | 日志级别，可选：`TRACE` / `DEBUG` / `INFO` / `SUCCESS` / `WARNING` / `ERROR` / `CRITICAL`                                                                                                                                                                                                                      |
| `file`    | `str`  | `"log/fansMedalRefresh_{time:YYYY-MM-DD}.log"` | 日志文件路径，可使用 `{time:YYYY-MM-DD}` 自动生成日期文件名，可用参数参考[`Loguru`文档](https://loguru.readthedocs.io/en/stable/api/logger.html#loguru._logger.Logger.add#:~:text=The%20record%20is%20just%20a%20Python%20dict,See%20datetime.datetime)，建议保留`{time:YYYY-MM-DD}`以便配合默认保留 30 天日志 |

**说明：**  
启用后程序运行日志将写入文件，便于排查问题与记录任务执行情况

---

## users — 用户配置列表（必填）

用于存放每个账号的登录信息与白/黑名单设置，**至少需要一个用户配置**。

| 字段         | 类型        | 必填 | 默认值 | 说明                                 |
| ------------ | ----------- | ---- | ------ | ------------------------------------ |
| `cookie`     | `str`       | ✅   | 无     | 用户的 B 站登录 Cookie，用于接口验证 |
| `white_uids` | `List[int]` |      | `[]`   | 白名单 UID，仅这些用户会被操作       |
| `black_uids` | `List[int]` |      | `[]`   | 黑名单 UID，这些用户会被跳过         |

**验证规则：**

- `cookie` 不能为空，否则会触发配置错误

---

## like — 点赞配置

| 字段         | 类型   | 默认值 | 说明                 |
| ------------ | ------ | ------ | -------------------- |
| `enabled`    | `bool` | `true` | 是否启用自动点赞功能 |
| `like_count` | `int`  | `30`   | 每次点赞数量         |

**说明：**  
若关闭 (`enabled=false`)，程序将跳过点赞任务

---

## danmaku — 弹幕配置

| 字段            | 类型        | 默认值               | 说明                     |
| --------------- | ----------- | -------------------- | ------------------------ |
| `enabled`       | `bool`      | `true`               | 是否启用自动弹幕发送     |
| `min_interval`  | `int`       | `5`                  | 最小弹幕发送间隔（秒）   |
| `max_interval`  | `int`       | `10`                 | 最大弹幕发送间隔（秒）   |
| `danmaku_count` | `int`       | `10`                 | 每次发送弹幕数量         |
| `danmaku_list`  | `List[str]` | 默认提供 15 条颜文字 | 弹幕文本列表（随机发送） |

**说明：**

- 可自由自定义弹幕内容（表情、祝福语等）
- 弹幕内容为纯文本，建议控制长度

---

## live — 观看配置

| 字段                 | 类型   | 默认值 | 说明                                         |
| -------------------- | ------ | ------ | -------------------------------------------- |
| `enabled`            | `bool` | `true` | 是否启用自动观看功能                         |
| `policy`             | `int`  | `1`    | 观看策略：`1`=仅点亮牌子，`2`=完整观看亲密度 |
| `light_time`         | `int`  | `15`   | 点亮所需观看时长（分钟）                     |
| `full_affinity_time` | `int`  | `25`   | 完整观看亲密度所需时长（分钟）               |

**策略说明：**

- `policy=1`：快速点亮粉丝牌，时间短
- `policy=2`：完整观看提升亲密度，时间更长
- 注意：脚本默认单次运行最多 24 小时

---

## push — 推送配置

支持多个推送通道（如 Telegram、Discord、WechatWork、Lark、DingTalk、PushPlus 等），具体请参考[onepush](https://github.com/y1ndan/onepush)。

| 字段            | 类型   | 默认值  | 说明                                                                                         |
| --------------- | ------ | ------- | -------------------------------------------------------------------------------------------- |
| `provider_name` | `str`  | 无      | 推送服务提供商名称（必填）                                                                   |
| `proxies`       | `dict` | `null`  | 网络代理设置，如 `{'http': 'socks5h://127.0.0.1:1080', 'https': 'socks5h://127.0.0.1:1080'}` |
| `use_markdown`  | `bool` | `false` | 是否启用 Markdown 格式消息，启用后会对常见 Markdown 字符进行转义，避免出错                   |
| 其他字段        | `任意` | 无      | 推送服务特定参数，如 `token`、`userid`、`key` 等，具体请参考各通道文档                       |

**示例：Telegram 推送**

```json
{
  "provider_name": "telegram",
  "proxies": {
    "http": "socks5h://127.0.0.1:1080",
    "https": "socks5h://127.0.0.1:1080"
  },
  "use_markdown": true,
  "token": "your_token",
  "userid": "your_userid"
}
```

# 参考项目

[fansMedalHelper](https://github.com/XiaoMiku01/fansMedalHelper) — 本项目的灵感来源与参考实现
