import html
import re
from html.parser import HTMLParser

from nepub.http import get_image
from nepub.type import Chapter, Image
from nepub.util import tcy


class NarouEpisodeParser(HTMLParser):
    PARAGRAPH_ID_PATTERN = re.compile(r"L[1-9][0-9]*")
    IMG_SRC_PATTERN = re.compile(
        r"//[1-9][0-9]*\.mitemin\.net/userpageimage/viewimagebig/icode/i[1-9][0-9]*/"
    )
    EPISODE_TITLE_CLASS = "p-novel__title"

    def __init__(self, include_images: bool = False, convert_tcy: bool = False):
        super().__init__()
        self.include_images = include_images
        self.convert_tcy = convert_tcy

    def reset(self):
        super().reset()
        self._title = ""
        self.paragraphs: list[str] = []
        self.images: list[Image] = []
        # handle_data などで先頭のタグより前でも [-1] を参照できるよう番兵を積んでおく
        self._tag_stack: list[str | None] = [None, None]
        self._id_stack: list[str | None] = [None, None]
        self._classes_stack: list[list[str]] = [[], []]
        self._in_paragraph = False
        self._current_paragraph = ""
        self._buff = ""
        self._consecutive_blank_paragraphs = 0

    @property
    def title(self) -> str:
        title = html.escape(self._title).strip()
        return tcy(title) if self.convert_tcy else title

    def _flush_buff(self):
        # バッファのデータをエスケープ & 縦中横処理し、現在の段落に連結する
        text = html.escape(self._buff)
        if self.convert_tcy:
            text = tcy(text)
        self._current_paragraph += text
        self._buff = ""

    def _is_paragraph_id(self, id_: str | None) -> bool:
        return id_ is not None and bool(self.PARAGRAPH_ID_PATTERN.fullmatch(id_))

    def handle_starttag(self, tag, attrs):
        self._flush_buff()
        attrs_dict = dict(attrs)
        self._tag_stack.append(tag)
        self._id_stack.append(attrs_dict.get("id"))
        self._classes_stack.append((attrs_dict.get("class") or "").split())
        if self._is_paragraph_id(self._id_stack[-1]):
            self._in_paragraph = True
        # ruby, rt はそのまま残す (rb タグは省略する)
        # include_images が設定されている場合は img も処理する
        if self._in_paragraph:
            if tag in ("ruby", "rt"):
                self._current_paragraph += f"<{tag}>"
            elif self.include_images and tag == "img":
                self._handle_img(attrs_dict)

    def _handle_img(self, attrs: dict[str, str | None]):
        src = attrs.get("src")
        if src is None:
            return
        if not self.IMG_SRC_PATTERN.fullmatch(src):
            raise ValueError(f"img_src が想定しない形式です: {src}")
        alt = html.escape(attrs.get("alt") or "").strip()
        image = get_image(f"https:{src}")
        self._current_paragraph += f'<img alt="{alt}" src="../image/{image["name"]}"/>'
        self.images.append(image)

    def handle_endtag(self, tag):
        self._flush_buff()
        if self._in_paragraph:
            if tag in ("ruby", "rt"):
                self._current_paragraph += f"</{tag}>"
            elif tag == "p":
                self._close_paragraph()
        if self._is_paragraph_id(self._id_stack[-1]):
            self._in_paragraph = False
        self._tag_stack.pop()
        self._id_stack.pop()
        self._classes_stack.pop()

    def _close_paragraph(self):
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

    def handle_data(self, data):
        # テキストが分割して渡されることを考慮し、一旦バッファに溜める
        if self._in_paragraph and self._tag_stack[-1] in ("ruby", "rb", "rt", "p"):
            self._buff += data
        if self.EPISODE_TITLE_CLASS in self._classes_stack[-1]:
            self._title += data


class NarouIndexParser(HTMLParser):
    NEXT_PAGE_PATTERN = re.compile(r"/[a-z0-9]+/\?p=([1-9][0-9]*)")
    EPISODE_ID_PATTERN = re.compile(r"/[a-z0-9]+/([1-9][0-9]*)/")

    def reset(self):
        super().reset()
        self._title = ""
        self._author = ""
        self.next_page: str | None = None
        self.chapters: list[Chapter] = [{"name": "default", "episodes": []}]
        # handle_data で [-2] まで参照するため番兵を 2 つ積んでおく
        self._classes_stack: list[list[str]] = [[], []]
        self._current_chapter = ""
        self._current_episode_created_at = ""

    @property
    def title(self) -> str:
        return html.escape(self._title).strip()

    @property
    def author(self) -> str:
        return html.escape(self._author).strip().removeprefix("作者：")

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        classes = (attrs_dict.get("class") or "").split()
        self._classes_stack.append(classes)
        href = attrs_dict.get("href")
        # next_page
        if "c-pager__item--next" in classes and href is not None:
            m = self.NEXT_PAGE_PATTERN.fullmatch(href)
            if not m:
                raise ValueError(f"next_page が認識できませんでした: {href}")
            self.next_page = m.group(1)
        # episode_id
        if "p-eplist__subtitle" in classes and href is not None:
            m = self.EPISODE_ID_PATTERN.fullmatch(href)
            if not m:
                raise ValueError(f"episode_id が認識できませんでした: {href}")
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
        # episode_updated_at (改稿日は span タグの title 属性に入っている)
        title_attr = attrs_dict.get("title")
        if tag == "span" and title_attr and self.chapters[-1]["episodes"]:
            self.chapters[-1]["episodes"][-1]["updated_at"] = html.escape(
                title_attr.strip().removesuffix(" 改稿")
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
        self._classes_stack.pop()

    def handle_data(self, data):
        classes = self._classes_stack[-1]
        if "p-novel__title" in classes:
            self._title += data
        # 作者名がリンクになってる場合となっていない場合を考慮
        if "p-novel__author" in classes or "p-novel__author" in self._classes_stack[-2]:
            self._author += data
        if "p-eplist__chapter-title" in classes:
            self._current_chapter += data
        if "p-eplist__update" in classes:
            self._current_episode_created_at += data
