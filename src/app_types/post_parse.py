import os
import re

from datetime import datetime
from dataclasses import dataclass, field
from typing import List

from src.utils.tools import deep_get, get_origin_image_url, get_size
from src.app_types.database import Status

CHANNEL_URL = "https://www.youtube.com/channel/{channel_id}"
POST_URL = "https://www.youtube.com/post/{post_id}"
VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"

class today(object):
    year = datetime.now().strftime('%Y')
    month = datetime.now().strftime('%m')
    day = datetime.now().strftime('%d')
    hour = datetime.now().strftime('%H')
    minute = datetime.now().strftime('%M')
    second = datetime.now().strftime('%S')

@dataclass
class FileInfo:
    path: str
    url: str
    name: str = ''
    size: int = 0

    def __post_init__(self):
        if os.path.exists(self.path) and self.name:
            self.size = get_size(self.path)

@dataclass
class Video:
    url: str = ''
    title: str = ''
    description: str = ''
    thumbnail: str = ''
    membership: int = Status.NOT_PROCESS
    length: str = ''
    uploader_name: str = ''
    uploader_channel: str = ''
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
        parser = _parser(self.content)
        self.today = today.year + today.month + today.day
        self.channel_url = CHANNEL_URL.format(channel_id=deep_get(self.content, ['channel_id'], ''))
        self.post_url = POST_URL.format(post_id=deep_get(self.content, ['post_id'], ''))
        self.author_name = deep_get(self.content, ['author', 'authorText', 'runs', 0, 'text'], '')
        self.author_thumbnail = get_origin_image_url(deep_get(self.content, ['author', 'authorThumbnail', 'thumbnails', -1, 'url'], ''))
        self.content_text = parser.get_content_text()
        self.video = parser.get_video()
        self.attachments = parser.get_attachments()
        self.content_links = parser.get_links()
        self.is_membership = True if deep_get(self.content, ['sponsor_only_badge', 'sponsorsOnlyBadgeRenderer', 'label', 'simpleText'], "") else False


class _parser:
    def __init__(self, content: dict) -> None:
        self.content = content

    def get_content_text(self) -> str:
        """獲取文章內容"""
        text = ""
        for item in deep_get(self.content, ['content_text', 'runs'], []):
            if 'text' in item:
                if 'urlEndpoint' in item: # 貼文包含連結文字
                    text += item['urlEndpoint']['url']
                elif 'browseEndpoint' in item: # 貼文包含YT內部連結
                    if 'http' not in item['browseEndpoint']['url']:
                        url = 'https://www.youtube.com/' + item['browseEndpoint']['url']
                    else:
                        url = item['browseEndpoint']['url']
                    text += f"[{item['text']}]({url})"
                else:
                    text += item['text']
            
        return text

    def get_attachments(self) -> list:
        """獲取附件圖片連結"""
        images = []
        # 附件圖片
        link = deep_get(self.content, ['backstage_attachment', 'backstageImageRenderer', 'image', 'thumbnails', -1, 'url'], "")
        images.append(get_origin_image_url(link))

        # 多圖附件
        links = deep_get(self.content, ['backstage_attachment', 'postMultiImageRenderer', 'images'], [])
        for image in links:
            links = deep_get(image, ['backstageImageRenderer', 'image', 'thumbnails'], [])
            for link in links:
                if 'url' in link:
                    images.append(get_origin_image_url(link['url']))
        return images


    def get_video(self) -> Video | None:
        """獲取影片連結"""
        video_content = deep_get(self.content, ['backstage_attachment', 'videoRenderer'], {})
        if video_content:
            video_id = video_content.get("videoId", '')
            if video_id:
                description = ''
                for item in deep_get(video_content, ['descriptionSnippet', 'runs'], []):
                    description += item['text']
                return Video(
                    url=VIDEO_URL.format(video_id=video_id),
                    title=deep_get(video_content, ['title', 'runs', 0,'text'], "").replace('\n', ''),
                    description=description,
                    thumbnail=get_origin_image_url(deep_get(video_content, ['thumbnail', 'thumbnails', -1, 'url'], '')),
                    membership=Status.FINISH.value if deep_get(video_content, ['badges', -1, 'metadataBadgeRenderer', 'label'], '') else Status.NOT_PROCESS.value,
                    length=deep_get(video_content, ['lengthText', 'simpleText'], ''),
                    uploader_name=deep_get(video_content, ['ownerText', 'runs', 0, 'text'], ''),
                    uploader_channel=CHANNEL_URL.format(channel_id=deep_get(video_content, ['ownerText', 'runs', 0, 'navigationEndpoint', 'browseEndpoint', 'browseId'], '')),
                    uploader_thumbnail=get_origin_image_url(deep_get(video_content, ['avatar', 'decoratedAvatarViewModel', 'avatar', 'avatarViewModel', 'image', 'sources', -1, 'url'], '')),
                )
        return None

    def get_links(self) -> list:
        """獲取所有連結"""
        content_text = deep_get(self.content, ['content_text', 'runs'], [])
        links = []
        for item in content_text:
            if 'urlEndpoint' in item:
                links.append(item['urlEndpoint']['url'])
            else:
                if 'loggingDirectives' in item:
                    # 處理可能的 loggingDirectives
                    url = item.get('text', '')
                    if url and re.match(r'https?://', url):
                        links.append(url)
        return links
