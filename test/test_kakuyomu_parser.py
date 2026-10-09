import json
from unittest import TestCase

from nepub.parser.kakuyomu import KakuyomuEpisodeParser, KakuyomuIndexParser


class TestKakuyomuEpisodeParser(TestCase):
    def test_kakuyomu_episode_parser(self):
        parser = KakuyomuEpisodeParser()
        parser.feed(
            """
            <p class="widget-episodeTitle js-vertical-composition-item">タイトルA</p>
            <p id="p1">　段落1</p>
            <p id="p2"><br /></p>
            <p id="p3"></p>
            <p id="p4">「段落4」</p>
            <p id="p5"></p>
            <p id="p6">"段落6"</p>
            <p id="p7">　　　　</p>
            <p id="p8">    </p>
            """
        )
        self.assertEqual("タイトルA", parser.title)
        self.assertEqual(
            ["　段落1", "<br />", "「段落4」", "&quot;段落6&quot;", "<br />"],
            parser.paragraphs,
        )

    def test_kakuyomu_episode_parser_multiple_br(self):
        parser = KakuyomuEpisodeParser()
        parser.feed(
            """
            <p id="p1">段落1</p>
            <p id="p2" class="blank"><br></p>
            <p id="p3">段落3</p>
            <p id="p4" class="blank"><br><br><br></p>
            <p id="p5">段落5</p>
            <p id="p6" class="blank"><br><br></p>
            <p id="p7" class="blank"><br></p>
            <p id="p8">段落8</p>
            """
        )
        self.assertEqual(
            ["段落1", "段落3", "<br />", "段落5", "<br />", "段落8"],
            parser.paragraphs,
        )


