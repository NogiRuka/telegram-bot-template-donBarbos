#!/usr/bin/env python3
"""
统一启动脚本(机器人 + API 服务 + 前端)

功能说明:
- 并行启动 Telegram 机器人(轮询模式)、FastAPI 服务(为前端提供数据接口)以及前端开发服务器
- 启动后以中文打印各服务地址与状态, 数据库地址进行脱敏输出

依赖安装(Windows):
- Python 依赖: pip install aiogram aiohttp[speedups] loguru pydantic pydantic-settings
  sqlalchemy aiomysql pymysql cachetools orjson alembic
- 前端依赖(在 `web` 目录): 建议安装 pnpm 或使用 npm, 首次运行需要 `pnpm install` 或 `npm install`

命名风格: 统一 snake_case
"""
import asyncio
import contextlib
import logging
import re
import shutil
import socket
import sys
import time
from pathlib import Path

import aiohttp
import uvicorn
from aiogram.exceptions import TelegramAPIError

from api.app import app as api_app
from api.app import quiet_uvicorn_logs

from bot.__main__ import main as bot_main
from bot.core.config import settings as core_settings
from bot.core.loader import bot as core_bot

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def mask_database_url(url: str) -> str:
    """数据库URL脱敏

    功能说明:
    - 对包含账户密码的数据库URL进行脱敏, 隐藏密码部分

    输入参数:
    - url: 数据库连接URL字符串

    返回值:
    - 脱敏后的URL字符串
    """
    at = url.find("@")
    scheme_end = url.find("://")
    if at == -1 or scheme_end == -1:
        return url
    cred = url[scheme_end + 3 : at]
    if ":" in cred:
        user = cred.split(":", 1)[0]
        masked = f"{user}:***"
    else:
        masked = cred
    return url[: scheme_end + 3] + masked + url[at:]


def read_web_port(default_port: int = 5173) -> int:
    """读取前端开发服务器端口

    功能说明:
    - 从 `web/vite.config.ts` 中解析 `server.port`, 若失败则返回默认端口

    输入参数:
    - default_port: 解析失败时使用的默认端口(默认 5173)

    返回值:
    - 端口号(int)
    """
    vite_config = project_root / "web" / "vite.config.ts"
    try:
        text = vite_config.read_text(encoding="utf-8")
        m = re.search(r"server:\s*\{[\s\S]*?port:\s*(\d+)", text)
        if m:
            return int(m.group(1))
    except OSError as err:
        logging.getLogger(__name__).debug("读取 vite 配置失败: %s", err)
    return default_port


async def start_bot() -> None:
    """启动 Telegram 机器人(轮询模式)

    功能说明:
    - 调用 `bot.__main__.main()` 在当前事件循环中以轮询模式运行机器人

    输入参数:
    - 无

    返回值:
    - None
    """
    await bot_main()


async def start_api() -> None:
    """启动 FastAPI 服务

    功能说明:
    - 使用 `uvicorn.Server` 在当前事件循环中运行 API 服务

    输入参数:
    - 无

    返回值:
    - None
    """
    port = ensure_free_port(core_settings.API_HOST, core_settings.API_PORT)
    globals()["runtime_api_port"] = port
    globals()["start_time_api"] = time.monotonic()

    quiet_uvicorn_logs()
    config = uvicorn.Config(
        api_app,
        host=core_settings.API_HOST,
        port=port,
        reload=False,
        log_level="warning",
        access_log=False,
        log_config=None,
    )
    server = uvicorn.Server(config)
    await server.serve()


