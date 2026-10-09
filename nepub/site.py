import re
from collections.abc import Callable
from dataclasses import dataclass

from nepub.parser.kakuyomu import KakuyomuEpisodeParser, KakuyomuIndexParser
from nepub.parser.narou import NarouEpisodeParser, NarouIndexParser

IndexParser = NarouIndexParser | KakuyomuIndexParser


@dataclass(frozen=True)
class Site:
    """小説投稿サイトごとに異なる部分 (URL, パーサー) の定義"""

    name: str
    novel_id_pattern: re.Pattern[str]
    index_url_template: str
    episode_url_template: str
    supports_illustration: bool
    new_index_parser: Callable[[], IndexParser]
    # (illustration, tcy) を受け取ってパーサーを作る
    new_episode_parser: Callable[[bool, bool], NarouEpisodeParser]

    def index_url(self, novel_id: str, page: str) -> str:
        return self.index_url_template.format(novel_id=novel_id, page=page)

    def episode_url(self, novel_id: str, episode_id: str) -> str:
        return self.episode_url_template.format(
            novel_id=novel_id, episode_id=episode_id
        )


NAROU = Site(
    name="Narou",
    novel_id_pattern=re.compile(r"[0-9a-zA-Z]+"),
    index_url_template="https://ncode.syosetu.com/{novel_id}/?p={page}",
    episode_url_template="https://ncode.syosetu.com/{novel_id}/{episode_id}/",
    supports_illustration=True,
    new_index_parser=NarouIndexParser,
    new_episode_parser=lambda illustration, tcy: NarouEpisodeParser(illustration, tcy),
)

KAKUYOMU = Site(
    name="Kakuyomu",
    novel_id_pattern=re.compile(r"[0-9]+"),
    # 目次は 1 ページにまとまっているので page は使わない
    index_url_template="https://kakuyomu.jp/works/{novel_id}",
    episode_url_template="https://kakuyomu.jp/works/{novel_id}/episodes/{episode_id}",
    supports_illustration=False,
    new_index_parser=KakuyomuIndexParser,
    new_episode_parser=lambda illustration, tcy: KakuyomuEpisodeParser(tcy),
)
