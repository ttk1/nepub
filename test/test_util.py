from unittest import TestCase

from nepub.util import range_to_episode_nums


class TestUtil(TestCase):
    def test_range_to_episode_nums(self):
        self.assertEqual(set(["1", "2", "3"]), range_to_episode_nums("1,2,3"))
        self.assertEqual(set(["1", "2", "3"]), range_to_episode_nums("1, 2, 3"))
        self.assertEqual(set(["1", "2", "3"]), range_to_episode_nums("1-3"))
        self.assertEqual(set(["1", "5", "6", "7"]), range_to_episode_nums("1, 5 - 7"))
        with self.assertRaisesRegex(Exception, "^range が想定しない形式です"):
            range_to_episode_nums("1,,2")
        with self.assertRaisesRegex(Exception, "^range が想定しない形式です"):
            range_to_episode_nums("1-")
        with self.assertRaisesRegex(Exception, "^range に含まれる値が大きすぎます"):
            range_to_episode_nums("1-99999")