class TestKakuyomuIndexParser(TestCase):
    def test_kakuyomu_index_parser(self):
        parser = KakuyomuIndexParser()
        parser.feed(
            """
            <script id="__NEXT_DATA__" type="application/json">
                {
                    "query": {
                        "workId": "work1"
                    },
                    "props": {
                        "pageProps": {
                            "__APOLLO_STATE__": {
                                "Work:work1": {
                                    "title": "タイトル",
                                    "author": {
                                        "__ref": "UserAccount:user1"
                                    },
                                    "tableOfContentsV2": [
                                        {
                                            "__ref": "TableOfContentsChapter:"
                                        }
                                    ]
                                },
                                "UserAccount:user1": {
                                    "activityName": "作者"
                                },
                                "TableOfContentsChapter:": {
                                    "episodeUnions": [
                                        {
                                            "__ref": "Episode:10001"
                                        },
                                        {
                                            "__ref": "Episode:10002"
                                        }
                                    ],
                                    "chapter": null
                                },
                                "Episode:10001": {
                                    "id": "10001",
                                    "title": "エピソード1",
                                    "publishedAt": "2000-01-01T00:00:00Z"
                                },
                                "Episode:10002": {
                                    "id": "10002",
                                    "title": "エピソード2",
                                    "publishedAt": "2000-01-02T00:00:00Z"
                                }
                            }
                        }
                    }
                }
            </script>
            """
        )
        self.assertEqual("タイトル", parser.title)
        self.assertEqual("作者", parser.author)
        self.assertEqual(
            [
                {
                    "name": "default",
                    "episodes": [
                        {
                            "id": "10001",
                            "title": "",
                            "created_at": "2000-01-01T00:00:00Z",
                            "updated_at": "2000-01-01T00:00:00Z",
                            "paragraphs": [],
                            "fetched": False,
                        },
                        {
                            "id": "10002",
                            "title": "",
                            "created_at": "2000-01-02T00:00:00Z",
                            "updated_at": "2000-01-02T00:00:00Z",
                            "paragraphs": [],
                            "fetched": False,
                        },
                    ],
                },
            ],
            parser.chapters,
        )

    def test_kakuyomu_index_parser_multiple_chapters(self):
        parser = KakuyomuIndexParser()
        parser.feed(
            """
            <script id="__NEXT_DATA__" type="application/json">
                {
                    "query": {
                        "workId": "work1"
                    },
                    "props": {
                        "pageProps": {
                            "__APOLLO_STATE__": {
                                "Work:work1": {
                                    "title": "タイトル",
                                    "author": {
                                        "__ref": "UserAccount:user1"
                                    },
                                    "tableOfContentsV2": [
                                        {
                                            "__ref": "TableOfContentsChapter:chapter1"
                                        },
                                        {
                                            "__ref": "TableOfContentsChapter:chapter2"
                                        }
                                    ]
                                },
                                "UserAccount:user1": {
                                    "activityName": "作者"
                                },
                                "TableOfContentsChapter:chapter1": {
                                    "episodeUnions": [
                                        {
                                            "__ref": "Episode:10001"
                                        },
                                        {
                                            "__ref": "Episode:10002"
                                        }
                                    ],
                                    "chapter": {
                                        "__ref": "Chapter:chapter1"
                                    }
                                },
                                "TableOfContentsChapter:chapter2": {
                                    "episodeUnions": [
                                        {
                                            "__ref": "Episode:10003"
                                        }
                                    ],
                                    "chapter": {
                                        "__ref": "Chapter:chapter2"
                                    }
                                },
                                "Chapter:chapter1": {
                                    "title": "第1章"
                                },
                                "Chapter:chapter2": {
                                    "title": "第2章"
                                },
                                "Episode:10001": {
                                    "id": "10001",
                                    "title": "エピソード1",
                                    "publishedAt": "2000-01-01T00:00:00Z"
                                },
                                "Episode:10002": {
                                    "id": "10002",
                                    "title": "エピソード2",
                                    "publishedAt": "2000-01-02T00:00:00Z"
                                },
                                "Episode:10003": {
                                    "id": "10003",
                                    "title": "エピソード3",
                                    "publishedAt": "2000-01-03T00:00:00Z"
                                }
                            }
                        }
                    }
                }
            </script>
            """
        )
        self.assertEqual("タイトル", parser.title)
        self.assertEqual("作者", parser.author)
        self.assertEqual(
            [
                {"name": "default", "episodes": []},
                {
                    "name": "第1章",
                    "episodes": [
                        {
                            "id": "10001",
                            "title": "",
                            "created_at": "2000-01-01T00:00:00Z",
                            "updated_at": "2000-01-01T00:00:00Z",
                            "paragraphs": [],
                            "fetched": False,
                        },
                        {
                            "id": "10002",
                            "title": "",
                            "created_at": "2000-01-02T00:00:00Z",
                            "updated_at": "2000-01-02T00:00:00Z",
                            "paragraphs": [],
                            "fetched": False,
                        },
                    ],
                },
                {
                    "name": "第2章",
                    "episodes": [
                        {
                            "id": "10003",
                            "title": "",
                            "created_at": "2000-01-03T00:00:00Z",
                            "updated_at": "2000-01-03T00:00:00Z",
                            "paragraphs": [],
                            "fetched": False,
                        },
                    ],
                },
            ],
            parser.chapters,
        )

    def test_kakuyomu_index_parser_invalid_episode_id(self):
        state = {
            "Work:1": {
                "title": "タイトル",
                "author": {"__ref": "UserAccount:1"},
                "tableOfContentsV2": [{"__ref": "TableOfContentsChapter:1"}],
            },
            "UserAccount:1": {"activityName": "作者"},
            "TableOfContentsChapter:1": {
                "chapter": None,
                "episodeUnions": [{"__ref": "Episode:x"}],
            },
            "Episode:x": {"id": "../1", "publishedAt": "2000-01-01T00:00:00Z"},
        }
        next_data = {
            "query": {"workId": "1"},
            "props": {"pageProps": {"__APOLLO_STATE__": state}},
        }
        parser = KakuyomuIndexParser()
        with self.assertRaisesRegex(Exception, "^episode_id が認識できませんでした"):
            parser.feed(f'<script id="__NEXT_DATA__">{json.dumps(next_data)}</script>')
