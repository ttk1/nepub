import json
import os
import re
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from typing import IO

from jinja2 import Environment, PackageLoader

from nepub.type import Chapter, Episode, Image, Metadata, MetadataImage

env = Environment(
    loader=PackageLoader("nepub"),
    # データ取得の際にエスケープ加工するので
    # ここではエスケープしない
    autoescape=False,
)
template_content = env.get_template("content.opf")
template_navigation = env.get_template("navigation.xhtml")
template_text = env.get_template("text.xhtml")

# EPUB 内のファイル名に使ってよい文字列 (エピソード ID, 画像ファイル名)
# パストラバーサルやテンプレートへの埋め込みで問題が起きないよう英数字等に限る
SAFE_NAME_PATTERN = re.compile(r"[0-9A-Za-z_-]+(\.[0-9A-Za-z]+)?")


def content(
    title: str,
    author: str,
    timestamp: str,
    episodes: list[Episode],
    images: list[MetadataImage],
):
    return template_content.render(
        {
            "title": title,
            "author": author,
            "timestamp": timestamp,
            "episodes": episodes,
            "images": images,
        }
    )


def nav(chapters: list[Chapter]):
    return template_navigation.render({"chapters": chapters})


def text(title: str, paragraphs: list[str]):
    return template_text.render({"title": title, "paragraphs": paragraphs})


def container():
    return resources.files("nepub.files").joinpath("container.xml").read_text("utf-8")


def style():
    return resources.files("nepub.files").joinpath("style.css").read_text("utf-8")


def read_metadata(path: str) -> Metadata:
    with zipfile.ZipFile(path, "r") as zf:
        with zf.open("src/metadata.json") as f:
            metadata: Metadata = json.load(f)
            return metadata


def write_epub(
    path: str,
    title: str,
    author: str,
    timestamp: str,
    chapters: list[Chapter],
    metadata: Metadata,
    images: list[Image],
):
    """EPUB を書き出す

    ダウンロードしていない (fetched でない) エピソードの本文と挿絵は
    path にある既存の EPUB から引き継ぐ。
    """
    episodes = [episode for chapter in chapters for episode in chapter["episodes"]]
    reused_episodes = [episode for episode in episodes if not episode["fetched"]]
    # 同じ挿絵が複数のエピソードで使われることがあるので ID で重複を除く
    manifest_images: list[MetadataImage] = []
    image_ids: set[str] = set()

    with (
        _replace_on_success(path) as tmp_file,
        zipfile.ZipFile(
            tmp_file, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf,
    ):
        zf.writestr(
            "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
        )
        for image in images:
            if image["id"] not in image_ids:
                image_ids.add(image["id"])
                manifest_images.append(image)
                zf.writestr(_image_path(image["name"]), image["data"])
        for episode in episodes:
            if episode["fetched"]:
                zf.writestr(
                    _text_path(episode["id"]),
                    text(episode["title"], episode["paragraphs"]),
                )
        if reused_episodes:
            with zipfile.ZipFile(path, "r") as old_zf:
                for episode in reused_episodes:
                    for old_image in metadata["episodes"][episode["id"]]["images"]:
                        if old_image["id"] not in image_ids:
                            image_ids.add(old_image["id"])
                            manifest_images.append(old_image)
                            name = _image_path(old_image["name"])
                            zf.writestr(name, old_zf.read(name))
                for episode in reused_episodes:
                    name = _text_path(episode["id"])
                    zf.writestr(name, old_zf.read(name))
        zf.writestr("META-INF/container.xml", container())
        zf.writestr("src/style.css", style())
        zf.writestr(
            "src/content.opf",
            content(title, author, timestamp, episodes, manifest_images),
        )
        zf.writestr("src/navigation.xhtml", nav(chapters))
        zf.writestr("src/metadata.json", json.dumps(metadata))


def _text_path(episode_id: str) -> str:
    return f"src/text/{_safe_name(episode_id)}.xhtml"


def _image_path(image_name: str) -> str:
    return f"src/image/{_safe_name(image_name)}"


def _safe_name(name: str) -> str:
    if not SAFE_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"EPUB 内のファイル名に使えない文字列です: {name}")
    return name


@contextmanager
def _replace_on_success(path: str) -> Iterator[IO[bytes]]:
    """一時ファイルに書き込み、正常に終わった場合だけ path を置き換える"""
    tmp_file = tempfile.NamedTemporaryFile(
        dir=os.path.dirname(os.path.abspath(path)),
        prefix=f"{os.path.basename(path)}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        with tmp_file:
            yield tmp_file
        os.replace(tmp_file.name, path)
    except BaseException:
        os.remove(tmp_file.name)
        raise
