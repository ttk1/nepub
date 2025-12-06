from typing import Dict, List, TypedDict


class Episode(TypedDict):
    id: str
    title: str
    created_at: str
    updated_at: str
    paragraphs: List[str]
    fetched: bool


class Chapter(TypedDict):
    name: str
    episodes: List[Episode]


class Image(TypedDict):
    id: str
    name: str
    type: str
    data: bytes


class MetadataImage(TypedDict):
    id: str
    name: str
    type: str


class MetadataEpisode(TypedDict):
    id: str
    title: str
    created_at: str
    updated_at: str
    images: List[MetadataImage]


class Metadata(TypedDict):
    novel_id: str
    kakuyomu: bool
    illustration: bool
    tcy: bool
    episodes: Dict[str, MetadataEpisode]
