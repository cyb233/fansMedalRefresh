import hashlib
import json
import time
import urllib.parse
import requests
from requests import cookies as requests_cookies
import qrcode
from rich.console import Console
from rich.panel import Panel
from pathlib import Path

console = Console()

APPKEY = "4409e2ce8ffd12b8"
APPSEC = "59b43e04ad6965f34319062b478f83dd"
LOGIN_FILE = Path("login_info.json")
ACCESS_TOKEN_FILE = Path("login_info.txt")

access_key = None
csrf = None
cookies = []


# =============== 工具函数 ===============
def md5(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def sign_params(params: dict):
    """计算签名"""
    params["appkey"] = APPKEY
    keys = sorted(params.keys())
    query = "&".join(f"{k}={urllib.parse.quote(str(params[k]))}" for k in keys)
    query_str = query + APPSEC
    params["sign"] = md5(query_str)
    return params


def map_to_string(params: dict) -> str:
    return "&".join(f"{k}={v}" for k, v in params.items())


# =============== 登录部分 ===============
def get_tv_qrcode_url_and_auth_code():
    api = "https://passport.bilibili.com/x/passport-tv-login/qrcode/auth_code"
    params = {"local_id": "0", "ts": str(int(time.time()))}
    sign_params(params)
    resp = requests.post(
        api,
        data=params,
        headers={
            "User-Agent": "Mozilla/5.0 BiliDroid/6.73.1 (bbcallen@gmail.com) os/android model/Mi 10 Pro mobi_app/android build/6731100 channel/xiaomi innerVer/6731110 osVer/12 network/2",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    resp.raise_for_status()
    data = resp.json()
    if data["code"] != 0:
        raise Exception("获取二维码失败: " + json.dumps(data, ensure_ascii=False))
    qrcode_url = data["data"]["url"]
    auth_code = data["data"]["auth_code"]
    return qrcode_url, auth_code


def verify_login(auth_code: str):
    api = "https://passport.bilibili.com/x/passport-tv-login/qrcode/poll"
    params = {"auth_code": auth_code, "local_id": "0", "ts": str(int(time.time()))}
    sign_params(params)

    while True:
        resp = requests.post(
            api,
            data=params,
            headers={
                "User-Agent": "Mozilla/5.0 BiliDroid/6.73.1 (bbcallen@gmail.com) os/android model/Mi 10 Pro mobi_app/android build/6731100 channel/xiaomi innerVer/6731110 osVer/12 network/2",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data["code"] == 0:
            console.print(Panel("✅ 登录成功", style="bold green"))
            access_token = data["data"]["access_token"]

            # 保存登录信息
            with open(LOGIN_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            with open(ACCESS_TOKEN_FILE, "w", encoding="utf-8") as f:
                f.write(access_token)
            console.print(f"AccessToken 已保存到 [cyan]{ACCESS_TOKEN_FILE}[/cyan]")
            return True
        else:
            console.print(f"等待扫码确认中...（{data['message']}）", style="yellow")
            time.sleep(3)


def is_login(cookies):
    """检测cookie是否有效"""
    if not cookies:
        return False, ""
    api = "https://api.bilibili.com/x/web-interface/nav"
    resp = requests.get(
        api,
        cookies={c.name: c.value for c in cookies},
        headers={
            "User-Agent": "Mozilla/5.0 BiliDroid/6.73.1 (bbcallen@gmail.com) os/android model/Mi 10 Pro mobi_app/android build/6731100 channel/xiaomi innerVer/6731110 osVer/12 network/2",
        },
    )
    data = resp.json()
    return data.get("code") == 0, data.get("data", {}).get("uname", "")


def login_bili():
    console.print(
        Panel(
            "请最大化终端窗口，以确保二维码完整显示，如果二维码显示乱码，请右击标题栏尝试更换字体显示",
            style="bold cyan",
        )
    )
    input("按回车继续...")

    qrcode_url, auth_code = get_tv_qrcode_url_and_auth_code()

    qr = qrcode.QRCode(border=1)
    qr.add_data(qrcode_url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    console.print(
        f"或使用手机 B 站 App 打开以下链接扫码登录：\n[yellow]{qrcode_url}[/yellow]"
    )
    verify_login(auth_code)


def load_login():
    """加载或扫码登录"""

    if not LOGIN_FILE.exists():
        console.print("未登录，开始扫码登录...", style="yellow")
        login_bili()
        return

    data = json.loads(LOGIN_FILE.read_text(encoding="utf-8"))
    cookie_list = data.get("data", {}).get("cookie_info", {}).get("cookies", [])
    cookies = [
        requests_cookies.create_cookie(name=c["name"], value=c["value"])
        for c in cookie_list
    ]

    for c in cookie_list:
        if c["name"] == "bili_jct":
            csrf = c["value"]

    ok, name = is_login(cookies)
    if ok:
        console.print(f"登录有效，欢迎回来 [green]{name}[/green]！")
    else:
        console.print("登录已失效，请重新扫码登录。", style="red")
        login_bili()


# =============== 主入口 ===============
if __name__ == "__main__":
    load_login()
    input("按回车退出...")
