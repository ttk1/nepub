import html
from html.parser import HTMLParser
import re
from typing import List
from nepub.http import get_image
from nepub.type import Chapter, Image


PARAGRAPH_ID_PATTERN = re.compile(r"L[1-9][0-9]*")
EPISODE_ID_PATTERN = re.compile(r"/[a-z0-9]+/([1-9][0-9]*)/")


class NarouEpisodeParser(HTMLParser):
    def __init__(self, include_images=False):
        super().__init__()
        self.include_images = include_images

    def reset(self):
        super().reset()
        self.title = ""
        self.paragraphs: List[str] = []
        self.images: List[Image] = []
        self._tag_stack: List[str | None] = [None, None]
        self._id_stack: List[str | None] = [None]
        self._classes_stack: List[List[str] | None] = [None]
        self._paragraph_flg = False
        self._current_paragraph = ""

    def handle_starttag(self, tag, attrs):
        # tag, id, classes をスタックに積む
        self._tag_stack.append(tag)
        self._id_stack.append(None)
        self._classes_stack.append(None)
        for attr in attrs:
            if attr[0] == "id":
                self._id_stack[-1] = attr[1]
            if attr[0] == "class":
                self._classes_stack[-1] = attr[1].split()
        # paragraph_flg
        if self._id_stack[-1] is not None and PARAGRAPH_ID_PATTERN.fullmatch(
            self._id_stack[-1]
        ):
            self._paragraph_flg = True
        # ruby, rt (rb タグは省略する) の処理
        # include_images が設定されている場合は img も処理する
        if self._paragraph_flg:
            if tag == "ruby":
                self._current_paragraph += "<ruby>"
            elif tag == "rt":
                self._current_paragraph += "<rt>"
            elif self.include_images and tag == "img":
                img_alt = ""
                img_src = ""
                for attr in attrs:
                    if attr[0] == "alt":
                        img_alt = attr[1]
                    elif attr[0] == "src":
                        img_src = attr[1]
                if img_src:
                    image = get_image(f"https:{img_src}")
                    self._current_paragraph += (
                        f'<img alt="{img_alt}" src="../image/{image["name"]}"/>'
                    )
                    self.images.append(image)

    def handle_endtag(self, tag):
        # ruby, rt, p
        # rb タグは省略する
        if self._paragraph_flg:
            if tag == "ruby":
                self._current_paragraph += "</ruby>"
            elif tag == "rt":
                self._current_paragraph += "</rt>"
            elif tag == "p" and self._current_paragraph:
                # 空の段落は読み飛ばす
                self.paragraphs.append(self._current_paragraph)
                self._current_paragraph = ""
        # paragraph_flg
        if self._id_stack[-1] is not None and PARAGRAPH_ID_PATTERN.fullmatch(
            self._id_stack[-1]
        ):
            self._paragraph_flg = False
        # tag, id, classes をスタックからおろす
        self._tag_stack.pop()
        self._id_stack.pop()
        self._classes_stack.pop()

    def handle_data(self, data):
        # ruby, rt, p
        if self._paragraph_flg and self._tag_stack[-1] in ["ruby", "rb", "rt", "p"]:
            self._current_paragraph += html.escape(data.rstrip())
        # title
        if (
            self._classes_stack[-1] is not None
            and "p-novel__title" in self._classes_stack[-1]
        ):
            self.title += html.escape(data.rstrip())


class NarouIndexParser(HTMLParser):
    def reset(self):
        super().reset()
        self.title = ""
        self.author = ""
        self.next_page = None
        self.chapters: List[Chapter] = [{"name": "default", "episodes": []}]
        self._classes_stack: List[List[str] | None] = [None, None]
        self._current_chapter: str = ""

    def handle_starttag(self, tag, attrs):
        # classes をスタックに積む
        self._classes_stack.append(None)
        for attr in attrs:
            if attr[0] == "class":
                self._classes_stack[-1] = attr[1].split()
        # next_page
        if (
            self._classes_stack[-1] is not None
            and "c-pager__item--next" in self._classes_stack[-1]
        ):
            for attr in attrs:
                if attr[0] == "href":
                    self.next_page = attr[1]
        # episode_id
        if (
            self._classes_stack[-1] is not None
            and "p-eplist__subtitle" in self._classes_stack[-1]
        ):
            for attr in attrs:
                if attr[0] == "href":
                    m = EPISODE_ID_PATTERN.fullmatch(attr[1])
                    if not m:
                        raise Exception(f"episode_id が認識できませんでした: {attr[1]}")
                    self.chapters[-1]["episodes"].append(
                        {
                            "id": m.group(1),
                            "title": "",
                            "paragraphs": [],
                        }
                    )

    def handle_endtag(self, tag):
        if tag == "div" and self._current_chapter:
            self.chapters.append({"name": self._current_chapter, "episodes": []})
            self._current_chapter = ""
        # classes をスタックからおろす
        self._classes_stack.pop()

    def handle_data(self, data):
        # title
        if (
            self._classes_stack[-1] is not None
            and "p-novel__title" in self._classes_stack[-1]
        ):
            self.title += html.escape(data.rstrip())
        # author
        if (
            self._classes_stack[-2] is not None
            and "p-novel__author" in self._classes_stack[-2]
        ):
            self.author += html.escape(data.rstrip())
        # chapter
        if (
            self._classes_stack[-1] is not None
            and "p-eplist__chapter-title" in self._classes_stack[-1]
        ):
            self._current_chapter += html.escape(data.rstrip())
