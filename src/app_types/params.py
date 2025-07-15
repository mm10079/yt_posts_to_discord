from dataclasses import dataclass, field

@dataclass
class DefaultParams:
    url: str = field(
        default= '',
        metadata={
            "nargs": "?",
            "help": "下載網址\n留空則調取channels資料夾中的設定檔",
            }
        )
    cookies: str = field(
        default= '',
        metadata={
            "help": "cookies 檔案路徑\n留空則使用網頁預設 cookies",
            }
        )

    def __post_init__(self):
        if not self.url or not self.url.startswith("http"):
            self.url = ""


@dataclass
class SaveParams:
    enable_posts: bool = field(
        default= True,
        metadata={
            "help": "是否下載貼文",
            }
    )
    post_output: str = field(
        default= 'downloads/posts',
        metadata={
            "help": "貼文儲存路徑",
            }
        )
    
    enable_media: bool = field(
        default= True,
        metadata={
            "help": "是否下載媒體檔案",
            }
    )
    media_output: str = field(
        default= 'downloads/media',
        metadata={
            "help": "下載檔案輸出路徑",
            }
        )
    
    enable_archive: bool = field(
        default= True,
        metadata={
            "help": "是否紀錄已下載內容",
            }
    )
    archive_output: str = field(
        default= 'database/archive.sqlite',
        metadata={
            "help": "下載檔案輸出路徑",
            }
        )

@dataclass
class TranslateParams:
    enable_translate: bool = field(
        default= False,
        metadata={
            "help": "是否翻譯貼文",
            }
    )
    chatgpt_model: str = field(
        default= 'gpt-3.5-turbo',
        metadata={
            "help": "翻譯模型",
            }
        )
    chatgpt_apikey: str = field(
        default= '',
        metadata={
            "help": "翻譯 API Key",
            }
        )


@dataclass
class DiscordParams:
    discord_original_token: str = field(
        default= '',
        metadata={
            "help": "Discord Token\n用於發送原始貼文",
            }
        )
    discord_translated_token: str = field(
        default= '',
        metadata={
            "help": "Discord Token\n用於發送翻譯貼文",
            }
        )
    discord_mediafile_token: str = field(
        default= '',
        metadata={
            "help": "Discord Token\n用於發送媒體檔案",
            }
        )
    discord_log_token: str = field(
        default= '',
        metadata={
            "help": "Discord Token\n用於發送系統通知",
        }
        )

@dataclass
class AdditionalParams:
    config_name: str = field(
        default= 'args.json',
        metadata={
            "help": "設定檔名",
            }
    )

@dataclass
class AllParams(DiscordParams, TranslateParams, SaveParams, DefaultParams):
    pass

@dataclass
class FileParams(AdditionalParams, AllParams):
    pass