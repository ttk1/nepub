from unittest import TestCase
from unittest.mock import patch

from nepub.parser.narou import NarouEpisodeParser, NarouIndexParser


class TestNarouEpisodeParser(TestCase):
    def test_narou_episode_parser(self):
        parser = NarouEpisodeParser()
        parser.feed(
            """
            <h1 class="p-novel__title p-novel__title--rensai">タイトルA</h1>
            <p id="L1">　段落1</p>
            <p id="L2"><br /></p>
            <p id="L3"></p>
            <p id="L4">「段落4」</p>
            <p id="L5"></p>
            <p id="L6">"段落6"</p>
            <p id="L7">　　　　</p>
            <p id="L8">    </p>
            """
        )
        self.assertEqual("タイトルA", parser.title)
        self.assertEqual(
            ["　段落1", "<br />", "「段落4」", "&quot;段落6&quot;", "<br />"],
            parser.paragraphs,
        )

    def test_narou_episode_parser_ruby(self):
        parser = NarouEpisodeParser()
        parser.feed(
            """
            <h1 class="p-novel__title p-novel__title--rensai">タイトルA</h1>
            <p id="L1">あああ<ruby>段落1<rt>だんらくいち</rt></ruby>あああ</p>
            <p id="L2">いいい<ruby>段落2<rp>(</rp><rt>だんらくに</rt><rp>)</rp></ruby>いいい</p>
            <p id="L3">ううう<ruby><rb>段落3</rb><rt>だんらくさん</rt></ruby>ううう</p>
            <p id="L3">えええ<ruby><rb>段落4</rb><rt>だんらくよん</rt></ruby>えええ</p>
            """
        )
        self.assertEqual("タイトルA", parser.title)
        self.assertEqual(
            [
                "あああ<ruby>段落1<rt>だんらくいち</rt></ruby>あああ",
                "いいい<ruby>段落2<rt>だんらくに</rt></ruby>いいい",
                "ううう<ruby>段落3<rt>だんらくさん</rt></ruby>ううう",
                "えええ<ruby>段落4<rt>だんらくよん</rt></ruby>えええ",
            ],
            parser.paragraphs,
        )

    @patch("nepub.parser.narou.get_image")
    def test_narou_episode_parser_image(self, get_image):
        get_image.return_value = {
            "id": "test_id",
            "name": "test_name",
            "type": "image/jpeg",
            "data": b"test_data",
        }
        parser = NarouEpisodeParser(include_images=True)
        parser.feed(
            """
            <p id="L1"><a href="//example.com/href" target="_blank"><img src="//12345.mitemin.net/userpageimage/viewimagebig/icode/i12345/" alt="test_alt" border="0" /></a></p>
            """
        )
        self.assertEqual(
            ['<img alt="test_alt" src="../image/test_name"/>'], parser.paragraphs
        )
        self.assertEqual(
            "https://12345.mitemin.net/userpageimage/viewimagebig/icode/i12345/",
            get_image.call_args[0][0],
        )

    def test_narou_episode_parser_tcy(self):
        parser = NarouEpisodeParser(convert_tcy=True)
        parser.feed(
            """
            <h1 class="p-novel__title p-novel__title--rensai">タイトルX</h1>
            <p id="L1">今日は6月28日です!?</p>
            <p id="L2">This is a pen.</p>
            """
        )
        self.assertEqual("タイトルＸ", parser.title)
        self.assertEqual(
            [
                '今日は６月<span class="tcy">28</span>日です<span class="tcy">⁉</span>',
                "This is a pen.",
            ],
            parser.paragraphs,
        )


class TestNarouIndexParser(TestCase):
    def test_narou_index_parser(self):
        parser = NarouIndexParser()
        parser.feed(
            """
            <h1 class="p-novel__title">タイトル</h1>
            <div class="p-novel__author">
                作者：<a href="https://mypage.syosetu.com/xxxx/">作者</a>
            </div>
            <span class="c-pager__item c-pager__item--first">最初へ</span>
            <span class="c-pager__item c-pager__item--before">前へ</span>
            <a href="/xxxx/?p=2" class="c-pager__item c-pager__item--next">次へ</a>
            <a href="/xxxx/?p=9" class="c-pager__item c-pager__item--last">最後へ</a>
            <div class="p-eplist__chapter-title">チャプター1</div>
            <div class="p-eplist__sublist">
                <a href="/xxxx/1/" class="p-eplist__subtitle">エピソード1</a>
                <div class="p-eplist__update">1999/01/01 00:00</div>
            </div>
            <div class="p-eplist__sublist">
                <a href="/xxxx/2/" class="p-eplist__subtitle">エピソード2</a>
                <div class="p-eplist__update">
                    1999/01/02 00:00
                    <span title="2000/01/02 00:00 改稿">（<u>改</u>）</span>
                </div>
            </div>
            <div class="p-eplist__chapter-title">チャプター2</div>
            <div class="p-eplist__sublist">
                <a href="/xxxx/3/" class="p-eplist__subtitle">エピソード3</a>
                <div class="p-eplist__update">1999/01/03 00:00</div>
            </div>
            """
        )
        self.assertEqual("タイトル", parser.title)
        self.assertEqual("作者", parser.author)
        self.assertEqual("2", parser.next_page)
        self.assertEqual(
            [
                {"name": "default", "episodes": []},
                {
                    "name": "チャプター1",
                    "episodes": [
                        {
                            "id": "1",
                            "title": "",
                            "created_at": "1999/01/01 00:00",
                            "updated_at": "",
                            "paragraphs": [],
                            "fetched": False,
                        },
                        {
                            "id": "2",
                            "title": "",
                            "created_at": "1999/01/02 00:00",
                            "updated_at": "2000/01/02 00:00",
                            "paragraphs": [],
                            "fetched": False,
                        },
                    ],
                },
                {
                    "name": "チャプター2",
                    "episodes": [
                        {
                            "id": "3",
                            "title": "",
                            "created_at": "1999/01/03 00:00",
                            "updated_at": "",
                            "paragraphs": [],
                            "fetched": False,
                        }
                    ],
                },
            ],
            parser.chapters,
        )

    def test_narou_index_parser_last_page(self):
        parser = NarouIndexParser()
        parser.feed(
            """
            <h1 class="p-novel__title">タイトル</h1>
            <div class="p-novel__author">
                作者：作者
            </div>
            <a href="/xxxx/" class="c-pager__item c-pager__item--first">最初へ</a>
            <a href="/xxxx/?p=9" class="c-pager__item c-pager__item--before">前へ</a>
            <span class="c-pager__item c-pager__item--next">次へ</span>
            <span class="c-pager__item c-pager__item--last">最後へ</span>
            <div class="p-eplist__sublist">
                <a href="/xxxx/999/" class="p-eplist__subtitle">エピソード1</a>
                <div class="p-eplist__update">1999/12/31 23:59</div>
            </div>
            """
        )
        self.assertEqual("タイトル", parser.title)
        self.assertEqual("作者", parser.author)
        self.assertEqual(None, parser.next_page)
        self.assertEqual(
            [
                {
                    "name": "default",
                    "episodes": [
                        {
                            "id": "999",
                            "title": "",
                            "created_at": "1999/12/31 23:59",
                            "updated_at": "",
                            "paragraphs": [],
                            "fetched": False,
                        },
                    ],
                },
            ],
            parser.chapters,
        )
