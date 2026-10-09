import hashlib
import time
import urllib.request
from collections.abc import Callable
from importlib.metadata import version

from nepub.type import Image

__version__ = version("nepub")


def get(url: str):
    headers = {"User-agent": f"nepub/{__version__}"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as res:
        return res.read().decode("utf-8")


def throttle(fetch: Callable[[str], str], interval: float) -> Callable[[str], str]:
    """2 回目以降の呼び出しの前に interval 秒待つようにする (サーバーに負荷をかけないため)"""
    called = False

    def throttled(url: str) -> str:
        nonlocal called
        if called:
            time.sleep(interval)
        called = True
        return fetch(url)

    return throttled


def get_image(url: str) -> Image:
    headers = {"User-agent": f"nepub/{__version__}"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as res:
        content_type = res.headers["Content-Type"]
        img_data = res.read()
        if content_type == "image/jpeg":
            img_ext = "jpg"
        elif content_type == "image/png":
            img_ext = "png"
        elif content_type == "image/gif":
            img_ext = "gif"
        else:
            raise Exception(f"対応していない画像の形式です: {content_type}")
        img_md5 = hashlib.md5(img_data).hexdigest()
        # MD5 ハッシュ値をファイル名にする
        img_name = f"{img_md5}.{img_ext}"
        return {
            "type": content_type,
            "id": img_md5,
            "name": img_name,
            "data": img_data,
        }
