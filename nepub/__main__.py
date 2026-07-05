import argparse
import datetime
import json
import os
import re
import tempfile
import time
import zipfile
from typing import Mapping, cast

from nepub.epub import container, content, nav, style, text
from nepub.http import get
from nepub.parser.kakuyomu import KakuyomuEpisodeParser, KakuyomuIndexParser
from nepub.parser.narou import NarouEpisodeParser, NarouIndexParser
from nepub.type import Chapter, Episode, Image, Metadata, MetadataEpisode, MetadataImage
from nepub.util import range_to_episode_nums

# サーバーに負荷をかけないようリクエストの間に入れる待ち時間 (秒)
REQUEST_INTERVAL = 1
NOVEL_ID_PATTERN = re.compile(r"[a-zA-Z0-9]+")
# 画像のファイル名は MD5 ハッシュ値 + 拡張子で生成している (nepub.http.get_image 参照)
IMAGE_NAME_PATTERN = re.compile(r"[0-9a-f]{32}\.(jpg|png|gif)")


def main():
    parser = argparse.ArgumentParser(
        description="Convert Narou and Kakuyomu novels to vertically written EPUBs."
    )
    parser.add_argument("novel_id", help="novel id", type=str)
    parser.add_argument(
        "-i",
        "--illustration",
        help="Include illustrations (Narou only)",
        action="store_true",
    )
    parser.add_argument(
        "--no-tcy", help="Disable Tate-Chu-Yoko conversion", action="store_true"
    )
    parser.add_argument(
        "-r",
        "--range",
        metavar="<range>",
        help='Specify the target episode number range using comma-separated values (e.g., "1,2,3") or a range notation (e.g., "10-20").',
        type=str,
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="<file>",
        help="Output file name. If not specified, ${novel_id}.epub is used. Update the file if it exists.",
        type=str,
    )
    parser.add_argument(
        "-k", "--kakuyomu", help="Use Kakuyomu as the source", action="store_true"
    )
    args = parser.parse_args()
    if not NOVEL_ID_PATTERN.fullmatch(args.novel_id):
        parser.error(f"invalid novel_id: {args.novel_id}")
    convert_to_epub(
        novel_id=args.novel_id,
        illustration=args.illustration,
        tcy=not args.no_tcy,
        episode_range=args.range,
        output=args.output or f"{args.novel_id}.epub",
        kakuyomu=args.kakuyomu,
    )


def index_page_url(novel_id: str, page: str, kakuyomu: bool) -> str:
    if kakuyomu:
        # カクヨムの目次はページ分割されていない
        return f"https://kakuyomu.jp/works/{novel_id}"
    return f"https://ncode.syosetu.com/{novel_id}/?p={page}"


def episode_page_url(novel_id: str, episode_id: str, kakuyomu: bool) -> str:
    if kakuyomu:
        return f"https://kakuyomu.jp/works/{novel_id}/episodes/{episode_id}"
    return f"https://ncode.syosetu.com/{novel_id}/{episode_id}/"


def load_metadata(output: str) -> Metadata | None:
    """既存の出力ファイルからメタデータを読み込む。ファイルがなければ None を返す。"""
    if not os.path.exists(output):
        return None
    print(f"{output} found. Loading metadata for update.")
    with zipfile.ZipFile(output) as zf, zf.open("src/metadata.json") as f:
        return cast(Metadata, json.load(f))


def check_options_match(metadata: Mapping[str, object], **options: object) -> bool:
    """既存ファイルのメタデータと今回のオプションが一致するか確認する。"""
    for key, value in options.items():
        actual = metadata.get(key, False)
        if actual != value:
            print(f"Process stopped as the {key} differs from metadata: {actual}")
            return False
    return True


