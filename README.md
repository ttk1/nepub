# nepub

「小説家になろう」および「カクヨム」の小説を縦書きの EPUB に変換するためのツール

## Requirements

* Python 3
  * 3.10 で動作確認しています

## Installation

```sh
pip install git+https://github.com/ttk1/nepub.git
```

## Usage

```sh
$ nepub -h
usage: nepub [-h] [-i] [-t] [-r <range>] [-o <file>] [-k] novel_id

positional arguments:
  novel_id              novel id

options:
  -h, --help            show this help message and exit
  -i, --illustration    Include illustrations (Narou only)
  -t, --tcy             Enable Tate-Chu-Yoko conversion
  -r <range>, --range <range>
                        Specify the target episode number range using
                        comma-separated values (e.g., "1,2,3") or a range notation (e.g., "10-20").
  -o <file>, --output <file>
                        Output file name. If not specified, ${novel_id}.epub is used.
                        Update the file if it exists.
  -k, --kakuyomu        Use Kakuyomu as the source
```

Example:

```sh
$ nepub xxxx
novel_id: xxxx, illustration: False, tcy: False, output: xxxx.epub, kakuyomu: False
xxxx.epub found. Loading metadata for update.
3 episodes found.
Start downloading...
Download skipped (already up to date) (1/3): https://ncode.syosetu.com/xxxx/1/
Download skipped (already up to date) (2/3): https://ncode.syosetu.com/xxxx/2/
Downloading (3/3): https://ncode.syosetu.com/xxxx/3/
Download is complete! (new: 1, skipped: 2)
Updated xxxx.epub.
```

※ xxxx の部分には小説ページの URL の末尾部分 (`https://ncode.syosetu.com/{ここの文字列}/`) に置き換えてください。

## 免責事項

本ツールは、小説投稿サイト「小説家になろう」および「カクヨム」の小説を縦書きの EPUB に変換するための非公式ツールです。
本ツールは株式会社ヒナプロジェクトおよび株式会社 KADOKAWA とは一切関係がありません。

「小説家になろう」は、株式会社ヒナプロジェクトの登録商標です。
「カクヨム」は、株式会社 KADOKAWA の登録商標です。

### 注意事項

* 自分用に作成したため、最低限読める EPUB を出力する機能しかありません
* 「小説家になろう」および「カクヨム」のサーバーに負荷をかけないよう、ご注意ください
* 本ツールの使用によって生じたいかなる結果についても責任を負いません。ご使用は自己責任でお願いいたします。
