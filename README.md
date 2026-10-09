# nepub

「小説家になろう」および「カクヨム」の小説を縦書きの EPUB に変換するためのツール

## Requirements

* Python 3
  * 3.11 以降に対応しています

## Installation

```sh
uv tool install git+https://github.com/ttk1/nepub.git
# または
pip install git+https://github.com/ttk1/nepub.git
```

## Usage

```sh
$ nepub -h
usage: nepub [-h] [-k] [-o FILE] [-r RANGE] [-i] [--no-tcy] novel_id

Convert a novel on Shosetsuka ni Narou or Kakuyomu into a vertically written EPUB.

positional arguments:
  novel_id              novel ID: the ncode in the Narou URL
                        (https://ncode.syosetu.com/<novel_id>/) or the work ID
                        in the Kakuyomu URL
                        (https://kakuyomu.jp/works/<novel_id>)

options:
  -h, --help            show this help message and exit
  -k, --kakuyomu        download from Kakuyomu
  -o FILE, --output FILE
                        output file (default: <novel_id>.epub); if it exists,
                        it is updated with new and updated episodes
  -r RANGE, --range RANGE
                        episode numbers to download, e.g. "1,2,3", "10-20" or
                        "1,5-7" (default: all episodes)
  -i, --illustration    include illustrations (Narou only)
  --no-tcy              disable tate-chu-yoko (upright numbers in vertical
                        text)

examples:
  nepub n0000aa                 download all episodes into n0000aa.epub
  nepub n0000aa -r 1-10         download only episodes 1 to 10
  nepub -k 1000                 download a novel from Kakuyomu

If the output file already exists, only new and updated episodes are downloaded.
```

Example:

```sh
$ nepub xxxx
Novel: xxxx (Narou)
Output: xxxx.epub (updating the existing file)
Options: illustrations: off, tcy: on
Title: タイトル
Author: 作者
Found 3 episodes.
[1/3] Skipped (up to date): https://ncode.syosetu.com/xxxx/1/
[2/3] Skipped (up to date): https://ncode.syosetu.com/xxxx/2/
[3/3] Downloading: https://ncode.syosetu.com/xxxx/3/
Done: 1 downloaded, 2 skipped (up to date).
Updated xxxx.epub.
```

※ xxxx の部分には小説ページの URL の末尾部分 (`https://ncode.syosetu.com/{ここの文字列}/`) に置き換えてください。

## Development

[uv](https://docs.astral.sh/uv/) (0.9.17 以降) を使用します。

```sh
uv sync --locked                       # uv.lock どおりに環境を構築 (ハッシュ検証あり)
uv run nepub xxxx                      # 実行
uv run python -m unittest discover -s test
uv run mypy nepub test
uv run ruff check --fix                # lint
uv run ruff format                     # フォーマット
```

## 免責事項

本ツールは、小説投稿サイト「小説家になろう」および「カクヨム」の小説を縦書きの EPUB に変換するための非公式ツールです。
本ツールは株式会社ヒナプロジェクトおよび株式会社 KADOKAWA とは一切関係がありません。

「小説家になろう」は、株式会社ヒナプロジェクトの登録商標です。
「カクヨム」は、株式会社 KADOKAWA の登録商標です。

### 注意事項

* 自分用に作成したため、最低限読める EPUB を出力する機能しかありません
* 「小説家になろう」および「カクヨム」のサーバーに負荷をかけないよう、ご注意ください
* 本ツールの使用によって生じたいかなる結果についても責任を負いません。ご使用は自己責任でお願いいたします。
