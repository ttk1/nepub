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
                                    "tableOfContents": [
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
                                            "__ref": "Episode:epsode1"
                                        },
                                        {
                                            "__ref": "Episode:epsode2"
                                        }
                                    ],
                                    "chapter": null
                                },
                                "Episode:epsode1": {
                                    "id": "epsode1",
                                    "title": "エピソード1",
                                    "publishedAt": "2000-01-01T00:00:00Z"
                                },
                                "Episode:epsode2": {
                                    "id": "epsode2",
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
                            "id": "epsode1",
                            "title": "",
                            "created_at": "2000-01-01T00:00:00Z",
                            "updated_at": "2000-01-01T00:00:00Z",
                            "paragraphs": [],
                            "fetched": False,
                        },
                        {
                            "id": "epsode2",
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
                                    "tableOfContents": [
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
                                            "__ref": "Episode:epsode1"
                                        },
                                        {
                                            "__ref": "Episode:epsode2"
                                        }
                                    ],
                                    "chapter": {
                                        "__ref": "Chapter:chapter1"
                                    }
                                },
                                "TableOfContentsChapter:chapter2": {
                                    "episodeUnions": [
                                        {
                                            "__ref": "Episode:epsode3"
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
                                "Episode:epsode1": {
                                    "id": "epsode1",
                                    "title": "エピソード1",
                                    "publishedAt": "2000-01-01T00:00:00Z"
                                },
                                "Episode:epsode2": {
                                    "id": "epsode2",
                                    "title": "エピソード2",
                                    "publishedAt": "2000-01-02T00:00:00Z"
                                },
                                "Episode:epsode3": {
                                    "id": "epsode3",
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
                            "id": "epsode1",
                            "title": "",
                            "created_at": "2000-01-01T00:00:00Z",
                            "updated_at": "2000-01-01T00:00:00Z",
                            "paragraphs": [],
                            "fetched": False,
                        },
                        {
                            "id": "epsode2",
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
                            "id": "epsode3",
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
