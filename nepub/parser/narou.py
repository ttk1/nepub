import html
import re
from html.parser import HTMLParser
from typing import List

from nepub.http import get_image
from nepub.type import Chapter, Image
from nepub.util import tcy


class NarouEpisodeParser(HTMLParser):
    PARAGRAPH_ID_PATTERN = re.compile(r"L[1-9][0-9]*")
    IMG_SRC_PATTERN = re.compile(
        r"//[1-9][0-9]*.mitemin.net/userpageimage/viewimagebig/icode/i[1-9][0-9]*/"
    )
    EPISODE_TITLE_CLASS = "p-novel__title"

    def __init__(self, include_images=False, convert_tcy=False):
        super().__init__()
        self.include_images = include_images
        self.convert_tcy = convert_tcy

    def reset(self):
        super().reset()
        self._title = ""
        self.paragraphs: List[str] = []
        self.images: List[Image] = []
        self._tag_stack: List[str | None] = [None, None]
        self._id_stack: List[str | None] = [None]
        self._classes_stack: List[List[str] | None] = [None]
        self._paragraph_flg = False
        self._current_paragraph = ""
        self._paragraph_buff = ""
        self._consecutive_blank_paragraphs = 0

    @property
    def title(self):
        if self.convert_tcy:
            return tcy(html.escape(self._title).strip())
        else:
            return html.escape(self._title).strip()

    def handle_starttag(self, tag, attrs):
        # バッファのデータをエスケープ & 縦中横処理し _current_paragraph に連結
        if self.convert_tcy:
            self._current_paragraph += tcy(html.escape(self._paragraph_buff))
        else:
            self._current_paragraph += html.escape(self._paragraph_buff)
        self._paragraph_buff = ""
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
        if self._id_stack[-1] is not None and self.PARAGRAPH_ID_PATTERN.fullmatch(
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
                        img_alt = html.escape(attr[1])
                    elif attr[0] == "src":
                        if not self.IMG_SRC_PATTERN.fullmatch(attr[1]):
                            raise Exception(f"img_src が想定しない形式です: {attr[1]}")
                        img_src = attr[1]
                if img_src:
                    image = get_image(f"https:{img_src}")
                    self._current_paragraph += (
                        f'<img alt="{img_alt.strip()}" src="../image/{image["name"]}"/>'
                    )
                    self.images.append(image)

    def handle_endtag(self, tag):
        # バッファのデータをエスケープ & 縦中横処理し _current_paragraph に連結
        if self.convert_tcy:
            self._current_paragraph += tcy(html.escape(self._paragraph_buff))
        else:
            self._current_paragraph += html.escape(self._paragraph_buff)
        self._paragraph_buff = ""
        # ruby, rt, p
        # rb タグは省略する
        if self._paragraph_flg:
            if tag == "ruby":
                self._current_paragraph += "</ruby>"
            elif tag == "rt":
                self._current_paragraph += "</rt>"
            elif tag == "p":
                # 先頭の字下げを残すため rstrip にしている
                paragraph = self._current_paragraph.rstrip()
                if paragraph:
                    self._consecutive_blank_paragraphs = 0
                    self.paragraphs.append(paragraph)
                else:
                    # 連続しない空行はそのまま除去
                    # 2 回以上連続する空行は一つの空行として出力する
                    self._consecutive_blank_paragraphs += 1
                    if self._consecutive_blank_paragraphs == 2:
                        self.paragraphs.append("<br />")
                self._current_paragraph = ""
        # paragraph_flg
        if self._id_stack[-1] is not None and self.PARAGRAPH_ID_PATTERN.fullmatch(
            self._id_stack[-1]
        ):
            self._paragraph_flg = False
        # tag, id, classes をスタックからおろす
        self._tag_stack.pop()
        self._id_stack.pop()
        self._classes_stack.pop()

    def handle_data(self, data):
        # ruby, rb, rt, p
        if self._paragraph_flg and self._tag_stack[-1] in ["ruby", "rb", "rt", "p"]:
            # 分割して処理されることを考慮し一旦バッファに入れる
            self._paragraph_buff += data
        # title
        if (
            self._classes_stack[-1] is not None
            and self.EPISODE_TITLE_CLASS in self._classes_stack[-1]
        ):
            self._title += data


class NarouIndexParser(HTMLParser):
    NEXT_PAGE_PATTERN = re.compile(r"/[a-z0-9]+/\?p=([1-9][0-9]*)")
    EPISODE_ID_PATTERN = re.compile(r"/[a-z0-9]+/([1-9][0-9]*)/")

    def reset(self):
        super().reset()
        self._title = ""
        self._author = ""
        self.next_page = None
        self.chapters: List[Chapter] = [{"name": "default", "episodes": []}]
        self._classes_stack: List[List[str] | None] = [None, None]
        self._current_chapter = ""
        self._current_episode_created_at = ""

    @property
    def title(self):
        return html.escape(self._title).strip()

    @property
    def author(self):
        return html.escape(self._author).strip().removeprefix("作者：")

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
                    m = self.NEXT_PAGE_PATTERN.fullmatch(attr[1])
                    if not m:
                        raise Exception(f"next_page が認識できませんでした: {attr[1]}")
                    self.next_page = m.group(1)
        # episode_id
        if (
            self._classes_stack[-1] is not None
            and "p-eplist__subtitle" in self._classes_stack[-1]
        ):
            for attr in attrs:
                if attr[0] == "href":
                    m = self.EPISODE_ID_PATTERN.fullmatch(attr[1])
                    if not m:
                        raise Exception(f"episode_id が認識できませんでした: {attr[1]}")
                    self.chapters[-1]["episodes"].append(
                        {
                            "id": m.group(1),
                            "title": "",
                            "created_at": "",
                            "updated_at": "",
                            "paragraphs": [],
                            "fetched": False,
                        }
                    )
        # episode_updated_at
        if tag == "span":
            for attr in attrs:
                if attr[0] == "title":
                    self.chapters[-1]["episodes"][-1]["updated_at"] = html.escape(
                        attr[1].strip().replace(" 改稿", "")
                    )

    def handle_endtag(self, tag):
        if tag == "div":
            if self._current_chapter:
                self.chapters.append(
                    {"name": html.escape(self._current_chapter).strip(), "episodes": []}
                )
                self._current_chapter = ""
            elif self._current_episode_created_at:
                self.chapters[-1]["episodes"][-1]["created_at"] = html.escape(
                    self._current_episode_created_at
                ).strip()
                self._current_episode_created_at = ""
        # classes をスタックからおろす
        self._classes_stack.pop()

    def handle_data(self, data):
        # title
        if (
            self._classes_stack[-1] is not None
            and "p-novel__title" in self._classes_stack[-1]
        ):
            self._title += data
        # author
        # 作者名がリンクになってる場合となっていない場合を考慮
        if (
            self._classes_stack[-1] is not None
            and "p-novel__author" in self._classes_stack[-1]
        ) or (
            self._classes_stack[-2] is not None
            and "p-novel__author" in self._classes_stack[-2]
        ):
            self._author += data
        # chapter
        if (
            self._classes_stack[-1] is not None
            and "p-eplist__chapter-title" in self._classes_stack[-1]
        ):
            self._current_chapter += data
        # episode_created_at
        if (
            self._classes_stack[-1] is not None
            and "p-eplist__update" in self._classes_stack[-1]
        ):
            self._current_episode_created_at += data
