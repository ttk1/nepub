import argparse
import datetime
import json
import os
import tempfile
import time
import zipfile
from typing import List

from nepub.epub import container, content, nav, style, text
from nepub.http import get
from nepub.parser.kakuyomu import KakuyomuEpisodeParser, KakuyomuIndexParser
from nepub.parser.narou import NarouEpisodeParser, NarouIndexParser
from nepub.type import Episode, Image, Metadata, MetadataImage
from nepub.util import range_to_episode_nums


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("novel_id", help="novel id", type=str)
    parser.add_argument(
        "-i",
        "--illustration",
        help="Include illustrations (Narou only)",
        action="store_true",
    )
    parser.add_argument(
        "-t", "--tcy", help="Enable Tate-Chu-Yoko conversion", action="store_true"
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
    if args.output:
        output = args.output
    else:
        output = f"{args.novel_id}.epub"
    convert_narou_to_epub(
        args.novel_id, args.illustration, args.tcy, args.range, output, args.kakuyomu
    )


def get_index_parser(kakuyomu: bool):
    if kakuyomu:
        return KakuyomuIndexParser()
    else:
        return NarouIndexParser()


def get_episode_parser(illustration: bool, tcy: bool, kakuyomu: bool):
    if kakuyomu:
        return KakuyomuEpisodeParser(tcy)
    else:
        return NarouEpisodeParser(illustration, tcy)


def get_index_page_url(novel_id: str, page: int, kakuyomu: bool):
    if kakuyomu:
        return f"https://kakuyomu.jp/works/{novel_id}"
    else:
        return f"https://ncode.syosetu.com/{novel_id}/?p={page}"


def get_episode_page_url(novel_id: str, episode_id: str, kakuyomu: bool):
    if kakuyomu:
        return f"https://kakuyomu.jp/works/{novel_id}/episodes/{episode_id}"
    else:
        return f"https://ncode.syosetu.com/{novel_id}/{episode_id}/"


def convert_narou_to_epub(
    novel_id: str,
    illustration: bool,
    tcy: bool,
    my_range: str,
    output: str,
    kakuyomu: bool,
):
    print(
        f"novel_id: {novel_id}, illustration: {illustration}, tcy: {tcy}, output: {output}, kakuyomu: {kakuyomu}"
    )

    # kakuyomu で illustration が指定されていたら処理を中止する
    if kakuyomu and illustration:
        print("Process stopped as illustration option is not supported for Kakuyomu.")
        return

    # metadata
    metadata: Metadata | None = None
    new_metadata: Metadata = {
        "novel_id": novel_id,
        "kakuyomu": kakuyomu,
        "illustration": illustration,
        "tcy": tcy,
        "episodes": {},
    }
    if os.path.exists(output):
        print(f"{output} found. Loading metadata for update.")
        with zipfile.ZipFile(output, "r") as zf_old:
            with zf_old.open("src/metadata.json") as f:
                metadata = json.load(f)

    # check novel_id
    if metadata and metadata["novel_id"] != novel_id:
        # metadata の novel_id と値が異なる場合処理を中止する
        print(
            f"Process stopped as the novel_id differs from metadata: {metadata['novel_id']}"
        )
        return

    # check kakuyomu flag
    if metadata and metadata.get("kakuyomu", False) != kakuyomu:
        # metadata の kakuyomu フラグと値が異なる場合処理を中止する
        print(
            f"Process stopped as the kakuyomu value differs from metadata: {metadata.get('kakuyomu', False)}"
        )
        return

    # check illustration flag
    if metadata and metadata.get("illustration", False) != illustration:
        # metadata の illustration フラグと値が異なる場合処理を中止する
        print(
            f"Process stopped as the illustration value differs from metadata: {metadata.get('illustration', False)}"
        )
        return

    # check tcy flag
    if metadata and metadata.get("tcy", False) != tcy:
        # metadata の tcy フラグと値が異なる場合処理を中止する
        print(
            f"Process stopped as the tcy value differs from metadata: {metadata.get('tcy', False)}"
        )
        return

    target_episode_nums: set[str] | None = None
    if my_range:
        target_episode_nums = range_to_episode_nums(my_range)

    # index
    index_parser = get_index_parser(kakuyomu)
    index_parser.feed(get(get_index_page_url(novel_id, 1, kakuyomu)))
    title = index_parser.title
    author = index_parser.author
    next_page = index_parser.next_page
    timestamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    chapters = index_parser.chapters
    while next_page is not None:
        index_parser.reset()
        index_parser.chapters = chapters
        index_parser.feed(get(get_index_page_url(novel_id, next_page, kakuyomu)))
        chapters = index_parser.chapters
        next_page = index_parser.next_page
        # 負荷かけないようにちょっと待つ
        time.sleep(1)

    # episode
    downloaded_count = 0
    skipped_count = 0
    episodes: List[Episode] = []
    images: List[Image] = []
    metadata_images: List[MetadataImage] = []
    episode_parser = get_episode_parser(illustration, tcy, kakuyomu)
    for chapter in chapters:
        for episode in chapter["episodes"]:
            episodes.append(episode)

    print(f"title: {title}")
    print(f"author: {author}")

    print(f"{len(episodes)} episodes found.")
    print("Start downloading...")

    ignored_episode_ids: list[str] = []
    for num, episode in enumerate(episodes):
        if metadata:
            if episode["id"] in metadata["episodes"]:
                metadata_episode = metadata["episodes"][episode["id"]]
                if metadata_episode["id"] == episode["id"]:
                    if (
                        target_episode_nums is not None
                        and str(num + 1) not in target_episode_nums
                    ):
                        # 取得対象外で既存のファイルに存在しているエピソードはそのまま取り出す
                        episode["title"] = metadata_episode["title"]
                        new_metadata["episodes"][episode["id"]] = metadata_episode
                        metadata_images += metadata_episode["images"]
                        continue
                    if not max(episode["created_at"], episode["updated_at"]) > max(
                        metadata_episode["created_at"], metadata_episode["updated_at"]
                    ):
                        # 更新がないエピソードはダウンロードをスキップ
                        episode["title"] = metadata_episode["title"]
                        new_metadata["episodes"][episode["id"]] = metadata_episode
                        metadata_images += metadata_episode["images"]
                        skipped_count += 1
                        print(
                            f"Download skipped (already up to date) ({num + 1}/{len(episodes)}): {get_episode_page_url(novel_id, episode['id'], kakuyomu)}"
                        )
                        continue
        if target_episode_nums is not None and str(num + 1) not in target_episode_nums:
            ignored_episode_ids.append(episode["id"])
            continue
        print(
            f"Downloading ({num + 1}/{len(episodes)}): {get_episode_page_url(novel_id, episode['id'], kakuyomu)}"
        )
        episode_parser.feed(
            get(get_episode_page_url(novel_id, episode["id"], kakuyomu))
        )
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
                {
                    "id": image["id"],
                    "name": image["name"],
                    "type": image["type"],
                }
                for image in episode_parser.images
            ],
        }
        episode_parser.reset()
        # 負荷かけないようにちょっと待つ
        time.sleep(1)
    # 処理対象外かつ既存のファイルに存在しないエピソードを削除
    episodes = [
        episode for episode in episodes if episode["id"] not in ignored_episode_ids
    ]
    for chapter in chapters:
        chapter["episodes"] = [
            episode
            for episode in chapter["episodes"]
            if episode["id"] not in ignored_episode_ids
        ]

    print(f"Download is complete! (new: {downloaded_count}, skipped: {skipped_count})")

    with tempfile.NamedTemporaryFile(
        prefix=output, dir=os.getcwd(), delete=False
    ) as tmp_file:
        tmp_file_name = tmp_file.name
        with zipfile.ZipFile(
            tmp_file, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
        ) as zf_new:
            unique_images: List[MetadataImage] = []
            image_md5s = set()
            for image in images:
                if image["id"] not in image_md5s:
                    image_md5s.add(image["id"])
                    unique_images.append(image)
                    zf_new.writestr(f"src/image/{image['name']}", image["data"])
            for episode in episodes:
                if episode["fetched"]:
                    zf_new.writestr(
                        f"src/text/{episode['id']}.xhtml",
                        text(episode["title"], episode["paragraphs"]),
                    )
            if metadata:
                with zipfile.ZipFile(output, "r") as zf_old:
                    for metadata_image in metadata_images:
                        if metadata_image["id"] not in image_md5s:
                            image_md5s.add(metadata_image["id"])
                            unique_images.append(metadata_image)
                            with zf_old.open(
                                f"src/image/{metadata_image['name']}"
                            ) as f:
                                zf_new.writestr(
                                    f"src/image/{metadata_image['name']}", f.read()
                                )
                    for episode in episodes:
                        if not episode["fetched"]:
                            with zf_old.open(f"src/text/{episode['id']}.xhtml") as f:
                                zf_new.writestr(
                                    f"src/text/{episode['id']}.xhtml", f.read()
                                )
            zf_new.writestr("mimetype", "application/epub+zip")
            zf_new.writestr("META-INF/container.xml", container())
            zf_new.writestr("src/style.css", style())
            zf_new.writestr(
                "src/content.opf",
                content(title, author, timestamp, episodes, unique_images),
            )
            zf_new.writestr("src/navigation.xhtml", nav(chapters))
            zf_new.writestr("src/metadata.json", json.dumps(new_metadata))

    if os.path.exists(output):
        os.remove(output)
        os.rename(tmp_file_name, output)
        print(f"Updated {output}.")
    else:
        os.rename(tmp_file_name, output)
        print(f"Created {output}.")


if __name__ == "__main__":
    main()
