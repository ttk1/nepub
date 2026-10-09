import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from nepub.parser.kakuyomu import KakuyomuEpisodeParser, KakuyomuIndexParser
from nepub.parser.narou import NarouEpisodeParser, NarouIndexParser

IndexParser = NarouIndexParser | KakuyomuIndexParser


class EpisodeParserFactory(Protocol):
    def __call__(self, *, illustration: bool, tcy: bool) -> NarouEpisodeParser: ...


@dataclass(frozen=True)
class Site:
    """小説投稿サイトごとに異なる部分 (URL, パーサー) の定義"""

    name: str
    novel_id_pattern: re.Pattern[str]
    index_url_template: str
    episode_url_template: str
    supports_illustration: bool
    new_index_parser: Callable[[], IndexParser]
    new_episode_parser: EpisodeParserFactory

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
    new_episode_parser=lambda *, illustration, tcy: NarouEpisodeParser(
        include_images=illustration, convert_tcy=tcy
    ),
)

KAKUYOMU = Site(
    name="Kakuyomu",
    novel_id_pattern=re.compile(r"[0-9]+"),
    # 目次は 1 ページにまとまっているので page は使わない
    index_url_template="https://kakuyomu.jp/works/{novel_id}",
    episode_url_template="https://kakuyomu.jp/works/{novel_id}/episodes/{episode_id}",
    supports_illustration=False,
    new_index_parser=KakuyomuIndexParser,
    new_episode_parser=lambda *, illustration, tcy: KakuyomuEpisodeParser(
        convert_tcy=tcy
    ),
)
