import re

RANGE_PATTERN = re.compile(r"[1-9][0-9]*(-[1-9][0-9]*)?(,[1-9][0-9]*(-[1-9][0-9]*)?)*")
# 安全のため range に指定できるエピソード番号の上限を設ける
MAX_EPISODE_NUM = 10_000

TCY_2_DIGITS_PATTERN = re.compile(r"(?<![\x00-\x7F])[0-9]{2}(?![\x00-\x7F])")
TCY_HALF_CHAR_PATTERN = re.compile(r"(?<![\x00-\x7F])[a-zA-Z0-9.,!?%]+(?![\x00-\x7F])")


def half_to_full(text: str) -> str:
    # 対象の半角文字 (英数字と .,!?%) は全て対応する全角文字と
    # コードポイントが 0xFEE0 ずれているだけなのでそれを利用する
    return "".join(chr(ord(c) + 0xFEE0) for c in text)


def tcy(text: str) -> str:
    # 全角文字に挟まれた 2 桁の数字を縦中横にする
    text = TCY_2_DIGITS_PATTERN.sub(r'<span class="tcy">\g<0></span>', text)
    # 全角文字に挟まれた残りの半角英数字記号は全角に変換する
    text = TCY_HALF_CHAR_PATTERN.sub(lambda m: half_to_full(m.group(0)), text)
    # ダブルクオートを爪括弧に変換
    text = text.replace("“", "〝").replace("”", "〟")
    # 連続する感嘆符・疑問符は合字にして縦中横にする
    text = (
        text.replace("！？", '<span class="tcy">⁉</span>')
        .replace("？！", '<span class="tcy">⁈</span>')
        .replace("！！", '<span class="tcy">‼</span>')
        .replace("？？", '<span class="tcy">⁇</span>')
    )
    return text


def range_to_episode_nums(range_str: str) -> set[int]:
    range_str = range_str.replace(" ", "")
    if not RANGE_PATTERN.fullmatch(range_str):
        raise ValueError(f"range が想定しない形式です: {range_str}")
    episode_nums: set[int] = set()
    for part in range_str.split(","):
        if "-" in part:
            start, end = map(int, part.split("-"))
            if end > MAX_EPISODE_NUM:
                raise ValueError(f"range に含まれる値が大きすぎます: {end}")
            episode_nums.update(range(start, end + 1))
        else:
            episode_nums.add(int(part))
    return episode_nums
