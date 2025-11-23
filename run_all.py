#!/usr/bin/env python3
"""
统一启动脚本(机器人 + API + 前端)

功能说明:
- 并行启动 Telegram 机器人(由机器人入口负责 API 并行启动)与前端开发服务器
- 控制台日志与 Bot 保持一致的彩色排版

依赖安装(Windows):
- Python 依赖: pip install aiogram loguru
- 前端依赖: 在 `web` 目录执行 pnpm install 或 npm install

命名风格: 统一 snake_case
"""
import asyncio
import contextlib
import os
from pathlib import Path
import shutil
import socket
from loguru import logger

from bot.__main__ import main as bot_main


async def start_web_process() -> asyncio.subprocess.Process | None:
    """启动前端开发服务器

    功能说明:
    - 优先使用 `pnpm dev`，不可用时使用 `npm run dev`
    - 在 `web` 目录下启动并返回异步子进程对象

    输入参数:
    - 无

    返回值:
    - asyncio.subprocess.Process | None: 启动成功返回进程对象，失败返回 None
    """
    web_dir = Path(__file__).parent / "web"
    pnpm = shutil.which("pnpm")
    npm = shutil.which("npm")
    cmd = pnpm and "pnpm dev" or (npm and "npm run dev")
    if not cmd:
        logger.warning("⚠️ 未检测到 pnpm 或 npm，前端未启动")
        return None
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(web_dir),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        logger.info("🌐 前端启动任务已提交: {}", cmd)
        return proc
    except OSError as err:
        logger.error("❗ 前端启动失败: {}", err)
        return None


def read_web_port(default_port: int = 3000) -> int:
    """读取前端端口

    功能说明:
    - 从 `web/vite.config.ts` 的 `server.port` 解析端口，失败回退默认值

    输入参数:
    - default_port: 解析失败时返回的默认端口(默认 3000)

    返回值:
    - int: 端口号
    """
    cfg = Path(__file__).parent / "web" / "vite.config.ts"
    try:
        text = cfg.read_text(encoding="utf-8")
        import re
        m = re.search(r"server:\s*\{[\s\S]*?port:\s*(\d+)", text)
        if m:
            return int(m.group(1))
    except OSError:
        pass
    return default_port


def get_lan_ip() -> str | None:
    """获取局域网IP

    功能说明:
    - 通过UDP探测外网路由，获取本机局域网IP

    输入参数:
    - 无

    返回值:
    - str | None: 局域网IP，失败返回 None
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return None


async def tail_web_logs(proc: asyncio.subprocess.Process) -> None:
    """监听前端日志并输出地址

    功能说明:
    - 读取子进程标准输出，解析并输出 Local/Network 地址

    输入参数:
    - proc: 前端子进程对象

    返回值:
    - None
    """
    if not proc or not proc.stdout:
        return
    try:
        while True:
            line = await proc.stdout.readline()
            if not line:
                break
            text = line.decode(errors="ignore").strip()
            if "Local:" in text:
                start = text.find("http://")
                if start != -1:
                    url = text[start:].split()[0]
                    logger.info("🌐 Web 本地地址: {}", url)
            elif "Network:" in text:
                start = text.find("http://")
                if start != -1:
                    url = text[start:].split()[0]
                    logger.info("🌐 Web 局域网地址: {}", url)
    except (asyncio.CancelledError, UnicodeDecodeError) as err:
        logger.debug("监听前端日志失败: {}", err)


async def main() -> None:
    """入口函数

    功能说明:
    - 并行启动机器人与前端，日志样式由机器人入口统一配置

    输入参数:
    - 无

    返回值:
    - None
    """
    os.environ["BOOT_BANNER_LABEL"] = "Bot & API & Web"
    bot_task = asyncio.create_task(bot_main())
    await asyncio.sleep(0.2)
    web_proc = await start_web_process()
    tail_task = None
    if web_proc:
        tail_task = asyncio.create_task(tail_web_logs(web_proc))
        port = read_web_port(3000)
        logger.info("🌐 Web 本地地址: http://localhost:{}", port)
        ip = get_lan_ip()
        if ip:
            logger.info("🌐 Web 局域网地址: http://{}:{}", ip, port)
    try:
        await bot_task
    finally:
        if tail_task:
            tail_task.cancel()
        if web_proc and web_proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                web_proc.terminate()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 收到 Ctrl+C, 已安全退出")
