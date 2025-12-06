import re

RANGE_PATTERN = re.compile(r"[1-9][0-9]*(-[1-9][0-9]*)?(,[1-9][0-9]*(-[1-9][0-9]*)?)*")


def half_to_full(c: str):
    return {
        "A": "Ａ",
        "B": "Ｂ",
        "C": "Ｃ",
        "D": "Ｄ",
        "E": "Ｅ",
        "F": "Ｆ",
        "G": "Ｇ",
        "H": "Ｈ",
        "I": "Ｉ",
        "J": "Ｊ",
        "K": "Ｋ",
        "L": "Ｌ",
        "M": "Ｍ",
        "N": "Ｎ",
        "O": "Ｏ",
        "P": "Ｐ",
        "Q": "Ｑ",
        "R": "Ｒ",
        "S": "Ｓ",
        "T": "Ｔ",
        "U": "Ｕ",
        "V": "Ｖ",
        "W": "Ｗ",
        "X": "Ｘ",
        "Y": "Ｙ",
        "Z": "Ｚ",
        "a": "ａ",
        "b": "ｂ",
        "c": "ｃ",
        "d": "ｄ",
        "e": "ｅ",
        "f": "ｆ",
        "g": "ｇ",
        "h": "ｈ",
        "i": "ｉ",
        "j": "ｊ",
        "k": "ｋ",
        "l": "ｌ",
        "m": "ｍ",
        "n": "ｎ",
        "o": "ｏ",
        "p": "ｐ",
        "q": "ｑ",
        "r": "ｒ",
        "s": "ｓ",
        "t": "ｔ",
        "u": "ｕ",
        "v": "ｖ",
        "w": "ｗ",
        "x": "ｘ",
        "y": "ｙ",
        "z": "ｚ",
        "0": "０",
        "1": "１",
        "2": "２",
        "3": "３",
        "4": "４",
        "5": "５",
        "6": "６",
        "7": "７",
        "8": "８",
        "9": "９",
        ".": "．",
        ",": "，",
        "!": "！",
        "?": "？",
        "%": "％",
    }[c]


TCY_2_DIGITS_PATTERN = re.compile(r"(?<![\x00-\x7F])[0-9]{2}(?![\x00-\x7F])")
TCY_HALF_CHAR_PATTERN = re.compile(r"(?<![\x00-\x7F])[a-zA-Z0-9.,!?%]+(?![\x00-\x7F])")


def tcy(text: str):
    text = TCY_2_DIGITS_PATTERN.sub(r'<span class="tcy">\g<0></span>', text)
    text = TCY_HALF_CHAR_PATTERN.sub(
        lambda m: "".join(half_to_full(c) for c in m.group(0)), text
    )
    # ダブルクオートを爪括弧に変換
    text = text.replace("“", "〝").replace("”", "〟")
    # 連続する感嘆符・疑問符
    text = (
        text.replace("！？", '<span class="tcy">⁉</span>')
        .replace("？！", '<span class="tcy">⁈</span>')
        .replace("！！", '<span class="tcy">‼</span>')
        .replace("？？", '<span class="tcy">⁇</span>')
    )
    return text


def range_to_episode_nums(my_range: str):
    my_range = my_range.replace(" ", "")
    if not RANGE_PATTERN.fullmatch(my_range):
        raise Exception(f"range が想定しない形式です: {my_range}")
    episode_nums: set[str] = set([])
    for r in my_range.split(","):
        if "-" in r:
            start, end = r.split("-")
            if int(end) > 10_000:
                # 安全のため値が大きすぎる場合はエラーにする
                raise Exception(f"range に含まれる値が大きすぎます: {end}")
            for i in range(int(start), int(end) + 1):
                episode_nums.add(str(i))
        else:
            episode_nums.add(r)
    return episode_nums
