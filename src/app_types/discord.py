import re
from dataclasses import dataclass, field, is_dataclass, asdict
from typing import Dict

DESCRIPTION_LIMIT = 3000 # API限制4096個字，安全起見改為3000
FILE_LIMIT = 10 * 1024 * 1024 # 10MB

@dataclass
class Author:
    """Embed欄位使用"""
    name: str|None = field(default=None) # 專欄作者名稱
    url: str|None = field(default=None) # 專欄作者連結
    icon_url: str|None = field(default=None) # 專欄作者左側小縮圖

    def __post_init__(self):
        if self.name:
            if len(self.name) > 256:
                raise Exception('標題超過 256 字符')
        if self.url:
            self.url = check_url(self.url)
        if self.icon_url:
            self.icon_url = check_url(self.icon_url)

@dataclass
class Field:
    """Embed欄位使用，最多存在25個"""
    name: str|None = field(default=None) # 欄位名稱
    value: str|None = field(default=None) # 欄位內容
    inline: bool = False # 是否在同一行

    def __post_init__(self):
        if self.name:
            if len(self.name) > 256:
                raise Exception('欄位名稱超過 256 字符')
        if self.value:
            if len(self.value) > 1024:
                raise Exception('欄位內容超過 1024 字符')

@dataclass
class EmbedUrl:
    url: str|None = field(default=None)

    def __post_init__(self):
        if self.url:
            self.url = check_url(self.url)

@dataclass
class Footer:
    text: str|None = field(default=None)
    icon_url: str|None = field(default=None)


    def __post_init__(self):
        if self.text:
            if len(self.text) > 2048:
                raise Exception('標題超過 2048 字符')
        if self.icon_url:
            self.icon_url = check_url(self.icon_url)

@dataclass
class Attachment:
    filename: str = ''
    title: str|None = field(default=None)
    description: str|None = field(default=None)
    url: str|None = field(default=None)



@dataclass
class Embed:
    """專欄"""
    author: Author|None = field(default=None)
    title: str|None = field(default=None) # 標題
    thumbnail: EmbedUrl|None = field(default=None) # 標題右側大縮圖
    description: str|None = field(default=None) # 描述內文
    url: str|None = field(default=None) # 標題連結
    color: str|int = "#000000" # 欄位側邊高亮顏色
    fields: list[Field]|None = field(default=None) # 欄位
    image: EmbedUrl|None = field(default=None) # 專欄圖片
    #video: EmbedUrl|None = field(default=None) # 專欄影片
    footer: Footer|None = field(default=None)
    timestamp: str|None = field(default=None)
    #attachments: list[Attachment]|None = field(default=None)

    def __post_init__(self):
        if self.title:
            if len(self.title) > 256:
                raise Exception('標題超過 256 字符')
        if self.description:
            if len(self.description) > DESCRIPTION_LIMIT:
                raise Exception(f'描述內文超過 {DESCRIPTION_LIMIT} 字符')
        if self.url:
            self.url = check_url(self.url)
        if self.color:
            if isinstance(self.color, str):
                if len(self.color) > 7 or not self.color.startswith('#'):
                    raise Exception('欄位側邊高亮顏色格式錯誤')
                self.color = int(self.color[1:], 16)
        if self.footer:
            if self.footer.text:
                if len(self.footer.text) > 2048:
                    raise Exception('標題超過 2048 字符')
            if self.footer.icon_url:
                self.footer.icon_url = check_url(self.footer.icon_url)
        if self.fields:
            if len(self.fields) > 25:
                raise Exception('欄位數量超過 25 個')
        if self.timestamp:
            # 格式為:"YYYY-MM-DD hh:mm"
            if not re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$', self.timestamp):
                raise Exception('時間格式錯誤')
        if self.image:
            # Images功能無法正常使用，修改成一次只能上傳一張
            if self.image.url:
                self.image.url = check_url(self.image.url)

@dataclass
class Post:
    """Embeds不能與檔案同時傳送，需用requests.post(webhook, json=json)"""
    username: str|None = field(default=None) # 機器人名稱
    avatar_url: str|None = field(default=None) # 機器人頭像
    content: str|None = field(default=None) # 貼文內容
    embeds: list[Embed]|None = field(default=None) # 專欄
    thread_name : str|None = field(default=None)
    flags: int|None = field(default=None)
    mention_everyone: bool|None = field(default=None)
    #attachments: list[Attachment]|None = field(default=None) 

    def __post_init__(self):
        if self.username:
            if len(self.username) > 32:
                raise Exception('機器人名稱超過 32 字符')
        if self.avatar_url:
            self.avatar_url = check_url(self.avatar_url)
        if self.content:
            if len(self.content) > 2000:
                raise Exception('貼文內容超過 2000 字符')
        else:
            if not self.embeds:
                raise Exception('貼文內容為空')
        if self.embeds:
            if len(self.embeds) > 10:
                raise Exception('專欄數量超過 10 個')
            
        if self.thread_name:
            if len(self.thread_name) > 256:
                raise Exception('用於論壇或體育頻道(指定串名稱) 超過 256 字符')

@dataclass
class Files:
    """
    檔案不能與Embed混用，需用requests.post(webhook, data=json, files=files)
    files: {'filename.ext': open('filename.ext', 'rb')}
    """
    files: Dict[str, bytes]



def check_url(url: str) -> str:
    if url.startswith("http://") or url.startswith("https://"):
        return url
    raise Exception("Invalid url")

def split_text(text: str, limit: int) -> list[str]:
    """
    將文字依據限制長度進行分段
    優先以換行符號 `\n` 拆分，超過限制才會拆字串
    """
    segments = []
    start = 0
    text_length = len(text)

    while start < text_length:
        # 如果剩下的長度在限制內，就直接加入
        if text_length - start <= limit:
            segment = text[start:].strip('\n')
            if segment:
                segments.append(segment)
            break

        # 嘗試從 start 到 limit 範圍內尋找最後一個換行符號
        end = start + limit
        newline_pos = text.rfind('\n', start, end)

        if newline_pos != -1:
            # 找到換行符，優先以此分段
            segment = text[start:newline_pos].strip('\n')
            start = newline_pos + 1  # 跳過換行
        else:
            # 沒有換行，直接以限制切斷
            segment = text[start:end].strip('\n')
            start = end

        if segment:
            segments.append(segment)

    return segments


def serialize_clean_dict(obj: Dict|list|Post) -> Dict|list:
    """將dataclass實例轉成dict，並且清理空白值"""
    if isinstance(obj, type):
        raise Exception('請輸入實例')
    elif is_dataclass(obj):
        obj = asdict(obj)  # 將 dataclass 轉成 dict
    
    if isinstance(obj, dict):
        return {
            k: serialize_clean_dict(v)
            for k, v in obj.items()
            if v not in (None, [], "", {})
        }
    elif isinstance(obj, list):
        return [serialize_clean_dict(i) for i in obj if i not in (None, [], "", {})]
    else:
        return obj