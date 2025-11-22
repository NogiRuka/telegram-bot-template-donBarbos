"""
API服务主应用
独立的 FastAPI 应用, 为 React 前端提供数据接口
位于 bot 目录下, 可直接调用 bot 的数据库操作
"""
from __future__ import annotations
import time
from contextlib import asynccontextmanager
from pathlib import Path
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import logging

from api.routes import admins, dashboard, users, webhooks

from bot.core.config import settings

def print_boot_banner(service_name: str) -> None:
    """打印启动 Banner（每次启动）

    功能说明：
    - 读取 `assets/banner.txt` 文本内容并打印到日志（控制台与文件）
    - 不使用任何标记文件，每次进程启动都会打印一次

    输入参数：
    - service_name: 服务名称说明（例如 "API"、"Bot"），用于日志定位

    返回值：
    - None
    """
    try:
        banner_path = Path("assets/banner.txt")
        text = ""
        if banner_path.exists():
            try:
                text = banner_path.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                logger.warning("读取 banner 失败: {}", e)
        info_lines = build_start_info_lines(service_name)
        width = _calc_banner_width(text, info_lines)
        formatted_info = _center_lines(width, info_lines)
        if text:
            logger.info("\n{}\n{}", text, formatted_info)
        else:
            logger.info("{}", formatted_info)
    except Exception:
        # 忽略打印失败，保证启动不中断
        pass


def build_start_info_lines(module_name: str) -> list[str]:
    """构建启动项目信息行（精简版）

    功能说明：
    - 仅返回两行信息：项目名与模块名，用于在 banner 下方显示

    输入参数：
    - module_name: 模块名称（例如 "API"、"Bot"）

    返回值：
    - list[str]: 信息行列表
    """
    try:
        project = "Telegram Bot Admin"
        return [f"项目: {project}", f"模块: {module_name}"]
    except Exception:
        return ["项目: Telegram Bot Admin", f"模块: {module_name}"]


def get_project_version() -> str:
    """读取项目版本号

    功能说明：
    - 从项目根目录的 `pyproject.toml` 中解析 `[project] version` 字段

    输入参数：
    - 无

    返回值：
    - str: 版本号字符串，解析失败返回 `unknown`
    """
    try:
        root = Path(__file__).absolute().parent.parent
        py = root / "pyproject.toml"
        if not py.exists():
            return "unknown"
        text = py.read_text(encoding="utf-8", errors="ignore")
        for line in text.splitlines():
            s = line.strip()
            if s.startswith("version = "):
                val = s.split("=", 1)[1].strip().strip('"').strip("'")
                return val or "unknown"
        return "unknown"
    except Exception:
        return "unknown"


def mask_database_url(url: str) -> str:
    """数据库URL脱敏

    功能说明：
    - 对包含账户密码的数据库URL进行脱敏，隐藏密码部分

    输入参数：
    - url: 数据库连接URL字符串

    返回值：
    - 脱敏后的URL字符串
    """
    try:
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
    except Exception:
        return url


def _calc_banner_width(text: str, info_lines: list[str]) -> int:
    """计算用于对齐的宽度

    功能说明：
    - 根据 banner 文本的最长行长度与信息行长度，确定对齐宽度

    输入参数：
    - text: banner 原始文本
    - info_lines: 需对齐的信息行

    返回值：
    - int: 对齐宽度（字符数）
    """
    try:
        banner_lines = [ln.rstrip() for ln in text.splitlines()] if text else []
        banner_width = max((len(ln) for ln in banner_lines), default=0)
        info_width = max((len(ln) for ln in info_lines), default=0)
        return max(banner_width, info_width)
    except Exception:
        return max((len(ln) for ln in info_lines), default=0)


