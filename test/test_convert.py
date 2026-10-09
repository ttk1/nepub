import io
import json
import os
import re
import tempfile
import zipfile
from contextlib import redirect_stdout
from typing import Any
from unittest import TestCase
from unittest.mock import patch

from nepub.convert import convert_to_epub

NOVEL_ID = "n0000aa"
INDEX_URL = f"https://ncode.syosetu.com/{NOVEL_ID}/?p="
EPISODE_URL = f"https://ncode.syosetu.com/{NOVEL_ID}/"


def narou_episode(num: str, published: str, updated: str | None = None):
    update = f'<span title="{updated} 改稿">（<u>改</u>）</span>' if updated else ""
    return f"""
        <div class="p-eplist__sublist">
            <a href="/{NOVEL_ID}/{num}/" class="p-eplist__subtitle">エピソード{num}</a>
            <div class="p-eplist__update">{published}{update}</div>
        </div>
    """


def narou_index(body: str, next_page: str | None = None):
    pager = (
        f'<a href="/{NOVEL_ID}/?p={next_page}" class="c-pager__item c-pager__item--next">次へ</a>'
        if next_page
        else ""
    )
    return f"""
        <h1 class="p-novel__title">小説</h1>
        <div class="p-novel__author">作者：作者</div>
        {pager}
        {body}
    """


def narou_page(title: str, body: str):
    return f"""
        <h1 class="p-novel__title p-novel__title--rensai">{title}</h1>
        <p id="L1">{body}</p>
    """


def narou_site(ep2_updated: str | None = None, with_ep5: bool = False):
    """2 ページに分かれた目次 (第一章: 1-3, 第二章: 4-5) と各話のページ"""
    page2 = narou_episode("3", "2024/01/03 00:00")
    page2 += '<div class="p-eplist__chapter-title">第二章</div>'
    page2 += narou_episode("4", "2024/01/04 00:00")
    if with_ep5:
        page2 += narou_episode("5", "2024/01/05 00:00")
    pages = {
        INDEX_URL + "1": narou_index(
            '<div class="p-eplist__chapter-title">第一章</div>'
            + narou_episode("1", "2024/01/01 00:00")
            + narou_episode("2", "2024/01/02 00:00", ep2_updated),
            next_page="2",
        ),
        INDEX_URL + "2": narou_index(page2),
    }
    for num in ["1", "2", "3", "4", "5"]:
        body = f"本文{num}" + ("（改稿）" if num == "2" and ep2_updated else "")
        pages[f"{EPISODE_URL}{num}/"] = narou_page(f"タイトル{num}", body)
    return pages


class FakeWeb:
    def __init__(self, pages: dict[str, str]):
        self.pages = pages
        self.requested: list[str] = []

    def get(self, url: str) -> str:
        self.requested.append(url)
        return self.pages[url]


