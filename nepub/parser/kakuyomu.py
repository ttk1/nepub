import html
import json
import re
from html.parser import HTMLParser
from typing import List

from nepub.parser.narou import NarouEpisodeParser
from nepub.type import Chapter


class KakuyomuEpisodeParser(NarouEpisodeParser):
    PARAGRAPH_ID_PATTERN = re.compile(r"p[1-9][0-9]*")
    EPISODE_TITLE_CLASS = "widget-episodeTitle"

    def __init__(self, convert_tcy=False):
        super().__init__(include_images=False, convert_tcy=convert_tcy)


class KakuyomuIndexParser(HTMLParser):
    def reset(self):
        super().reset()
        self.title = ""
        self.author = ""
        self.next_page = None
        self.chapters: List[Chapter] = [{"name": "default", "episodes": []}]
        self._json_flg = False
        self._buff = ""

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            for attr in attrs:
                if attr[0] == "id" and attr[1] == "__NEXT_DATA__":
                    self._json_flg = True
                    break

    def handle_endtag(self, tag):
        if tag == "script" and self._json_flg:
            data = json.loads(self._buff)
            work_id = data["query"]["workId"]
            state = data["props"]["pageProps"]["__APOLLO_STATE__"]

            work = state[f"Work:{work_id}"]
            self.title = html.escape(work["title"]).strip()
            self.author = html.escape(
                state[work["author"]["__ref"]]["activityName"]
            ).strip()

            tocs = work["tableOfContents"]
            for toc in tocs:
                toc_chapter_ref = toc["__ref"]
                toc_chapter = state[toc_chapter_ref]
                chapter_ref = toc_chapter["chapter"]
                if chapter_ref is not None:
                    chapter = state[chapter_ref["__ref"]]
                    chapter_name = chapter["title"]
                    self.chapters.append(
                        {"name": html.escape(chapter_name).strip(), "episodes": []}
                    )
                episode_refs = toc_chapter["episodeUnions"]
                for episode_ref in episode_refs:
                    episode = state[episode_ref["__ref"]]
                    self.chapters[-1]["episodes"].append(
                        {
                            "id": html.escape(episode["id"]).strip(),
                            "title": "",
                            "created_at": html.escape(episode["publishedAt"]).strip(),
                            "updated_at": html.escape(episode["publishedAt"]).strip(),
                            "paragraphs": [],
                            "fetched": False,
                        }
                    )

            self._json_flg = False
            self._buff = ""

    def handle_data(self, data):
        if self._json_flg:
            self._buff += data
