import re
import sys
import logging
from typing import List
from requests.cookies import create_cookie
from http import cookiejar
from youtube_community_tab.post import Post
from youtube_community_tab.community_tab import CommunityTab
from youtube_community_tab.requests_handler import requests_cache

#This is a modified version of youtube_community_tab
#https://github.com/HoloArchivists/youtube-community-tab

POST_REGEX=r"^(?:(?:https?:\/\/)?(?:.*?\.)?(?:youtube\.com\/)((?:channel\/UC[a-zA-Z0-9_-]+\/community\?lb=)|post\/))?(?P<post_id>Ug[a-zA-Z0-9_-]+)(.*)?$"
CHANNEL_REGEX=r"^(?:(?:https?:\/\/)?(?:.*?\.)?(?:youtube\.com\/))((?P<channel_handle>@[a-zA-Z0-9_-]+)|((channel\/)?(?P<channel_id>UC[a-zA-Z0-9_-]+)))(?:\/.*)?$"
HANDLE_TO_ID_REGEX = r'"channelId":"(UC[a-zA-Z0-9_-]+)"'
CLEAN_FILENAME_KINDA=r"[^\w\-_\. \[\]\(\)]"

log = logging.getLogger(__name__)

def use_default_cookies():
    requests_cache.cookies.set(
        'SOCS',
        'CAESNQgDEitib3FfaWRlbnRpdHlmcm9udGVuZHVpc2VydmVyXzIwMjIwNzA1LjE2X3AwGgJwdCACGgYIgOedlgY',
        domain='.youtube.com',
        path='/'
    )
    requests_cache.cookies.set(
        'CONSENT',
        'PENDING+917',
        domain='.youtube.com',
        path='/'
    )

def use_cookies(cookie_jar_path):
    cookie_jar = cookiejar.MozillaCookieJar(cookie_jar_path)
    try:
        cookie_jar.load()
        log.info(f"讀取cookies路徑：{cookie_jar_path}")
    except FileNotFoundError:
        use_default_cookies()
        log.error(f"無法找到cookies檔：{cookie_jar_path}，繼續使用預設cookies...")
        return
    except (cookiejar.LoadError, OSError) as e:
        use_default_cookies()
        log.error(f"{e}")
        log.error(f"無法讀取cookies：{cookie_jar_path}，繼續使用預設cookies")
        return
        # 將 MozillaCookieJar 的 cookies 一個一個轉入 requests 的 cookie jar
    for c in cookie_jar:
        cookie = create_cookie(
            name=c.name,
            value=c.value,
            domain=c.domain,
            path=c.path,
            secure=c.secure,
            expires=c.expires,
        )
        requests_cache.cookies.set_cookie(cookie)
        
def get_channel_id_from_handle(channel_handle):
    handle_url = f"https://youtube.com/{channel_handle}"
    channel_home_r = requests_cache.get(handle_url)
    if not channel_home_r.ok:
        log.critical(f"無法將頻道標籤轉換為頻道ID編號，無回應{handle_url}")
        sys.exit(1)
    channel_home = channel_home_r.text
    if (channel_id_m := re.search(HANDLE_TO_ID_REGEX, channel_home)) and \
        (channel_id := channel_id_m.group(1)):
        return channel_id
    log.critical(f"無法將頻道標籤轉換為頻道ID編號，資料格式可能已變更")
    sys.exit(1)

def get_post(post_id):
    post = Post.from_post_id(post_id)
    return post

def get_channel_posts(channel_id:str, reverse: bool = True):
    """讀取頻道的全部社群貼文"""
    ct = CommunityTab(channel_id)
    ct.channel_id = channel_id
    page_count = 1
    print(f"從社群貼文中獲取貼文 (頁面{page_count})", end="\r")
    ct.load_posts(0)
    while(ct.posts_continuation_token):
        page_count += 1
        print(f"從社群貼文中獲取貼文 (頁面{page_count})", end="\r")
        ct.load_posts(0)
    log.info(f"從社群貼文中獲取貼文 (頁面{page_count})")
    log.info(f"找到 {len(ct.posts)} 則貼文")
    if reverse:
        ct.posts = list(reversed(ct.posts))
    return ct.posts

def clean_name(text):
    return re.sub(CLEAN_FILENAME_KINDA, "_", text)

def main(link: str, cookies_path: str= "", reverse: bool=True) -> List[Post]:
    if cookies_path:
        use_cookies(cookies_path)
    else:
        use_default_cookies()
    posts = []
    post_id_m = re.search(POST_REGEX, link)
    channel_id_m = re.search(CHANNEL_REGEX, link)
    if post_id_m:
        log.info(f"開始解析貼文網址...")
        post_id = post_id_m.group("post_id")
        posts.append(get_post(post_id))
    elif channel_id_m:
        channel_handle = channel_id_m.group("channel_handle")
        if channel_handle:
            channel_id = get_channel_id_from_handle(channel_handle)
            log.info(f"將頻道標籤轉換為頻道ID編號：{channel_handle} -> {channel_id}")
        else:
            channel_id = channel_id_m.group("channel_id")
        log.info(f"開始解析頻道網址...")
        posts.extend(get_channel_posts(channel_id, reverse))
    else:
        log.info(f"無法解析的網址類型：{link}")
    log.info("爬取完成！")
    return posts