def _center_lines(width: int, lines: list[str]) -> str:
    """将信息行按指定宽度居中对齐

    功能说明：
    - 为每一行计算左侧缩进，使其在给定宽度下居中

    输入参数：
    - width: 对齐宽度
    - lines: 待对齐的文本行

    返回值：
    - str: 对齐后的多行文本
    """
    try:
        centered = []
        for ln in lines:
            ln = ln.rstrip()
            pad = max(0, (width - len(ln)) // 2)
            centered.append(" " * pad + ln)
        return "\n".join(centered)
    except Exception:
        return "\n".join(lines)

def setup_api_logging() -> None:
    """初始化 API 文件日志

    功能说明:
    - 创建 `logs/api` 目录并添加 loguru 文件日志输出
    - 根据 `API_DEBUG` 设置日志等级

    输入参数:
    - 无

    返回值:
    - None
    """
    try:
        Path("logs/api").mkdir(parents=True, exist_ok=True)
        logger.add(
            "logs/api/api.log",
            level="DEBUG" if settings.API_DEBUG else "INFO",
            format="{time} | {level} | {module}:{function}:{line} | {message}",
            rotation="100 KB",
            compression="zip",
        )
    except Exception:
        # 避免日志初始化失败影响服务启动
        pass

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    应用生命周期管理

    功能说明:
    - 应用启动与关闭时打印日志

    输入参数:
    - app: FastAPI 应用实例

    返回值:
    - None
    """
    del app
    logger.info("API 服务启动中...")
    yield None
    logger.info("API 服务关闭中...")


def create_app() -> FastAPI:
    """
    创建FastAPI应用实例

    Returns:
        FastAPI: 配置好的FastAPI应用实例
    """
    setup_api_logging()
    print_boot_banner("API")
    app = FastAPI(
        title="Telegram Bot Admin API",
        description="为Telegram Bot管理界面提供的API服务",
        version="1.0.0",
        lifespan=lifespan
    )

    # 配置CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.get_api_allowed_origins(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
    app.include_router(users.router, prefix="/api", tags=["users"])
    app.include_router(admins.router, prefix="/api", tags=["admins"])
    app.include_router(webhooks.router, prefix="/api", tags=["webhooks"])
    app.add_api_route("/", webhooks.handle_emby_webhook, methods=["POST"], tags=["webhooks"])

    @app.middleware("http")
    async def log_requests(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        请求日志中间件

        功能说明:
        - 在开发阶段输出每个 API 请求的基本信息, 包括方法、路径、状态码与耗时

        输入参数:
        - request: 请求对象
        - call_next: 下游处理器

        返回值:
        - Response: 响应对象
        """
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as err:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.exception(
                "API {method} {path} error after {ms}ms: {err}",
                method=request.method,
                path=request.url.path,
                ms=duration_ms,
                err=err,
            )
            raise
        else:
            duration_ms = int((time.monotonic() - start) * 1000)
            client = request.client.host if request.client else "-"
            logger.info(
                "API {method} {path} -> {status} {ms}ms from {client}",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                ms=duration_ms,
                client=client,
            )
            return response

    @app.get("/")
    async def root() -> dict[str, str]:
        """
        根路径健康检查

        功能说明:
        - 返回服务运行状态

        输入参数:
        - 无

        返回值:
        - dict[str, str]: 服务状态信息
        """
        return {"message": "Telegram Bot Admin API", "status": "running"}

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """
        健康检查端点

        功能说明:
        - 返回健康检查状态

        输入参数:
        - 无

        返回值:
        - dict[str, str]: 健康状态信息
        """
        return {"status": "healthy"}

    return app


def quiet_uvicorn_logs() -> None:
    """压低 Uvicorn 日志等级

    功能说明:
    - 将 'uvicorn' 与 'uvicorn.error' 日志等级设为 WARNING
    - 禁用 'uvicorn.access' 访问日志, 避免重复输出

    输入参数:
    - 无

    返回值:
    - None
    """
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").disabled = True


def get_uvicorn_log_config() -> dict[str, object]:
    """生成 Uvicorn 日志配置(压低噪音)

    功能说明:
    - 设置 'uvicorn' 与 'uvicorn.error' 为 WARNING 等级并输出到控制台
    - 移除 'uvicorn.access' 的处理器, 禁止访问日志传播

    输入参数:
    - 无

    返回值:
    - dict[str, object]: logging 配置字典
    """
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {"format": "%(levelname)s: %(message)s"}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            }
        },
        "root": {"level": "WARNING", "handlers": ["console"]},
        "loggers": {
            "uvicorn": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "uvicorn.error": {"level": "WARNING", "handlers": ["console"], "propagate": False},
            "uvicorn.access": {"level": "WARNING", "handlers": [], "propagate": False},
        },
    }


# 创建应用实例
app = create_app()


if __name__ == "__main__":
    import uvicorn

    logger.info(f"启动API服务在 http://{settings.API_HOST}:{settings.API_PORT}")
    quiet_uvicorn_logs()
    uvicorn.run(
        "api.app:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="warning" if not settings.API_DEBUG else "debug",
        access_log=False,
        log_config=None,
    )
