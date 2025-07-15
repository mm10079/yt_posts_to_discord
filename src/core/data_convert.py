import re
from datetime import datetime
from typing import Any, TypeVar, Union, Sequence, Mapping

from src.app_types import database, post_parse
from src.app_types.database import Status

CHANNEL_URL = "https://www.youtube.com/channel/{channel_id}"
POST_URL = "https://www.youtube.com/post/{post_id}"
VIDEO_URL = "https://www.youtube.com/watch?v={video_id}"

OriginImageEndPoint = '=s0?imgmax=0'
T = TypeVar("T")

def get_today() -> str:
    """獲取當前日期，格式為 YYYYMMDD"""
    return datetime.now().strftime('%Y%m%d')

def deep_get(
    data: Union[Mapping[str, Any], Sequence[Any]],
    keys: Sequence[Union[str, int]],
    default: T = None,
) -> Union[Any, T]:
    """從嵌套的字典或列表中獲取值。
    支持多層級的鍵或索引，並提供默認值。
    :param data: 要查找的數據，可以是字典或列表。
    :param keys: 鍵或索引的序列，表示要查找的路徑。
    :param default: 如果未找到值，返回的默認值。
    :return: 找到的值或默認值。
    """
    for key in keys:
        if isinstance(data, dict) and isinstance(key, str):
            data = data.get(key, default)
        elif isinstance(data, list) and isinstance(key, int):
            if 0 <= key < len(data) or -len(data) <= key < 0:
                data = data[key]
            else:
                return default
        else:
            return default
    return data if data is not None else default

def get_origin_image_url(url: str) -> str:
    # 確保URL以http或https開頭
    if not url:
        return ''
    if not url.startswith(('http:', 'https:')):
        url = 'https:' + url
    url = url[:url.rfind('=s')] + OriginImageEndPoint
    return url

class post_parser:
    def __init__(self, content: dict):
        self.content = content

        self.channel_url = CHANNEL_URL.format(channel_id=deep_get(self.content, ['channel_id'], ''))
        self.post_url = POST_URL.format(post_id=deep_get(self.content, ['post_id'], ''))
        self.post_init()
        self.content_text = self.get_content_text()
        self.video = self.get_video()

    def post_init(self):
        """獲取縮略圖連結"""
        self.author_name = deep_get(self.content, ['author', 'authorText', 'runs', 0, 'text'], '')
        self.author_thumbnail = deep_get(self.content, ['author', 'authorThumbnail', 'thumbnails', -1, 'url'], '')
        if self.author_thumbnail:
            self.author_thumbnail = get_origin_image_url(self.author_thumbnail)
        self.is_membership = True if deep_get(self.content, ['sponsor_only_badge', 'sponsorsOnlyBadgeRenderer', 'label', 'simpleText'], "") else False

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

    def attachments(self) -> list:
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

    def get_video(self) -> post_parse.Video | None:
        """獲取影片連結"""
        video_content = deep_get(self.content, ['backstage_attachment', 'videoRenderer'], {})
        if video_content:
            video_id = video_content.get("videoId", '')
            if video_id:
                description = ''
                for item in deep_get(video_content, ['descriptionSnippet', 'runs'], []):
                    description += item['text']
                return post_parse.Video(
                    url=VIDEO_URL.format(video_id=video_id),
                    title=deep_get(video_content, ['title', 'runs', 0,'text'], "").replace('\n', ''),
                    description=description,
                    thumbnail=get_origin_image_url(deep_get(video_content, ['thumbnail', 'thumbnails', -1, 'url'], '')),
                    membership=True if deep_get(video_content, ['badges', -1, 'metadataBadgeRenderer', 'label'], '') else False,
                    length=deep_get(video_content, ['lengthText', 'simpleText'], ''),
                    uploader=deep_get(video_content, ['ownerText', 'runs', 0, 'text'], ''),
                    uploader_id=deep_get(video_content, ['ownerText', 'runs', 0, 'navigationEndpoint', 'browseEndpoint', 'browseId'], ''),
                    uploader_thumbnail=get_origin_image_url(deep_get(video_content, ['avatar', 'decoratedAvatarViewModel', 'avatar', 'avatarViewModel', 'image', 'sources', -1, 'url'], '')),
                )
        return None

    def links(self) -> list:
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

def remove_same_videos(links: set[str]):
    yt_video_keys = set()
    for link in list(links):
        if 'youtu.be' in link:
            key = link.split('youtu.be/')[1]
        elif 'youtube.com/watch' in link:
            key = link.split('v=')[1]
        else:
            continue
        if key in yt_video_keys:
            links.remove(link)
        else:
            yt_video_keys.add(key)

def get_all_post_links(content: dict) -> list[str]:
    links = set()
    parser = post_parser(content)
    links.update(parser.links())
    links.update(parser.attachments())
    if parser.video:
        links.add(parser.video.url)
    remove_same_videos(links)
    return list(links)

def convert_post_to_type(post_data: dict) -> database.Data_Post:
    post = database.Data_Post(
        pid=post_data.get('post_id', ''),
        time=get_today(),
        content=post_data,
        links=get_all_post_links(post_data),
        membership=Status.FINISH if deep_get(post_data, ['sponsor_only_badge', 'sponsorsOnlyBadgeRenderer', 'label', 'simpleText'], "") else Status.NOT_PROCESS,
    )
    return post