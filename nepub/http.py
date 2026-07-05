import hashlib
import urllib.request
from http.client import HTTPResponse
from importlib.metadata import version
from typing import cast

from nepub.type import Image

__version__ = version("nepub")

TIMEOUT_SECONDS = 10
IMAGE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
}


def _open(url: str) -> HTTPResponse:
    req = urllib.request.Request(url, headers={"User-agent": f"nepub/{__version__}"})
    # urlopen の戻り値の型は Any だが、http(s) では HTTPResponse が返る
    return cast(HTTPResponse, urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS))


def get(url: str) -> str:
    with _open(url) as res:
        return res.read().decode("utf-8")


def get_image(url: str) -> Image:
    with _open(url) as res:
        content_type = res.headers["Content-Type"]
        if content_type not in IMAGE_EXTENSIONS:
            raise ValueError(f"対応していない画像の形式です: {content_type}")
        data = res.read()
    # MD5 ハッシュ値をファイル名にする
    md5 = hashlib.md5(data).hexdigest()
    return {
        "type": content_type,
        "id": md5,
        "name": f"{md5}.{IMAGE_EXTENSIONS[content_type]}",
        "data": data,
    }
