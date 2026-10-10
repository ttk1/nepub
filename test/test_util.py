from unittest import TestCase

from nepub.util import range_to_episode_nums, tcy


class TestUtil(TestCase):
    def test_range_to_episode_nums(self):
        self.assertEqual(set(["1", "2", "3"]), range_to_episode_nums("1,2,3"))
        self.assertEqual(set(["1", "2", "3"]), range_to_episode_nums("1, 2, 3"))
        self.assertEqual(set(["1", "2", "3"]), range_to_episode_nums("1-3"))
        self.assertEqual(set(["1", "5", "6", "7"]), range_to_episode_nums("1, 5 - 7"))
        with self.assertRaisesRegex(ValueError, "^invalid range: 1,,2"):
            range_to_episode_nums("1,,2")
        with self.assertRaisesRegex(ValueError, "^invalid range: 1-"):
            range_to_episode_nums("1-")
        with self.assertRaisesRegex(ValueError, "^invalid range: 3-1 "):
            range_to_episode_nums("1,3-1")
        with self.assertRaisesRegex(ValueError, "^range value is too large: 99999"):
            range_to_episode_nums("1-99999")

    def test_tcy_digits_before_space(self):
        cases = [
            # 行頭 / 全角文字 / 全角文字 + 半角スペース の後で、半角スペース + 全角文字が続く数字
            ("1 サブタイトル", "１ サブタイトル"),
            ("12 サブタイトル", '<span class="tcy">12</span> サブタイトル'),
            ("123 サブタイトル", "１２３ サブタイトル"),
            ("第1 話", "第１ 話"),
            ("第 1 話", "第 １ 話"),
            ("第 12 話", '第 <span class="tcy">12</span> 話'),
            # 半角スペースが複数でもよい
            ("123  サブタイトル", "１２３  サブタイトル"),
            ("第  12  話", '第  <span class="tcy">12</span>  話'),
            # 英文中の数字は変換しない
            ("Chapter 1 開始", "Chapter 1 開始"),
            ("Chapter  1  開始", "Chapter  1  開始"),
            ("a1 開始", "a1 開始"),
            # 後ろが「半角スペース + 全角文字」でなければ対象外
            ("1 abc", "1 abc"),
            ("1 ", "1 "),
            # 既存のルール (前後が全角文字 / 文字列の端) はそのまま
            ("第1話", "第１話"),
            ("第12話", '第<span class="tcy">12</span>話'),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(expected, tcy(text))
