import os
import sys
import json
import time
import copy
import logging
import requests

from typing import Dict

from src.app_types import discord, post_parse
from src.service import compress

def get_split_line():
    if getattr(sys, 'frozen', False):
        # ✅ getattr 安全存取，避免靜態報錯
        base_path = getattr(sys, '_MEIPASS', os.getcwd())
    else:
        base_path = os.getcwd()
    return os.path.join(base_path, 'src', 'data', 'split_line.png')

log = logging.getLogger(__name__)

class discord_post:
    def __init__(self, webhook:str) -> None:
        self.webhook = webhook
        self.post = discord.Post(content=" ")
        self.posts_queue: list[discord.Post] = []
        self.embed = discord.Embed()
        self.embeds_queue: list[discord.Embed] = []
        self.files_queue: list[Dict[str, bytes]] = []

    def get_clean_post(self):
        post = copy.deepcopy(self.post)
        post.embeds = None
        post.content = None
        return post
    
    def get_clean_embed(self):
        embed = copy.deepcopy(self.embed)
        embed.fields = None
        return embed

    def add_content(self, content: str):
        """分割內容"""
        for text in discord.split_text(content, discord.DESCRIPTION_LIMIT):
            if not text:
                continue
            post = copy.deepcopy(self.post)
            post.embeds = None
            post.content = text
            self.posts_queue.append(post)

    def add_embed(self, description:str = "", fields: list[discord.Field] = []):
        for text in discord.split_text(description, discord.DESCRIPTION_LIMIT):
            if not text:
                continue
            post = self.get_clean_post()
            embed = self.get_clean_embed()
            embed.description = text
            post.embeds = [embed]
            self.posts_queue.append(post)
        if not self.embeds_queue and fields:
            self.embeds_queue.append(self.get_clean_embed())
        if fields:
            self.embeds_queue[-1].fields = fields

    def add_image(self, image: discord.EmbedUrl):
        if not self.embeds_queue and not self.posts_queue:
            embed = self.get_clean_embed()
            embed.image = image
            self.embeds_queue.append(embed)
        elif self.embeds_queue:
            self.embeds_queue[-1].image = image
        elif self.posts_queue:
            if not self.posts_queue[-1].embeds:
                self.posts_queue[-1].embeds = [self.get_clean_embed()]
            self.posts_queue[-1].embeds[-1].image = image

    def add_file(self, filename: str|None, file: str|bytes):
        file_byte = None
        if isinstance(file, str):
            if 'http' not in file:
                if not filename:
                    filename = os.path.basename(file)
                if os.path.exists(file):
                    with open(file, 'rb') as f:
                        file_byte = f.read()
                else:
                    raise Exception(f"路徑 {file} 不存在")
            else:
                if not filename:
                    filename = os.path.basename(file.split("=", 1)[0])
                response = requests.get(file)
                if response.status_code == 200:
                    file_byte = response.content
                else:
                    raise Exception(f"網址 {file} 無法下載")
        else:
            if not filename:
                filename = 'file'
            file_byte = file
        if len(file_byte) > 9 * 1024 * 1024:
            raise Exception(f"檔案 {filename} 太大")
        self.files_queue.append({filename: file_byte})

    def send(self, source_post: discord.Post, files: Dict[str, bytes]|None = None):
        post = discord.serialize_clean_dict(source_post)
        if files:
            response = requests.post(self.webhook, data=post, files=files)
        else:
            response = requests.post(self.webhook, json=post)
        if response.status_code != 204:
            log.error(f"發送貼文失敗，狀態碼：{response.status_code}")
            raise Exception(f"發送貼文失敗：{response.text}")

    def start_send(self):
        file_post = copy.deepcopy(self.post)
        file_post.embeds = None
        file_post.content = None
        for post in self.posts_queue:
            self.send(source_post=post)
            time.sleep(0.5)
        if self.embeds_queue:
            embed_post = copy.deepcopy(file_post)
            embed_post.embeds = self.embeds_queue
            self.send(source_post=embed_post)
            time.sleep(0.5)
        for files in self.files_queue:
            self.send(source_post=file_post, files=files)
            time.sleep(0.5)

