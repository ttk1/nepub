import argparse

from nepub.convert import convert_to_epub


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("novel_id", help="novel id", type=str)
    parser.add_argument(
        "-i",
        "--illustration",
        help="Include illustrations (Narou only)",
        action="store_true",
    )
    parser.add_argument(
        "--no-tcy", help="Disable Tate-Chu-Yoko conversion", action="store_true"
    )
    parser.add_argument(
        "-r",
        "--range",
        metavar="<range>",
        help='Specify the target episode number range using comma-separated values (e.g., "1,2,3") or a range notation (e.g., "10-20").',
        type=str,
    )
    parser.add_argument(
        "-o",
        "--output",
        metavar="<file>",
        help="Output file name. If not specified, ${novel_id}.epub is used. Update the file if it exists.",
        type=str,
    )
    parser.add_argument(
        "-k", "--kakuyomu", help="Use Kakuyomu as the source", action="store_true"
    )
    args = parser.parse_args()
    if args.output:
        output = args.output
    else:
        output = f"{args.novel_id}.epub"
    convert_to_epub(
        args.novel_id,
        illustration=args.illustration,
        tcy=not args.no_tcy,
        my_range=args.range,
        output=output,
        kakuyomu=args.kakuyomu,
    )


if __name__ == "__main__":
    main()
