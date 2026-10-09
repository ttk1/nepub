import datetime
import os
import zipfile
from typing import Literal

from nepub.epub import read_metadata, write_epub
from nepub.http import Fetch, get, throttle
from nepub.site import KAKUYOMU, NAROU, Site
from nepub.type import Chapter, Episode, Image, Metadata, MetadataEpisode
from nepub.util import range_to_episode_nums

# 既存の EPUB と一致していないと更新できない設定
# metadata のキー -> (対応する CLI オプション, そのオプションを指定したときの値)
METADATA_OPTIONS: dict[Literal["kakuyomu", "illustration", "tcy"], tuple[str, bool]] = {
    "kakuyomu": ("--kakuyomu", True),
    "illustration": ("--illustration", True),
    "tcy": ("--no-tcy", False),
}


class ConvertError(Exception):
    """利用者に表示して処理を中止するエラー (入力の誤り等)"""


def convert_to_epub(
    novel_id: str,
    *,
    illustration: bool,
    tcy: bool,
    my_range: str | None,
    output: str,
    kakuyomu: bool,
    fetch: Fetch | None = None,
):
    """小説をダウンロードして EPUB を作成する

    output が既に存在する場合は、更新されたエピソードだけをダウンロードして更新する。
    fetch はテスト用。省略すると 1 秒間隔で HTTP リクエストを送る。
    """
    site = KAKUYOMU if kakuyomu else NAROU
    if illustration and not site.supports_illustration:
        raise ConvertError(
            f"the --illustration option is not supported for {site.name}"
        )
    if not site.novel_id_pattern.fullmatch(novel_id):
        raise ConvertError(f"invalid novel ID for {site.name}: {novel_id}")
    try:
        target_episode_nums = range_to_episode_nums(my_range) if my_range else None
    except ValueError as e:
        raise ConvertError(str(e)) from e

    exists = os.path.exists(output)
    print(f"Novel: {novel_id} ({site.name})")
    print(
        f"Output: {output} ({'updating the existing file' if exists else 'new file'})"
    )
    print(
        f"Options: illustrations: {'on' if illustration else 'off'}, tcy: {'on' if tcy else 'off'}"
    )

    new_metadata: Metadata = {
        "novel_id": novel_id,
        "kakuyomu": kakuyomu,
        "illustration": illustration,
        "tcy": tcy,
        "episodes": {},
    }
    old_episodes: dict[str, MetadataEpisode] = {}
    if exists:
        try:
            old_metadata = read_metadata(output)
        except (zipfile.BadZipFile, KeyError) as e:
            raise ConvertError(
                f"cannot update {output}: it is not an EPUB created by nepub"
            ) from e
        check_metadata(old_metadata, new_metadata, output)
        old_episodes = old_metadata["episodes"]

    if fetch is None:
        fetch = throttle(get, interval=1)

    title, author, chapters = fetch_index(site, novel_id, fetch)
    timestamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    episodes = [episode for chapter in chapters for episode in chapter["episodes"]]

    print(f"Title: {title}")
    print(f"Author: {author}")
    print(f"Found {len(episodes)} episode{'' if len(episodes) == 1 else 's'}.")
    # 進捗表示の番号の桁をそろえる ([ 1/12] のように)
    num_width = len(str(len(episodes)))

    downloaded_count = 0
    skipped_count = 0
    images: list[Image] = []
    ignored_episode_ids: set[str] = set()
    for num, episode in enumerate(episodes, start=1):
        old_episode = old_episodes.get(episode["id"])
        in_range = target_episode_nums is None or str(num) in target_episode_nums
        url = site.episode_url(novel_id, episode["id"])
        progress = f"[{num:>{num_width}}/{len(episodes)}]"

        if old_episode and (not in_range or not is_updated(episode, old_episode)):
            # 既存の EPUB にあり、取得対象外か更新されていないエピソードはそのまま使う
            episode["title"] = old_episode["title"]
            new_metadata["episodes"][episode["id"]] = old_episode
            if in_range:
                skipped_count += 1
                print(f"{progress} Skipped (up to date): {url}")
        elif not in_range:
            # 取得対象外で既存の EPUB にもないエピソードは含めない
            ignored_episode_ids.add(episode["id"])
        else:
            print(f"{progress} Downloading: {url}")
            parser = site.new_episode_parser(illustration=illustration, tcy=tcy)
            parser.feed(fetch(url))
            episode["title"] = parser.title
            episode["paragraphs"] = parser.paragraphs
            episode["fetched"] = True
            images += parser.images
            new_metadata["episodes"][episode["id"]] = to_metadata_episode(
                episode, parser.images
            )
            downloaded_count += 1

    for chapter in chapters:
        chapter["episodes"] = [
            episode
            for episode in chapter["episodes"]
            if episode["id"] not in ignored_episode_ids
        ]

    print(f"Done: {downloaded_count} downloaded, {skipped_count} skipped (up to date).")

    write_epub(output, title, author, timestamp, chapters, new_metadata, images)
    print(f"{'Updated' if exists else 'Created'} {output}.")


def check_metadata(old: Metadata, new: Metadata, output: str):
    """既存の EPUB と異なる設定で更新しようとしている場合は ConvertError を送出する"""
    if old["novel_id"] != new["novel_id"]:
        raise ConvertError(
            f"cannot update {output}: it contains a different novel ({old['novel_id']}); "
            "specify another output file with -o"
        )
    for key, (option, value_with_option) in METADATA_OPTIONS.items():
        old_value = old.get(key, False)
        if old_value != new[key]:
            created = "with" if old_value == value_with_option else "without"
            raise ConvertError(
                f"cannot update {output}: it was created {created} {option}; "
                "use the same options or specify another output file with -o"
            )


def fetch_index(
    site: Site, novel_id: str, fetch: Fetch
) -> tuple[str, str, list[Chapter]]:
    """目次を取得し (タイトル, 作者, 章のリスト) を返す"""
    parser = site.new_index_parser()
    parser.feed(fetch(site.index_url(novel_id, "1")))
    title = parser.title
    author = parser.author
    chapters: list[Chapter] = parser.chapters
    while parser.next_page is not None:
        next_page = parser.next_page
        parser = site.new_index_parser()
        parser.feed(fetch(site.index_url(novel_id, next_page)))
        # ページ先頭の章見出しのないエピソードは前のページの最後の章の続き
        chapters[-1]["episodes"] += parser.chapters[0]["episodes"]
        chapters += parser.chapters[1:]
    return title, author, chapters


def is_updated(episode: Episode, old_episode: MetadataEpisode) -> bool:
    return max(episode["created_at"], episode["updated_at"]) > max(
        old_episode["created_at"], old_episode["updated_at"]
    )


def to_metadata_episode(episode: Episode, images: list[Image]) -> MetadataEpisode:
    return {
        "id": episode["id"],
        "title": episode["title"],
        "created_at": episode["created_at"],
        "updated_at": episode["updated_at"],
        "images": [
            {"id": image["id"], "name": image["name"], "type": image["type"]}
            for image in images
        ],
    }