def send_post(webhook: str, post_parser: post_parse.PostParser):
    set_post = discord_post(webhook)
    # 初始化貼文基礎資訊
    post = set_post.post
    post.username = post_parser.author_name
    post.avatar_url = post_parser.author_thumbnail
    # 初始化Embed基礎資訊
    set_post.embed.author = discord.Author(
        name=post_parser.author_name,
        url=post_parser.channel_url,
        icon_url=post_parser.author_thumbnail
        )
    set_post.embed.title = "頻道會員限定" if post_parser.is_membership else "公開貼文"
    set_post.embed.url = post_parser.post_url
    set_post.embed.color = int("#584AD7"[1:], 16)
    set_post.embed.timestamp = f"{post_parse.today.year}-{post_parse.today.month}-{post_parse.today.day} {post_parse.today.hour}:{post_parse.today.minute}"
    set_post.embed.footer = discord.Footer(text=post_parser.author_name, icon_url=post_parser.author_thumbnail)
    # 添加貼文內文
    set_post.add_embed(description=post_parser.content_text)
    # 添加貼文附件
    for attachment in post_parser.attachments:
        set_post.add_image(image=discord.EmbedUrl(url=attachment))
    if post_parser.video:
        # 添加影片
        video_embed = discord.Embed(
            author = discord.Author(
                name=post_parser.video.uploader_name,
                url=post_parser.video.uploader_channel,
                icon_url=post_parser.video.uploader_thumbnail
                ),
            title = post_parser.video.title,
            url = post_parser.video.url,
            image=discord.EmbedUrl(url=post_parser.video.thumbnail),
            description = post_parser.video.description,
            color = "#584AD7",
            timestamp = f"{post_parser.today[0:4]}-{post_parser.today[4:6]}-{post_parser.today[6:]} 00:00",
            footer = discord.Footer(text=f"影片長度 {post_parser.video.length}", icon_url=post_parser.author_thumbnail)
            )
        set_post.embeds_queue.append(video_embed)
    # 添加分隔線
    set_post.add_file(filename="split_line.png", file=get_split_line())
    set_post.start_send()

    
def send_media(webhook: str, post_parser: post_parse.PostParser, success: list[post_parse.FileInfo], error: list[post_parse.FileInfo], unknown: list[post_parse.FileInfo]):
    if not success and not error and not unknown:
        return
    
    set_post = discord_post(webhook)
    # 初始化貼文基礎資訊
    post = set_post.post
    post.username = post_parser.author_name
    post.avatar_url = post_parser.author_thumbnail

    # 初始化Embed基礎資訊
    set_post.embed.author = discord.Author(
        name=post_parser.author_name,
        url=post_parser.channel_url,
        icon_url=post_parser.author_thumbnail
        )
    set_post.embed.title = "下載狀態通知"
    set_post.embed.url = post_parser.post_url
    set_post.embed.color = int("#584AD7"[1:], 16)
    set_post.embed.timestamp = f"{post_parse.today.year}-{post_parse.today.month}-{post_parse.today.day} {post_parse.today.hour}:{post_parse.today.minute}"
    set_post.embed.footer = discord.Footer(text=post_parser.author_name, icon_url=post_parser.author_thumbnail)
    
    # 添加貼文內文
    description = ""
    for file in success:
        description += f"成功：[{file.name}]({file.url})\n"
        if file.size < discord.FILE_LIMIT:
            c_filepath = file.path
            if not os.path.isfile(file.path):
                c_filepath = file.path + '.7z'
                if not os.path.exists(c_filepath):
                    log.info(f"壓縮檔案：{c_filepath}")
                    compress.compress_to_7z(file.path)
            set_post.add_file(filename=file.name, file=c_filepath)

        if os.path.isfile(file.path):
            file_ext = file.path.split('.')[-1]
            if file_ext in ['rar', 'zip', '7z']:
                os.remove(file.path)


    for file in error:
        description += f"失敗：[{file.name}]({file.url})\n"
    n = 0
    for file in unknown:
        n += 1
        description += f"未知：[{n}.檔案]({file.url})\n"
    set_post.add_embed(description=description)
    
    set_post.start_send()