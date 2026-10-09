import datetime
import os
from typing import Literal

from nepub.epub import read_metadata, write_epub
from nepub.http import Fetch, get, throttle
from nepub.site import KAKUYOMU, NAROU, Site
from nepub.type import Chapter, Episode, Image, Metadata, MetadataEpisode
from nepub.util import range_to_episode_nums

# 既存の EPUB と一致していないと更新できない設定
METADATA_FLAGS: tuple[Literal["kakuyomu", "illustration", "tcy"], ...] = (
    "kakuyomu",
    "illustration",
    "tcy",
)


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
    print(
        f"novel_id: {novel_id}, illustration: {illustration}, tcy: {tcy}, output: {output}, kakuyomu: {kakuyomu}"
    )
    site = KAKUYOMU if kakuyomu else NAROU

    if illustration and not site.supports_illustration:
        print(
            f"Process stopped as illustration option is not supported for {site.name}."
        )
        return
    if not site.novel_id_pattern.fullmatch(novel_id):
        print(f"Process stopped as the novel_id is invalid: {novel_id}")
        return

    new_metadata: Metadata = {
        "novel_id": novel_id,
        "kakuyomu": kakuyomu,
        "illustration": illustration,
        "tcy": tcy,
        "episodes": {},
    }
    old_episodes: dict[str, MetadataEpisode] = {}
    exists = os.path.exists(output)
    if exists:
        print(f"{output} found. Loading metadata for update.")
        old_metadata = read_metadata(output)
        error = check_metadata(old_metadata, new_metadata)
        if error:
            print(f"Process stopped as {error}")
            return
        old_episodes = old_metadata["episodes"]

    target_episode_nums = range_to_episode_nums(my_range) if my_range else None
    if fetch is None:
        fetch = throttle(get, interval=1)

    title, author, chapters = fetch_index(site, novel_id, fetch)
    timestamp = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    episodes = [episode for chapter in chapters for episode in chapter["episodes"]]

    print(f"title: {title}")
    print(f"author: {author}")
    print(f"{len(episodes)} episodes found.")
    print("Start downloading...")

    downloaded_count = 0
    skipped_count = 0
    images: list[Image] = []
    ignored_episode_ids: set[str] = set()
    for num, episode in enumerate(episodes, start=1):
        old_episode = old_episodes.get(episode["id"])
        in_range = target_episode_nums is None or str(num) in target_episode_nums
        url = site.episode_url(novel_id, episode["id"])
        progress = f"({num}/{len(episodes)}): {url}"

        if old_episode and (not in_range or not is_updated(episode, old_episode)):
            # 既存の EPUB にあり、取得対象外か更新されていないエピソードはそのまま使う
            episode["title"] = old_episode["title"]
            new_metadata["episodes"][episode["id"]] = old_episode
            if in_range:
                skipped_count += 1
                print(f"Download skipped (already up to date) {progress}")
        elif not in_range:
            # 取得対象外で既存の EPUB にもないエピソードは含めない
            ignored_episode_ids.add(episode["id"])
        else:
            print(f"Downloading {progress}")
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

    print(f"Download is complete! (new: {downloaded_count}, skipped: {skipped_count})")

    write_epub(output, title, author, timestamp, chapters, new_metadata, images)
    print(f"{'Updated' if exists else 'Created'} {output}.")


def check_metadata(old: Metadata, new: Metadata) -> str | None:
    """既存の EPUB と異なる設定で更新しようとしている場合はその内容を返す"""
    if old["novel_id"] != new["novel_id"]:
        return f"the novel_id differs from metadata: {old['novel_id']}"
    for key in METADATA_FLAGS:
        if old.get(key, False) != new[key]:
            return f"the {key} value differs from metadata: {old.get(key, False)}"
    return None


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