def fetch_index(novel_id: str, kakuyomu: bool) -> tuple[str, str, list[Chapter]]:
    """目次ページを (複数ページある場合は全ページ) 取得する。"""
    parser: NarouIndexParser | KakuyomuIndexParser = (
        KakuyomuIndexParser() if kakuyomu else NarouIndexParser()
    )
    parser.feed(get(index_page_url(novel_id, "1", kakuyomu)))
    title = parser.title
    author = parser.author
    while parser.next_page is not None:
        next_page = parser.next_page
        chapters = parser.chapters
        # サーバーに負荷をかけないようちょっと待つ
        time.sleep(REQUEST_INTERVAL)
        parser.reset()
        # chapters はページをまたいで積み上げる
        parser.chapters = chapters
        parser.feed(get(index_page_url(novel_id, next_page, kakuyomu)))
    return title, author, parser.chapters


def create_episode_parser(
    illustration: bool, tcy: bool, kakuyomu: bool
) -> NarouEpisodeParser:
    if kakuyomu:
        return KakuyomuEpisodeParser(convert_tcy=tcy)
    return NarouEpisodeParser(include_images=illustration, convert_tcy=tcy)


def is_updated(episode: Episode, cached: MetadataEpisode) -> bool:
    """目次上の日時が既存ファイル取得時より新しければ True。"""
    return max(episode["created_at"], episode["updated_at"]) > max(
        cached["created_at"], cached["updated_at"]
    )


def convert_to_epub(
    novel_id: str,
    illustration: bool,
    tcy: bool,
    episode_range: str | None,
    output: str,
    kakuyomu: bool,
) -> None:
    print(
        f"novel_id: {novel_id}, illustration: {illustration}, tcy: {tcy}, output: {output}, kakuyomu: {kakuyomu}"
    )

    if kakuyomu and illustration:
        print("Process stopped as illustration option is not supported for Kakuyomu.")
        return

    metadata = load_metadata(output)
    if metadata is not None and not check_options_match(
        metadata,
        novel_id=novel_id,
        kakuyomu=kakuyomu,
        illustration=illustration,
        tcy=tcy,
    ):
        return

    target_episode_nums = (
        range_to_episode_nums(episode_range) if episode_range else None
    )

    title, author, chapters = fetch_index(novel_id, kakuyomu)
    episodes = [episode for chapter in chapters for episode in chapter["episodes"]]

    print(f"title: {title}")
    print(f"author: {author}")
    print(f"{len(episodes)} episodes found.")
    print("Start downloading...")

    new_metadata: Metadata = {
        "novel_id": novel_id,
        "kakuyomu": kakuyomu,
        "illustration": illustration,
        "tcy": tcy,
        "episodes": {},
    }
    images: list[Image] = []
    old_images: list[MetadataImage] = []
    ignored_episode_ids: set[str] = set()
    downloaded_count = 0
    skipped_count = 0
    episode_parser = create_episode_parser(illustration, tcy, kakuyomu)

    for num, episode in enumerate(episodes, start=1):
        url = episode_page_url(novel_id, episode["id"], kakuyomu)
        in_range = target_episode_nums is None or num in target_episode_nums
        cached = metadata["episodes"].get(episode["id"]) if metadata else None
        if cached and (not in_range or not is_updated(episode, cached)):
            # 既存ファイルにあり更新もない (または取得対象外の) エピソードはそのまま使う
            episode["title"] = cached["title"]
            new_metadata["episodes"][episode["id"]] = cached
            old_images += cached["images"]
            if in_range:
                skipped_count += 1
                print(
                    f"Download skipped (already up to date) ({num}/{len(episodes)}): {url}"
                )
            continue
        if not in_range:
            # 取得対象外かつ既存ファイルにも存在しないエピソードは出力から除外する
            ignored_episode_ids.add(episode["id"])
            continue
        # サーバーに負荷をかけないようちょっと待つ
        time.sleep(REQUEST_INTERVAL)
        print(f"Downloading ({num}/{len(episodes)}): {url}")
        episode_parser.feed(get(url))
        downloaded_count += 1
        episode["title"] = episode_parser.title
        episode["paragraphs"] = episode_parser.paragraphs
        episode["fetched"] = True
        images += episode_parser.images
        new_metadata["episodes"][episode["id"]] = {
            "id": episode["id"],
            "title": episode["title"],
            "created_at": episode["created_at"],
            "updated_at": episode["updated_at"],
            "images": [
                {"id": image["id"], "name": image["name"], "type": image["type"]}
                for image in episode_parser.images
            ],
        }
        episode_parser.reset()

    if ignored_episode_ids:
        episodes = [e for e in episodes if e["id"] not in ignored_episode_ids]
        for chapter in chapters:
            chapter["episodes"] = [
                e for e in chapter["episodes"] if e["id"] not in ignored_episode_ids
            ]

    print(f"Download is complete! (new: {downloaded_count}, skipped: {skipped_count})")

    is_update = metadata is not None
    write_epub(
        output=output,
        title=title,
        author=author,
        chapters=chapters,
        episodes=episodes,
        images=images,
        old_images=old_images,
        new_metadata=new_metadata,
        old_file=output if is_update else None,
    )
    print(f"{'Updated' if is_update else 'Created'} {output}.")


