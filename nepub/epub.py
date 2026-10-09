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
# EPUB に含めてよい挿絵の形式
IMAGE_TYPES = ("image/jpeg", "image/png", "image/gif")


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

    # 書き込む本文 (エピソード ID -> XHTML) と挿絵 (画像 ID -> (情報, データ)) を集める
    # 同じ挿絵が複数のエピソードで使われることがあるので画像 ID で重複を除く
    texts: dict[str, str | bytes] = {}
    image_files: dict[str, tuple[MetadataImage, bytes]] = {}
    for episode in episodes:
        if episode["fetched"]:
            texts[episode["id"]] = text(episode["title"], episode["paragraphs"])
    for image in images:
        image_files.setdefault(image["id"], (image, image["data"]))
    # 今回ダウンロードしていないエピソード (更新がない / 取得範囲外) は、
    # 更新前の EPUB (path) に入っている本文と挿絵をそのまま使う
    if reused_episodes:
        with zipfile.ZipFile(path, "r") as old_zf:
            for episode in reused_episodes:
                # 本文は変換済みの XHTML をそのままコピーする
                texts[episode["id"]] = old_zf.read(_text_path(episode["id"]))
                # そのエピソードが使っている挿絵は metadata に記録されている
                # ダウンロードした挿絵や、他のエピソードで集めた挿絵と同じものは読み込まない
                for old_image in metadata["episodes"][episode["id"]]["images"]:
                    if old_image["id"] not in image_files:
                        data = old_zf.read(_image_path(old_image["name"]))
                        image_files[old_image["id"]] = (old_image, data)
    manifest_images = [_check_image(image) for image, _ in image_files.values()]

    # 一時ファイルに zip を書き、全部書き終わったら path と差し替える
    # (途中で失敗しても path の既存ファイルは壊れない)
    with (
        _replace_on_success(path) as tmp_file,
        zipfile.ZipFile(
            tmp_file, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf,
    ):
        zf.writestr(
            "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
        )
        for image_info, data in image_files.values():
            zf.writestr(_image_path(image_info["name"]), data)
        for episode in episodes:
            zf.writestr(_text_path(episode["id"]), texts[episode["id"]])
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


def _check_image(image: MetadataImage) -> MetadataImage:
    """content.opf にそのまま埋め込まれる挿絵の情報を検証する"""
    _safe_name(image["id"])
    _safe_name(image["name"])
    if image["type"] not in IMAGE_TYPES:
        raise ValueError(f"EPUB に含められない画像の形式です: {image['type']}")
    return image


def _safe_name(name: str) -> str:
    if not SAFE_NAME_PATTERN.fullmatch(name):
        raise ValueError(f"EPUB 内のファイル名に使えない文字列です: {name}")
    return name


@contextmanager
def _replace_on_success(path: str) -> Iterator[IO[bytes]]:
    """一時ファイルに書き込み、正常に終わった場合だけ path を置き換える

    with ブロックには一時ファイルが渡される。
    ブロックが正常に終われば一時ファイルで path を置き換え、
    例外が起きた場合は一時ファイルを削除して例外をそのまま投げ直す。
    """
    # os.replace は別のドライブには移動できないので path と同じフォルダに作る
    # 閉じたあとに os.replace したいので自動削除はしない (delete=False)
    tmp_file = tempfile.NamedTemporaryFile(
        dir=os.path.dirname(os.path.abspath(path)),
        prefix=f"{os.path.basename(path)}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        # with を抜けると一時ファイルが閉じられる
        # (Windows では開いたままだと os.replace / os.remove できない)
        with tmp_file:
            # ここで呼び出し側の with ブロックが実行される
            yield tmp_file
        # 正常終了: 既存ファイルがあっても 1 回の操作で上書きする
        os.replace(tmp_file.name, path)
    except BaseException:
        # 失敗 (Ctrl+C による中断も含む): 一時ファイルだけ消して path には触らない
        os.remove(tmp_file.name)
        raise