async def start_web_process() -> asyncio.subprocess.Process | None:
    """启动前端开发服务器(Vite)

    功能说明:
    - 优先使用 `pnpm dev`, 如果不可用则尝试 `npm run dev`
    - 在 `web` 目录下启动并返回子进程对象

    输入参数:
    - 无

    返回值:
    - 子进程对象(Process), 若无法启动则返回 None
    """
    web_dir = project_root / "web"
    try:
        (project_root / "logs" / "web").mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    pnpm = shutil.which("pnpm")
    npm = shutil.which("npm")

    if pnpm:
        cmd = "pnpm dev"
    elif npm:
        cmd = "npm run dev"
    else:
        return None

    globals()["start_time_web"] = time.monotonic()
    return await asyncio.create_subprocess_shell(
        cmd,
        cwd=str(web_dir),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


async def tail_web_logs(proc: asyncio.subprocess.Process) -> None:
    """监听前端日志并解析实际端口

    功能说明:
    - 读取前端开发服务器子进程的标准输出, 解析其中的本地地址行, 提取并保存实际端口

    输入参数:
    - proc: 前端子进程对象

    返回值:
    - None
    """
    if not proc or not proc.stdout:
        return
    try:
        log_path = project_root / "logs" / "web" / "web-dev.log"
        f = log_path.open("a", encoding="utf-8", errors="ignore")
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode(errors="ignore").strip()
            try:
                f.write(text + "\n")
                f.flush()
            except OSError:
                pass
            m = re.search(r"Local:\s*http://localhost:(\d+)", text)
            if m:
                port = int(m.group(1))
                globals()["runtime_web_port"] = port
                globals()["runtime_web_ready_time"] = time.monotonic()
            m2 = re.search(r"Network:\s*(http://[\w\.-]+:\d+)", text)
            if m2:
                globals()["runtime_web_network"] = m2.group(1)
    except (asyncio.CancelledError, UnicodeDecodeError, OSError) as err:
        logging.getLogger(__name__).debug("监听前端日志失败: %s", err)
    finally:
        try:
            f.close()
        except Exception:
            pass


async def print_summary() -> None:
    """打印统一服务清单(中文)

    功能说明:
    - 汇总并打印: 机器人信息(用户名/ID)、API 服务地址、前端地址、数据库脱敏地址、日志位置

    输入参数:
    - 无

    返回值:
    - None
    """
    api_settings = core_settings
    bot_settings = core_settings
    bot = core_bot

    try:
        me = await bot.get_me()
        bot_desc = f"运行中(@{me.username}, ID={me.id})"
    except (TelegramAPIError, aiohttp.ClientError, asyncio.TimeoutError) as err:
        logging.getLogger(__name__).debug("获取机器人信息失败: %s", err)
        bot_desc = "运行中(信息获取失败)"

    runtime_port = globals().get("runtime_web_port")
    web_port = int(runtime_port) if runtime_port else read_web_port(default_port=3000)
    web_url = f"http://localhost:{web_port}"
    any_addr_v4 = "0.0.0.0"
    api_host = api_settings.API_HOST if any_addr_v4 != api_settings.API_HOST else "localhost"
    api_port = globals().get("runtime_api_port", api_settings.API_PORT)
    api_url = f"http://{api_host}:{api_port}"

    api_status, api_probe_ms = await probe_api_with_time(api_url)
    api_status_text = "运行中" if api_status else "启动失败"

    # 使用顶部定义的表格工具函数

    # 启动耗时(秒)
    bot_cost = None
    if globals().get("start_time_bot"):
        bot_cost = max(0.0, time.monotonic() - globals()["start_time_bot"])  # 近似
    api_cost = None
    if globals().get("start_time_api"):
        api_cost = api_probe_ms / 1000.0 if api_status else max(0.0, time.monotonic() - globals()["start_time_api"])
    web_cost = None
    if globals().get("start_time_web") and globals().get("runtime_web_ready_time"):
        web_cost = max(0.0, globals()["runtime_web_ready_time"] - globals()["start_time_web"])
    # 使用顶部的 with_cost 工具函数

    network_info: str | None = None
    if globals().get("runtime_web_network"):
        network_info = f"(网络: {globals()['runtime_web_network']})"
    [
        ["机器人", "轮询(无端口)", "运行中", with_cost(bot_desc, bot_cost)],
        ["API", api_url, api_status_text, with_cost(get_api_extra_info(api_url), api_cost)],
        [
            "前端",
            web_url if not network_info else f"{web_url}{network_info}",
            "开发中" if globals().get("web_proc_started") else "未启动",
            with_cost("开发端口", web_cost),
        ],
        ["数据库", mask_database_url(bot_settings.database_url), "可用", "连接(已脱敏)"],
        ["日志", "logs/bot/bot.log; logs/api/api.log; logs/web/web-dev.log", "可用", "文件输出"],
    ]


def get_api_extra_info(api_url: str) -> str:
    """API附加信息

    功能说明:
    - 返回 API 健康检查路径、版本号与路由数量摘要(中文)

    输入参数:
    - api_url: API 基础地址

    返回值:
    - 字符串, 包含健康检查路径、版本与路由数量
    """
    version = getattr(api_app, "version", "unknown")
    routes = [r for r in getattr(api_app, "routes", []) if getattr(r, "path", None)]
    return f"健康检查: {api_url}/health; 版本 v{version}; 路由 {len(routes)}"


async def run_all() -> None:
    """并行启动机器人、API 与前端

    功能说明:
    - 并行启动三个服务, 并打印统一中文服务清单
    - 捕获 Ctrl+C(KeyboardInterrupt)进行优雅关闭

    输入参数:
    - 无

    返回值:
    - None
    """
    setup_logging_quiet()

    globals()["start_time_bot"] = time.monotonic()
    bot_task = asyncio.create_task(start_bot())
    api_task = asyncio.create_task(start_api())
    web_proc = await start_web_process()
    globals()["web_proc_started"] = bool(web_proc)
    if web_proc:
        globals()["tail_web_task"] = asyncio.create_task(tail_web_logs(web_proc))

    await asyncio.sleep(3)
    await print_summary()

    try:
        await asyncio.gather(bot_task, api_task)
    except asyncio.CancelledError:
        pass
    finally:
        if web_proc and web_proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                web_proc.terminate()


def setup_logging_quiet() -> None:
    """统一压低噪音日志等级

    功能说明:
    - 将 SQLAlchemy 引擎日志降至 WARNING, 避免控制台出现大量 SQL 语句
    - 可按需扩展其他第三方库日志等级

    输入参数:
    - 无

    返回值:
    - None
    """
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def ensure_free_port(host: str, preferred_port: int) -> int:
    """确保端口可用, 不可用时向上递增查找

    功能说明:
    - 尝试绑定指定端口, 失败则递增端口号直至成功(最多 +10)

    输入参数:
    - host: 绑定主机
    - preferred_port: 首选端口

    返回值:
    - 实际可用端口
    """
    any_addr_v4 = "0.0.0.0"
    host_probe = "127.0.0.1" if host == any_addr_v4 else host
    port = preferred_port
    for _ in range(11):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host_probe, port))
            except OSError:
                port += 1
            else:
                return port
    return preferred_port


