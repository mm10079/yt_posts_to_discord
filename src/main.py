import os
import asyncio

from youtube_community_tab.post import Post as YT_Post

from src import BASE_DIR, __description__
from src.app_types.post_parse import PostParser
from src.app_types.database import Data_PostEnum, Data_Post, Status
from src.core import data_convert
from src.config import logger
from src.service import load_channels, graber, archive, downloader, notify, translate

log = logger.setup_logging()

class work_station:
    def __init__(self, config: load_channels.params.FileParams) -> None:
        self.config = config
        self.db = None
        self.init_database()

        self.data_posts = []

    def init_database(self):
        if self.config.enable_archive:
            self.db = archive.database(self.config.archive_output, os.path.splitext(os.path.basename(self.config.config_name))[0], Data_Post)

    def get_posts(self):
        """去除資料庫已有的貼文，並將貼文轉成Data_Post類型並儲存到self.data_posts"""
        try:
            yt_posts: list[YT_Post] = graber.main(self.config.url, self.config.cookies)
        except Exception as e:
            log.error(f"爬取失敗：{e}\n")
            return

        skip_pids = []
        _posts: list[Data_Post] = []
        if self.db:
            skip_pids = self.db.get_values_from_key('pid')
        for post in yt_posts:
            post_contetn = post.as_json()
            if post_contetn['post_id'] in skip_pids:
                continue
            _posts.append(data_convert.convert_post_to_type(post_contetn))
            self.data_posts = _posts # 清除已存在的貼文

    def record_posts(self):
        if not self.db and not self.config.post_output:
            log.info("未設定儲存位置與資料庫位置，跳過儲存貼文")
            return
        
        log.info(f"未紀錄貼文數：{len(self.data_posts)}")
        for post in self.data_posts:
            if self.db:
                self.db.save_new_post(post)
                log.info(f"紀錄貼文：{post.pid}")

            if self.config.enable_posts and self.config.post_output:
                savepath = os.path.join(self.config.post_output, post.time)
                os.makedirs(savepath, exist_ok=True)
                # 儲存貼文
                downloader.download_json(os.path.join(savepath, f"{post.pid}.json"), post.content)
                log.info(f"儲存貼文：{post.pid}")
                # 儲存貼文附件
                asyncio.run(downloader.save_attachments(savepath, post.pid, post.links))

    def notify_posts(self):
        """發送原文貼文至Discord"""
        if not self.config.discord_original_token:
            return
        log.info(f"開始讀取待通知貼文...")
        if self.db:
            self.data_posts = self.db.get_specific_list(Data_PostEnum.ORIGIN_NOTIFY.value, Status.NOT_PROCESS)
            log.info(f"未通知原文貼文數：{len(self.data_posts)}")
        for post in self.data_posts:
            log.info(f"通知貼文：{post.pid}")
            try:
                post_parser = PostParser(post.content)
                notify.send_post(self.config.discord_original_token, post_parser)
                if self.db:
                    self.db.insert_post_data(Data_PostEnum.PID.value, post.pid, Data_PostEnum.ORIGIN_NOTIFY.value, Status.FINISH.value)
            except Exception as e:
                log.error(f"通知失敗，PID：{post.pid}")
                log.error(f"通知貼文失敗：{e}")

    def translate_posts(self):
        """發送翻譯貼文至Discord"""
        if not self.config.enable_translate or \
            not self.config.chatgpt_apikey or \
            not self.config.chatgpt_model or \
            not self.config.discord_translated_token:
            return
        log.info(f"開始讀取待翻譯貼文...")
        if self.db:
            self.data_posts = self.db.get_specific_list(Data_PostEnum.TRANSLATE_NOTIFY.value, Status.NOT_PROCESS)
            log.info(f"未通知翻譯貼文數：{len(self.data_posts)}")
        gpt = translate.Chatgpt(self.config.chatgpt_apikey, self.config.chatgpt_model)
        for post in self.data_posts:
            log.info(f"通知貼文：{post.pid}")
            try:
                post_parser = PostParser(post.content)
                # 翻譯貼文
                post_parser.content_text = gpt.translate(post_parser.content_text)
                if post_parser.video:
                    # 翻譯影片介紹
                    post_parser.video.description = gpt.translate(post_parser.video.description)
                notify.send_post(self.config.discord_translated_token, post_parser)
                if self.db:
                    self.db.insert_post_data(Data_PostEnum.PID.value, post.pid, Data_PostEnum.TRANSLATE_NOTIFY.value, Status.FINISH.value)
            except Exception as e:
                log.error(f"通知失敗，PID：{post.pid}")
                log.error(f"通知貼文失敗：{e}")
        
    def dl_media(self):
        if not self.config.enable_media or not self.config.media_output:
            return

        log.info(f"開始讀取待下載媒體貼文...")
        if self.db:
            self.data_posts = self.db.get_specific_list(Data_PostEnum.DOWNLOADED.value, Status.NOT_PROCESS)
            log.info(f"未下載媒體貼文數：{len(self.data_posts)}")
        for post in self.data_posts:
            log.info(f"下載媒體貼文：{post.pid}")
            try:
                success, error, unknown  = downloader.download_links(self.config.media_output, post.links)
                if success or error or unknown:
                    log.info(f"[PID:{post.pid}]下載狀態總結：{len(success)} 個成功，{len(error)} 個失敗，{len(unknown)} 個未知")
                if self.db and not error:
                    self.db.insert_post_data(Data_PostEnum.PID.value, post.pid, Data_PostEnum.DOWNLOADED.value, Status.FINISH.value)
                else:
                    for f in error:
                        log.error(f"[PID:{post.pid}]下載失敗：{f.url}")
                for f in unknown:
                    log.warning(f"[PID:{post.pid}]未知檔案名稱，需檢查是否下載成功：{f.url}")
                if self.config.discord_download_token:
                    notify.send_media(self.config.discord_download_token, PostParser(post.content), success, error, unknown)
            except Exception as e:
                log.error(f"[PID:{post.pid}]下載媒體貼文失敗")

def main():
    log.info(f"開始執行主程式...")
    log.info(__description__)
    configs = load_channels.loading_configs()
    for config in configs:
        log.info(f"取得設定檔：{config.config_name}")
        log.info(f"網址：{config.url}")
        station = work_station(config)
        station.get_posts()
        station.record_posts()
        station.notify_posts()
        station.translate_posts()
        station.dl_media()
        log.info(f"設定檔：{config.config_name} 作業完成！\n")
    log.info(f"執行主程式結束")

if __name__ == "__main__":
    main()

