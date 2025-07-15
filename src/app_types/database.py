from dataclasses import dataclass, field, fields
from enum import Enum
from typing import List

class Status(int, Enum):
    NOT_PROCESS = 0
    FINISH = 1

class Data_PostEnum(str, Enum):
    ID = 'id'
    PID = 'pid'
    TIME = 'time'
    CONTENT = 'content'
    LINKS = 'links'
    MEMBERSHIP = 'membership'
    ORIGIN_NOTIFY = 'origin_notify'
    TRANSLATE_NOTIFY = 'translate_notify'
    MEDIA_NOTIFY = 'media_notify'
    DOWNLOADED = 'downloaded'

@dataclass
class Data_Post:
    id: int = field(
        default=0,
        metadata={
            "sql": "PRIMARY KEY AUTOINCREMENT",
        }) # 紀錄貼文儲存ID順序
    pid: str = '' # 紀錄貼文ID
    time: str = '' # 紀錄下載時間(YT沒有貼文發布時間)
    content: dict = field(default_factory=dict) # 紀錄貼文Json完整內容
    links: List[str] = field(default_factory=list) # 紀錄所有連結
    membership: int = Status.NOT_PROCESS # 紀錄是否為會員貼文
    origin_notify: int = Status.NOT_PROCESS # 紀錄上傳貼文狀態
    translate_notify: int = Status.NOT_PROCESS # 紀錄翻譯貼文狀態
    media_notify: int = Status.NOT_PROCESS # 紀錄下載媒體檔案狀態
    downloaded: int = Status.NOT_PROCESS # 紀錄下載媒體檔案狀態
