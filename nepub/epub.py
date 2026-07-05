from importlib import resources

from jinja2 import Environment, PackageLoader

from nepub.type import Chapter, Episode, MetadataImage

env = Environment(
    loader=PackageLoader("nepub"),
    # データ取得の際にエスケープ加工するのでここではエスケープしない
    autoescape=False,
)
template_content = env.get_template("content.opf")
template_navigation = env.get_template("navigation.xhtml")
template_text = env.get_template("text.xhtml")


def content(
    title: str,
    author: str,
    timestamp: str,
    episodes: list[Episode],
    images: list[MetadataImage],
) -> str:
    return template_content.render(
        title=title,
        author=author,
        timestamp=timestamp,
        episodes=episodes,
        images=images,
    )


def nav(chapters: list[Chapter]) -> str:
    return template_navigation.render(chapters=chapters)


def text(title: str, paragraphs: list[str]) -> str:
    return template_text.render(title=title, paragraphs=paragraphs)


def container() -> str:
    return _read_file("container.xml")


def style() -> str:
    return _read_file("style.css")


def _read_file(name: str) -> str:
    return resources.files("nepub").joinpath("files").joinpath(name).read_text("utf-8")
