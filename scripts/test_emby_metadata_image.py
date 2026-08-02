from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
from pathlib import Path
from typing import Any

import aiohttp

from bot.utils.emby import get_emby_client


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_local_image(path: Path) -> bytes:
    if not path.exists():
        raise FileNotFoundError(f"本地图片不存在: {path}")
    if not path.is_file():
        raise ValueError(f"图片路径不是文件: {path}")
    return path.read_bytes()


async def download_image(
    url: str,
    referer: str | None,
    archive_path: Path,
) -> bytes:
    headers = {
        "Referer": referer or f"{url.split('/', 3)[0]}//{url.split('/', 3)[2]}/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131.0 Safari/537.36"
        ),
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    }

    timeout = aiohttp.ClientTimeout(total=30)

    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers,
    ) as session:
        async with session.get(url) as response:
            body = await response.read()
            content_type = response.headers.get("Content-Type", "")

            print(f"[下载] HTTP 状态: {response.status}")
            print(f"[下载] Content-Type: {content_type}")
            print(f"[下载] 响应字节数: {len(body)}")
            print(f"[下载] Referer: {headers['Referer']}")

            if response.status >= 400:
                preview = body[:300].decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"图片下载失败: HTTP {response.status}, 响应内容: {preview}"
                )

            if not body:
                raise RuntimeError("图片响应为空")

            if "text/html" in content_type.lower():
                preview = body[:300].decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"下载到的不是图片，而是 HTML 页面: {preview}"
                )

    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(body)

    print(f"[归档] 保存路径: {archive_path.resolve()}")
    print(f"[归档] 文件存在: {archive_path.exists()}")
    print(f"[归档] 文件大小: {archive_path.stat().st_size}")
    print(f"[归档] SHA256: {sha256_bytes(body)}")

    return body


def get_image_tags(item: dict[str, Any]) -> dict[str, Any]:
    image_tags = item.get("ImageTags")
    return image_tags if isinstance(image_tags, dict) else {}


async def get_item_tags(
    client: Any,
    user_id: str,
    item_id: str,
) -> dict[str, Any]:
    item = await client.get_item(user_id, item_id)
    if not item:
        raise RuntimeError(f"Emby 找不到 Item: {item_id}")

    tags = get_image_tags(item)
    print(f"[Emby] Item ID: {item_id}")
    print(f"[Emby] Name: {item.get('Name')}")
    print(f"[Emby] ImageTags: {tags}")
    print(f"[Emby] Primary: {tags.get('Primary')}")
    return tags


async def upload_image(
    client: Any,
    user_id: str,
    item_id: str,
    image_bytes: bytes,
    image_type: str,
) -> None:
    before_tags = await get_item_tags(client, user_id, item_id)
    before_primary = before_tags.get(image_type)

    encoded = base64.b64encode(image_bytes).decode("ascii")
    print(f"[上传] 目标 Item: {item_id}")
    print(f"[上传] 图片类型: {image_type}")
    print(f"[上传] Base64 长度: {len(encoded)}")
    print("[上传] 开始调用 Emby upload_item_image ...")

    result = await client.upload_item_image(
        item_id,
        encoded,
        image_type,
    )
    print(f"[上传] 接口返回值: {result!r}")

    await asyncio.sleep(2)

    after_tags = await get_item_tags(client, user_id, item_id)
    after_primary = after_tags.get(image_type)

    print(f"[验证] 上传前 {image_type}: {before_primary}")
    print(f"[验证] 上传后 {image_type}: {after_primary}")

    if after_primary and after_primary != before_primary:
        print(f"[验证] 成功: {image_type} 图片哈希已变化")
    elif after_primary:
        print(f"[验证] Emby 返回了 {image_type} 哈希，但哈希没有变化")
    else:
        print(f"[验证] 失败: Emby 没有返回 {image_type} 图片哈希")


async def main(args: argparse.Namespace) -> None:
    client = get_emby_client()
    if client is None:
        raise RuntimeError("Emby 未配置，请检查 Emby 地址和 API Key")

    users, _ = await client.get_users(limit=1)
    if not users or not users[0].get("Id"):
        raise RuntimeError("Emby 没有可用于读取 Item 的用户")

    user_id = str(users[0]["Id"])
    print(f"[连接] 使用 Emby 用户: {user_id}")

    if args.image_path:
        image_path = Path(args.image_path)
        image_bytes = read_local_image(image_path)
        print(f"[输入] 使用本地图片: {image_path.resolve()}")
        print(f"[输入] 文件大小: {len(image_bytes)}")
        print(f"[输入] SHA256: {sha256_bytes(image_bytes)}")

        archive_path = Path(args.archive_path)
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(image_bytes)
        print(f"[归档] 本地图片已复制到: {archive_path.resolve()}")
    elif args.image_url:
        image_bytes = await download_image(
            args.image_url,
            args.referer,
            Path(args.archive_path),
        )
    else:
        raise ValueError("必须提供 --image-path 或 --image-url")

    await upload_image(
        client=client,
        user_id=user_id,
        item_id=args.item_id,
        image_bytes=image_bytes,
        image_type=args.image_type,
    )

    await client.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="独立测试图片下载、归档和 Emby 图片更新",
    )
    parser.add_argument(
        "--item-id",
        required=True,
        help="Emby 影片或角色 Item ID",
    )
    parser.add_argument(
        "--image-type",
        default="Primary",
        choices=("Primary", "Backdrop", "Logo", "Thumb"),
        help="Emby 图片类型",
    )
    parser.add_argument(
        "--image-url",
        help="远程图片地址",
    )
    parser.add_argument(
        "--image-path",
        help="本地图片路径",
    )
    parser.add_argument(
        "--referer",
        default="https://www.ck-download.com/",
        help="远程图片下载 Referer",
    )
    parser.add_argument(
        "--archive-path",
        default="data/emby_metadata/images/manual/test-image.jpg",
        help="图片归档路径",
    )
    return parser


if __name__ == "__main__":
    parser = build_parser()
    parsed_args = parser.parse_args()

    if bool(parsed_args.image_url) == bool(parsed_args.image_path):
        parser.error("--image-url 和 --image-path 必须二选一")

    asyncio.run(main(parsed_args))