def write_epub(
    output: str,
    title: str,
    author: str,
    chapters: list[Chapter],
    episodes: list[Episode],
    images: list[Image],
    old_images: list[MetadataImage],
    new_metadata: Metadata,
    old_file: str | None,
) -> None:
    """EPUB を一時ファイルに書き出し、成功したら output に置き換える。"""
    timestamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    out_dir = os.path.dirname(os.path.abspath(output))
    fd, tmp_path = tempfile.mkstemp(prefix=os.path.basename(output) + ".", dir=out_dir)
    try:
        with (
            os.fdopen(fd, "wb") as tmp_file,
            zipfile.ZipFile(
                tmp_file, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as zf,
        ):
            # mimetype は無圧縮で先頭に配置する必要がある
            zf.writestr(
                "mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED
            )
            written_image_ids: set[str] = set()
            unique_images: list[MetadataImage] = []
            for image in images:
                if image["id"] in written_image_ids:
                    continue
                written_image_ids.add(image["id"])
                unique_images.append(image)
                zf.writestr(f"src/image/{image['name']}", image["data"])
            for episode in episodes:
                if episode["fetched"]:
                    zf.writestr(
                        f"src/text/{episode['id']}.xhtml",
                        text(episode["title"], episode["paragraphs"]),
                    )
            if old_file:
                _copy_from_old_file(
                    zf, old_file, episodes, old_images, written_image_ids, unique_images
                )
            zf.writestr("META-INF/container.xml", container())
            zf.writestr("src/style.css", style())
            zf.writestr(
                "src/content.opf",
                content(title, author, timestamp, episodes, unique_images),
            )
            zf.writestr("src/navigation.xhtml", nav(chapters))
            zf.writestr("src/metadata.json", json.dumps(new_metadata))
    except BaseException:
        os.remove(tmp_path)
        raise
    os.replace(tmp_path, output)


def _copy_from_old_file(
    zf_new: zipfile.ZipFile,
    old_file: str,
    episodes: list[Episode],
    old_images: list[MetadataImage],
    written_image_ids: set[str],
    unique_images: list[MetadataImage],
) -> None:
    """更新のなかった画像とテキストを既存の EPUB からコピーする。"""
    with zipfile.ZipFile(old_file) as zf_old:
        for image in old_images:
            if image["id"] in written_image_ids:
                continue
            if not IMAGE_NAME_PATTERN.fullmatch(image["name"]):
                raise ValueError(
                    f"画像のファイル名が想定しない形式です: {image['name']}"
                )
            written_image_ids.add(image["id"])
            unique_images.append(image)
            zf_new.writestr(
                f"src/image/{image['name']}", zf_old.read(f"src/image/{image['name']}")
            )
        for episode in episodes:
            if not episode["fetched"]:
                zf_new.writestr(
                    f"src/text/{episode['id']}.xhtml",
                    zf_old.read(f"src/text/{episode['id']}.xhtml"),
                )


if __name__ == "__main__":
    main()