class TestConvert(TestCase):
    """EPUB を更新する際、各エピソードは次のパターンに分かれる

    | 元のファイル | range  | 更新 | 動作                       | テスト                  |
    |--------------|--------|------|----------------------------|-------------------------|
    | なし         | 範囲内 | -    | 新しく取得                 | test_update, test_range |
    | なし         | 範囲外 | -    | 含めない                   | test_range              |
    | あり         | 範囲外 | なし | 元のファイルのものを引き継ぐ | test_range              |
    | あり         | 範囲外 | あり | 元のファイルのものを引き継ぐ | test_range              |
    | あり         | 範囲内 | あり | 新しく取得                 | test_update             |
    | あり         | 範囲内 | なし | 元のファイルのものを引き継ぐ | test_update             |

    range を指定しない場合は全話が範囲内になる。
    """

    def setUp(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.output = os.path.join(tmp_dir.name, "novel.epub")

    def convert(
        self,
        web: FakeWeb,
        novel_id=NOVEL_ID,
        illustration=False,
        tcy=False,
        my_range=None,
        kakuyomu=False,
    ) -> list[str]:
        """変換を実行し、標準出力の各行を返す"""
        web.requested.clear()
        out = io.StringIO()
        with redirect_stdout(out):
            convert_to_epub(
                novel_id,
                illustration=illustration,
                tcy=tcy,
                my_range=my_range,
                output=self.output,
                kakuyomu=kakuyomu,
                fetch=web.get,
            )
        return out.getvalue().splitlines()

    def read(self, name: str) -> str:
        with zipfile.ZipFile(self.output) as zf:
            return zf.read(name).decode("utf-8")

    def namelist(self) -> list[str]:
        with zipfile.ZipFile(self.output) as zf:
            return zf.namelist()

    def spine(self) -> list[str]:
        return re.findall(
            r'<itemref linear="yes" idref="(\w+)" />', self.read("src/content.opf")
        )

    def nav(self) -> list[tuple[str, str]]:
        return re.findall(
            r'<a href="text/(\w+)\.xhtml">(.*?)</a>', self.read("src/navigation.xhtml")
        )

    def metadata(self):
        return json.loads(self.read("src/metadata.json"))

    def test_create(self):
        web = FakeWeb(narou_site())
        lines = self.convert(web)

        self.assertEqual(
            [INDEX_URL + "1", INDEX_URL + "2"]
            + [f"{EPISODE_URL}{num}/" for num in ["1", "2", "3", "4"]],
            web.requested,
        )
        self.assertEqual(
            [
                f"novel_id: {NOVEL_ID}, illustration: False, tcy: False, output: {self.output}, kakuyomu: False",
                "title: 小説",
                "author: 作者",
                "4 episodes found.",
                "Start downloading...",
                f"Downloading (1/4): {EPISODE_URL}1/",
                f"Downloading (2/4): {EPISODE_URL}2/",
                f"Downloading (3/4): {EPISODE_URL}3/",
                f"Downloading (4/4): {EPISODE_URL}4/",
                "Download is complete! (new: 4, skipped: 0)",
                f"Created {self.output}.",
            ],
            lines,
        )
        self.assertEqual(
            [
                "mimetype",
                "src/text/1.xhtml",
                "src/text/2.xhtml",
                "src/text/3.xhtml",
                "src/text/4.xhtml",
                "META-INF/container.xml",
                "src/style.css",
                "src/content.opf",
                "src/navigation.xhtml",
                "src/metadata.json",
            ],
            self.namelist(),
        )
        with zipfile.ZipFile(self.output) as zf:
            self.assertEqual(zipfile.ZIP_STORED, zf.getinfo("mimetype").compress_type)
        self.assertEqual("application/epub+zip", self.read("mimetype"))
        self.assertIn("<h1>タイトル1</h1>", self.read("src/text/1.xhtml"))
        self.assertIn("<p>本文1</p>", self.read("src/text/1.xhtml"))
        self.assertEqual(["1", "2", "3", "4"], self.spine())
        self.assertEqual(
            [
                ("1", "第一章"),
                ("1", "タイトル1"),
                ("2", "タイトル2"),
                ("3", "タイトル3"),
                ("4", "第二章"),
                ("4", "タイトル4"),
            ],
            self.nav(),
        )
        self.assertEqual(
            {
                "novel_id": NOVEL_ID,
                "kakuyomu": False,
                "illustration": False,
                "tcy": False,
                "episodes": {
                    num: {
                        "id": num,
                        "title": f"タイトル{num}",
                        "created_at": f"2024/01/0{num} 00:00",
                        "updated_at": "",
                        "images": [],
                    }
                    for num in ["1", "2", "3", "4"]
                },
            },
            self.metadata(),
        )

    def test_update(self):
        """range を指定せずに更新する (全話が範囲内)"""
        # 1 回目: 1-4 話で作成
        self.convert(FakeWeb(narou_site()))
        text1 = self.read("src/text/1.xhtml")

        # 2 回目: 2 話を更新ありにし、5 話を追加して更新
        web = FakeWeb(narou_site(ep2_updated="2024/02/01 00:00", with_ep5=True))
        lines = self.convert(web)

        # 更新された話 (2) と新しい話 (5) だけをダウンロードする
        self.assertEqual(
            [INDEX_URL + "1", INDEX_URL + "2", f"{EPISODE_URL}2/", f"{EPISODE_URL}5/"],
            web.requested,
        )
        self.assertEqual(
            [
                f"novel_id: {NOVEL_ID}, illustration: False, tcy: False, output: {self.output}, kakuyomu: False",
                f"{self.output} found. Loading metadata for update.",
                "title: 小説",
                "author: 作者",
                "5 episodes found.",
                "Start downloading...",
                f"Download skipped (already up to date) (1/5): {EPISODE_URL}1/",
                f"Downloading (2/5): {EPISODE_URL}2/",
                f"Download skipped (already up to date) (3/5): {EPISODE_URL}3/",
                f"Download skipped (already up to date) (4/5): {EPISODE_URL}4/",
                f"Downloading (5/5): {EPISODE_URL}5/",
                "Download is complete! (new: 2, skipped: 3)",
                f"Updated {self.output}.",
            ],
            lines,
        )
        # [あり・範囲内・更新なし] 1, 3, 4 話: 元のファイルのものを引き継ぐ
        self.assertEqual(text1, self.read("src/text/1.xhtml"))
        # [あり・範囲内・更新あり] 2 話: 新しく取得する
        self.assertIn("<p>本文2（改稿）</p>", self.read("src/text/2.xhtml"))
        # [なし・範囲内] 5 話: 新しく取得して追加する
        self.assertEqual(["1", "2", "3", "4", "5"], self.spine())
        self.assertEqual(("5", "タイトル5"), self.nav()[-1])
        self.assertEqual(
            "2024/02/01 00:00", self.metadata()["episodes"]["2"]["updated_at"]
        )
        # 一時ファイルが残っていない
        self.assertEqual(["novel.epub"], os.listdir(os.path.dirname(self.output)))

    def test_range(self):
        """range を指定して作成・更新する"""
        # 1 回目: range=2-3 で作成
        web = FakeWeb(narou_site())
        self.convert(web, my_range="2-3")
        # [なし・範囲内] 2, 3 話: 新しく取得する
        # [なし・範囲外] 1, 4 話: 含めない
        self.assertEqual(
            [INDEX_URL + "1", INDEX_URL + "2", f"{EPISODE_URL}2/", f"{EPISODE_URL}3/"],
            web.requested,
        )
        self.assertEqual(["2", "3"], self.spine())
        self.assertEqual(
            [("2", "第一章"), ("2", "タイトル2"), ("3", "タイトル3")], self.nav()
        )
        self.assertEqual(["2", "3"], list(self.metadata()["episodes"]))

        # 2 回目: 2 話を更新ありにして range=4 で更新
        web = FakeWeb(narou_site(ep2_updated="2024/02/01 00:00"))
        lines = self.convert(web, my_range="4")
        # [なし・範囲内] 4 話だけを新しく取得する
        self.assertEqual(
            [INDEX_URL + "1", INDEX_URL + "2", f"{EPISODE_URL}4/"], web.requested
        )
        self.assertIn("Download is complete! (new: 1, skipped: 0)", lines)
        # [なし・範囲外] 1 話: 引き続き含めない
        self.assertEqual(["2", "3", "4"], self.spine())
        self.assertEqual(["2", "3", "4"], list(self.metadata()["episodes"]))
        # [あり・範囲外・更新なし] 3 話: 元のファイルのものを引き継ぐ
        self.assertIn("<p>本文3</p>", self.read("src/text/3.xhtml"))
        # [あり・範囲外・更新あり] 2 話: 更新があっても取得せず元のファイルのものを引き継ぐ
        # (metadata も古いままなので、次に範囲内で更新したときに取得される)
        self.assertIn("<p>本文2</p>", self.read("src/text/2.xhtml"))
        self.assertEqual("", self.metadata()["episodes"]["2"]["updated_at"])

    def test_options_differ_from_metadata(self):
        web = FakeWeb(narou_site())
        self.convert(web)
        with open(self.output, "rb") as f:
            before = f.read()

        cases: list[tuple[dict[str, Any], str]] = [
            ({"novel_id": "n9999zz"}, "the novel_id differs from metadata: n0000aa"),
            (
                {"illustration": True},
                "the illustration value differs from metadata: False",
            ),
            ({"tcy": True}, "the tcy value differs from metadata: False"),
        ]
        for kwargs, message in cases:
            with self.subTest(kwargs=kwargs):
                lines = self.convert(web, **kwargs)
                self.assertEqual(f"Process stopped as {message}", lines[-1])
                self.assertEqual([], web.requested)
                with open(self.output, "rb") as f:
                    self.assertEqual(before, f.read())

    def test_invalid_novel_id(self):
        web = FakeWeb({})
        lines = self.convert(web, novel_id="n0000aa/../x")
        self.assertEqual(
            "Process stopped as the novel_id is invalid: n0000aa/../x", lines[-1]
        )
        self.assertEqual([], web.requested)

    @patch("nepub.parser.narou.get_image")
    def test_unsafe_image_in_metadata(self, get_image):
        get_image.return_value = {
            "id": "0123456789abcdef0123456789abcdef",
            "name": "0123456789abcdef0123456789abcdef.png",
            "type": "image/png",
            "data": b"png data",
        }
        pages = narou_site()
        pages[f"{EPISODE_URL}1/"] = narou_page(
            "タイトル1",
            '<img src="//1.mitemin.net/userpageimage/viewimagebig/icode/i1/" alt="挿絵">',
        )
        updated_pages = {**pages, **narou_site(ep2_updated="2024/02/01 00:00")}
        updated_pages[f"{EPISODE_URL}1/"] = pages[f"{EPISODE_URL}1/"]

        # 既存の EPUB の metadata.json に仕込まれた不正な挿絵の情報
        cases = [
            ("name", "../../evil.png", "ファイル名に使えない"),
            ("id", 'x" onload="evil', "ファイル名に使えない"),
            ("type", "text/html", "画像の形式"),
        ]
        for key, value, message in cases:
            with self.subTest(key=key):
                if os.path.exists(self.output):
                    os.remove(self.output)
                self.convert(FakeWeb(pages), illustration=True)
                self.tamper_image_metadata(episode_id="1", key=key, value=value)
                with open(self.output, "rb") as f:
                    before = f.read()

                # 挿絵のある 1 話を元のファイルから引き継ぐ更新を行う
                with self.assertRaisesRegex(ValueError, message):
                    self.convert(FakeWeb(updated_pages), illustration=True)

                # 元のファイルはそのまま残り、一時ファイルも残らない
                with open(self.output, "rb") as f:
                    self.assertEqual(before, f.read())
                self.assertEqual(
                    ["novel.epub"], os.listdir(os.path.dirname(self.output))
                )

    def tamper_image_metadata(self, episode_id: str, key: str, value: str):
        """既存の EPUB の metadata.json にあるエピソードの挿絵の情報を書き換える"""
        with zipfile.ZipFile(self.output) as zf:
            entries = {name: zf.read(name) for name in zf.namelist()}
        metadata = json.loads(entries["src/metadata.json"])
        metadata["episodes"][episode_id]["images"][0][key] = value
        entries["src/metadata.json"] = json.dumps(metadata).encode("utf-8")
        with zipfile.ZipFile(self.output, "w") as zf:
            for name, data in entries.items():
                zf.writestr(name, data)

    def test_kakuyomu_with_illustration(self):
        web = FakeWeb({})
        lines = self.convert(web, illustration=True, kakuyomu=True)
        self.assertEqual(
            "Process stopped as illustration option is not supported for Kakuyomu.",
            lines[-1],
        )
        self.assertFalse(os.path.exists(self.output))

    @patch("nepub.parser.narou.get_image")
    def test_illustration(self, get_image):
        get_image.return_value = {
            "id": "0123456789abcdef0123456789abcdef",
            "name": "0123456789abcdef0123456789abcdef.png",
            "type": "image/png",
            "data": b"png data",
        }
        pages = narou_site()
        pages[f"{EPISODE_URL}1/"] = narou_page(
            "タイトル1",
            '<img src="//1.mitemin.net/userpageimage/viewimagebig/icode/i1/" alt="挿絵">',
        )
        self.convert(FakeWeb(pages), illustration=True)

        # 挿絵のある話を再ダウンロードしなくても、挿絵は既存のファイルから引き継ぐ
        pages.update(narou_site(ep2_updated="2024/02/01 00:00"))
        pages[f"{EPISODE_URL}1/"] = "unused"
        web = FakeWeb(pages)
        self.convert(web, illustration=True)

        self.assertNotIn(f"{EPISODE_URL}1/", web.requested)
        self.assertEqual(1, get_image.call_count)
        with zipfile.ZipFile(self.output) as zf:
            self.assertEqual(
                b"png data", zf.read("src/image/0123456789abcdef0123456789abcdef.png")
            )
        self.assertIn(
            '<img alt="挿絵" src="../image/0123456789abcdef0123456789abcdef.png"/>',
            self.read("src/text/1.xhtml"),
        )
        self.assertIn(
            'href="image/0123456789abcdef0123456789abcdef.png"',
            self.read("src/content.opf"),
        )


class TestConvertKakuyomu(TestCase):
    def test_create(self):
        work_id = "1000"
        state = {
            f"Work:{work_id}": {
                "title": "カクヨム小説",
                "author": {"__ref": "UserAccount:1"},
                "tableOfContentsV2": [{"__ref": "TableOfContentsChapter:1"}],
            },
            "UserAccount:1": {"activityName": "カクヨム作者"},
            "TableOfContentsChapter:1": {
                "chapter": None,
                "episodeUnions": [{"__ref": "Episode:11"}, {"__ref": "Episode:12"}],
            },
            "Episode:11": {"id": "11", "publishedAt": "2024-01-01T00:00:00Z"},
            "Episode:12": {"id": "12", "publishedAt": "2024-01-02T00:00:00Z"},
        }
        next_data = {
            "query": {"workId": work_id},
            "props": {"pageProps": {"__APOLLO_STATE__": state}},
        }
        base = f"https://kakuyomu.jp/works/{work_id}"
        web = FakeWeb(
            {
                base: f'<script id="__NEXT_DATA__">{json.dumps(next_data)}</script>',
                f"{base}/episodes/11": '<h1 class="widget-episodeTitle">話1</h1><p id="p1">本文</p>',
                f"{base}/episodes/12": '<h1 class="widget-episodeTitle">話2</h1><p id="p1">本文</p>',
            }
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = os.path.join(tmp_dir, "novel.epub")
            with redirect_stdout(io.StringIO()):
                convert_to_epub(
                    work_id,
                    illustration=False,
                    tcy=False,
                    my_range=None,
                    output=output,
                    kakuyomu=True,
                    fetch=web.get,
                )
            with zipfile.ZipFile(output) as zf:
                metadata = json.loads(zf.read("src/metadata.json"))
                text = zf.read("src/text/12.xhtml").decode("utf-8")

        self.assertEqual(
            [base, f"{base}/episodes/11", f"{base}/episodes/12"], web.requested
        )
        self.assertTrue(metadata["kakuyomu"])
        self.assertEqual(["11", "12"], list(metadata["episodes"]))
        self.assertIn("<h1>話2</h1>", text)
