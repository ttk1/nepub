from unittest import TestCase

from nepub.util import half_to_full, range_to_episode_nums, tcy


class TestUtil(TestCase):
    def test_half_to_full(self):
        self.assertEqual("ＡＢＣｘｙｚ０１９．，！？％", half_to_full("ABCxyz019.,!?%"))

    def test_tcy(self):
        self.assertEqual(
            '今日は６月<span class="tcy">28</span>日です<span class="tcy">⁉</span>',
            tcy("今日は6月28日です!?"),
        )
        # 半角英数字が全角文字に挟まれていない場合は変換しない
        self.assertEqual("This is a pen.", tcy("This is a pen."))
        self.assertEqual("〝引用〟", tcy("“引用”"))

    def test_range_to_episode_nums(self):
        self.assertEqual({1, 2, 3}, range_to_episode_nums("1,2,3"))
        self.assertEqual({1, 2, 3}, range_to_episode_nums("1, 2, 3"))
        self.assertEqual({1, 2, 3}, range_to_episode_nums("1-3"))
        self.assertEqual({1, 5, 6, 7}, range_to_episode_nums("1, 5 - 7"))
        with self.assertRaisesRegex(ValueError, "^range が想定しない形式です"):
            range_to_episode_nums("1,,2")
        with self.assertRaisesRegex(ValueError, "^range が想定しない形式です"):
            range_to_episode_nums("1-")
        with self.assertRaisesRegex(ValueError, "^range に含まれる値が大きすぎます"):
            range_to_episode_nums("1-99999")
