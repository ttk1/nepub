import html
import json
import re
from html.parser import HTMLParser

from nepub.parser.narou import NarouEpisodeParser
from nepub.type import Chapter


class KakuyomuEpisodeParser(NarouEpisodeParser):
    PARAGRAPH_ID_PATTERN = re.compile(r"p[1-9][0-9]*")
    EPISODE_TITLE_CLASS = "widget-episodeTitle"

    def __init__(self, convert_tcy: bool = False):
        super().__init__(include_images=False, convert_tcy=convert_tcy)


class KakuyomuIndexParser(HTMLParser):
    def reset(self):
        super().reset()
        self.title = ""
        self.author = ""
        # カクヨムの目次はページ分割されていないので常に None
        self.next_page: str | None = None
        self.chapters: list[Chapter] = [{"name": "default", "episodes": []}]
        self._in_next_data = False
        self._buff = ""

    def handle_starttag(self, tag, attrs):
        if tag == "script" and ("id", "__NEXT_DATA__") in attrs:
            self._in_next_data = True

    def handle_endtag(self, tag):
        if tag == "script" and self._in_next_data:
            self._parse_next_data(self._buff)
            self._in_next_data = False
            self._buff = ""

    def handle_data(self, data):
        if self._in_next_data:
            self._buff += data

    def _parse_next_data(self, raw: str):
        data = json.loads(raw)
        state = data["props"]["pageProps"]["__APOLLO_STATE__"]
        work = state[f"Work:{data['query']['workId']}"]
        self.title = html.escape(work["title"]).strip()
        self.author = html.escape(
            state[work["author"]["__ref"]]["activityName"]
        ).strip()
        for toc_ref in work["tableOfContents"]:
            toc_chapter = state[toc_ref["__ref"]]
            chapter_ref = toc_chapter["chapter"]
            if chapter_ref is not None:
                chapter = state[chapter_ref["__ref"]]
                self.chapters.append(
                    {"name": html.escape(chapter["title"]).strip(), "episodes": []}
                )
            for episode_ref in toc_chapter["episodeUnions"]:
                episode = state[episode_ref["__ref"]]
                published_at = html.escape(episode["publishedAt"]).strip()
                self.chapters[-1]["episodes"].append(
                    {
                        "id": html.escape(episode["id"]).strip(),
                        "title": "",
                        "created_at": published_at,
                        # 更新日が分からないので作成日と同じ値を入れておく
                        "updated_at": published_at,
                        "paragraphs": [],
                        "fetched": False,
                    }
                )
