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
# 「1 サブタイトル」「第 1 話」のように半角スペース (1 つ以上) を挟んで全角文字が続く数字
# 前は 行頭 / 全角文字 / 全角文字 + 半角スペース のいずれか (group 1 に入る)
# (「Chapter 1 開始」のような英文中の数字は対象にしない)
TCY_DIGITS_BEFORE_SPACE_PATTERN = re.compile(
    r"(^|[^\x00-\x7F] *)([0-9]+)(?= +[^\x00-\x7F])"
)


def digits_to_tcy(digits: str):
    """2 桁の数字は縦中横、それ以外の桁数は全角にする"""
    if len(digits) == 2:
        return f'<span class="tcy">{digits}</span>'
    return "".join(half_to_full(c) for c in digits)


def tcy(text: str):
    # 半角スペースはそのまま残し、数字だけを変換する
    text = TCY_DIGITS_BEFORE_SPACE_PATTERN.sub(
        lambda m: m.group(1) + digits_to_tcy(m.group(2)), text
    )
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
        raise ValueError(f'invalid range: {my_range} (e.g. "1,2,3", "10-20")')
    episode_nums: set[str] = set([])
    for r in my_range.split(","):
        if "-" in r:
            start, end = r.split("-")
            start_num, end_num = int(start), int(end)
            if start_num > 10_000:
                # 安全のため値が大きすぎる場合はエラーにする
                raise ValueError(f"range value is too large: {start} (max: 10000)")
            if end_num > 10_000:
                raise ValueError(f"range value is too large: {end} (max: 10000)")
            if start_num > end_num:
                raise ValueError(
                    f"invalid range: {r} (start must be less than or equal to end)"
                )
            for i in range(start_num, end_num + 1):
                episode_nums.add(str(i))
        else:
            if int(r) > 10_000:
                raise ValueError(f"range value is too large: {r} (max: 10000)")
            episode_nums.add(r)
    return episode_nums
