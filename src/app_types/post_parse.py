from typing import List
from dataclasses import dataclass, field

from src.core import data_convert

@dataclass
class Video:
    url: str = ''
    title: str = ''
    description: str = ''
    thumbnail: str = ''
    membership: bool = False
    length: str = ''
    uploader: str = ''
    uploader_id: str = ''
    uploader_thumbnail: str = ''

@dataclass
class PostParser:
    """輸入貼文json內容,解析出貼文相關資訊"""
    content: dict

    today: str = ''
    channel_url: str = ''
    post_url: str = ''
    author_name: str = ''
    author_thumbnail: str = ''
    content_text: str = ''
    video: Video|None = field(default=None)
    attachments: List[str] = field(default_factory=list)
    content_links: List[str] = field(default_factory=list)
    is_membership: bool = False

    def __post_init__(self):
        parser = data_convert.post_parser(self.content)
        self.today = data_convert.get_today()
        self.channel_url = parser.channel_url
        self.post_url = parser.post_url
        self.author_name = parser.author_name
        self.author_thumbnail = parser.author_thumbnail
        self.content_text = parser.content_text
        self.video = parser.video
        self.attachments = parser.attachments()
        self.content_links = parser.links()
        self.is_membership = parser.is_membership