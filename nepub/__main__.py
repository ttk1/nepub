import argparse

from nepub.convert import ConvertError, convert_to_epub

DESCRIPTION = (
    "Convert a novel on Shosetsuka ni Narou or Kakuyomu into a vertically written EPUB."
)

EPILOG = """\
examples:
  nepub n0000aa                 download all episodes into n0000aa.epub
  nepub n0000aa -r 1-10         download only episodes 1 to 10
  nepub -k 1000                 download a novel from Kakuyomu

If the output file already exists, only new and updated episodes are downloaded.
"""


def main():
    parser = argparse.ArgumentParser(
        prog="nepub",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "novel_id",
        help="novel ID: the ncode in the Narou URL (https://ncode.syosetu.com/<novel_id>/) "
        "or the work ID in the Kakuyomu URL (https://kakuyomu.jp/works/<novel_id>)",
    )
    parser.add_argument(
        "-k", "--kakuyomu", action="store_true", help="download from Kakuyomu"
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="output file (default: <novel_id>.epub); "
        "if it exists, it is updated with new and updated episodes",
    )
    parser.add_argument(
        "-r",
        "--range",
        metavar="RANGE",
        help='episode numbers to download, e.g. "1,2,3", "10-20" or "1,5-7" '
        "(default: all episodes)",
    )
    parser.add_argument(
        "-i",
        "--illustration",
        action="store_true",
        help="include illustrations (Narou only)",
    )
    parser.add_argument(
        "--no-tcy",
        action="store_true",
        help="disable tate-chu-yoko (upright numbers in vertical text)",
    )
    args = parser.parse_args()

    try:
        convert_to_epub(
            args.novel_id,
            illustration=args.illustration,
            tcy=not args.no_tcy,
            my_range=args.range,
            output=args.output or f"{args.novel_id}.epub",
            kakuyomu=args.kakuyomu,
        )
    except ConvertError as e:
        parser.exit(1, f"{parser.prog}: error: {e}\n")


if __name__ == "__main__":
    main()