async def probe_api(api_url: str) -> bool:
    """探测 API 健康状态

    功能说明:
    - 访问 API 的 /health, 判断是否返回 200

    输入参数:
    - api_url: API 基础地址

    返回值:
    - bool: 运行状态
    """
    try:
        async with aiohttp.ClientSession() as session, session.get(f"{api_url}/health", timeout=3) as resp:
            http_ok = 200
            return resp.status == http_ok
    except (aiohttp.ClientError, asyncio.TimeoutError) as err:
        logging.getLogger(__name__).debug("探测 API 失败: %s", err)
        return False


async def probe_api_with_time(api_url: str) -> tuple[bool, int]:
    """探测 API 健康状态并返回耗时(毫秒)

    功能说明:
    - 访问 API 的 /health, 返回状态与请求耗时

    输入参数:
    - api_url: API 基础地址

    返回值:
    - (bool, int): (运行状态, 耗时毫秒)
    """
    start = time.monotonic()
    ok = await probe_api(api_url)
    cost_ms = int((time.monotonic() - start) * 1000)
    return ok, cost_ms


# (移除重复定义)


def main() -> None:
    """入口函数

    功能说明:
    - 在新的事件循环中执行 `run_all`

    输入参数:
    - 无

    返回值:
    - None
    """
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(run_all())


if __name__ == "__main__":
    main()
def is_cjk(ch: str) -> bool:
    """判断字符是否为 CJK 宽字符

    功能说明:
    - 基于正则判断中日韩统一表意文字等区段

    输入参数:
    - ch: 单个字符

    返回值:
    - bool: 是否为宽字符
    """
    return bool(re.match(r"[\u2E80-\u9FFF\uF900-\uFAFF\uFF00-\uFFEF]", ch))


def display_width(s: str) -> int:
    """计算字符串的显示宽度

    功能说明:
    - CJK 字符宽度记为 2, 其他记为 1

    输入参数:
    - s: 字符串

    返回值:
    - 宽度数值
    """
    w = 0
    for ch in str(s):
        w += 2 if is_cjk(ch) else 1
    return w


def pad_str(s: str, target: int) -> str:
    """右侧补空格到目标宽度

    功能说明:
    - 若当前宽度不足, 按显示宽度计算补齐

    输入参数:
    - s: 字符串
    - target: 目标宽度

    返回值:
    - 补齐后的字符串
    """
    cur = display_width(s)
    if cur >= target:
        return str(s)
    return str(s) + " " * (target - cur)


def center_str(s: str, target: int) -> str:
    """居中至目标宽度

    功能说明:
    - 依据显示宽度计算左右填充空格

    输入参数:
    - s: 字符串
    - target: 目标宽度

    返回值:
    - 居中后的字符串
    """
    cur = display_width(s)
    if cur >= target:
        return str(s)
    left = (target - cur) // 2
    right = target - cur - left
    return (" " * left) + str(s) + (" " * right)


def format_table(headers: list[str], rows: list[list[str]]) -> str:
    """格式化为对齐的表格字符串

    功能说明:
    - 兼容中英文宽度, 按显示宽度对齐列, 表头居中

    输入参数:
    - headers: 列头列表
    - rows: 行内容列表

    返回值:
    - 格式化后的表格字符串
    """
    fixed_widths = [8, 40, 8, 32]
    cols = list(zip(*([headers, *rows]), strict=False))
    auto_widths = [max(display_width(cell) for cell in col) for col in cols]
    widths = [max(a, f) for a, f in zip(auto_widths, fixed_widths, strict=False)]

    def fmt(row: list[str]) -> str:
        cells = [pad_str(cell, w) for cell, w in zip(row, widths, strict=False)]
        return " | ".join(cells)

    header = " | ".join(center_str(h, w) for h, w in zip(headers, widths, strict=False))
    sep = "-" * len(header)
    lines = [header, sep] + [fmt(r) for r in rows]
    return "\n".join(lines)


def with_cost(desc: str, cost: float | None) -> str:
    """附加耗时描述

    功能说明:
    - 若提供耗时(秒), 在描述后以"(约 x.xs)"追加

    输入参数:
    - desc: 原始描述
    - cost: 耗时(秒), 可为 None

    返回值:
    - 拼接后的描述字符串
    """
    return desc if cost is None else f"{desc}(约 {cost:.1f}s)"
