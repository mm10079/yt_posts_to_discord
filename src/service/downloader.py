import os
import time
import json
import aiohttp
import asyncio
import aiofiles
import logging
import requests
import subprocess

from urllib.parse import unquote
from src.utils import path_format
from src.app_types import post_parse
from src.service import compress

log = logging.getLogger(__name__)

def download_json(filepath, content):
    if os.path.exists(filepath):
        log.info(f'檔案已存在：{filepath}')
        return
    log.debug(f'儲存json檔案：{filepath}')
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(json.dumps(content, indent=4, ensure_ascii=False))

def download_file_by_url(url: str, filepath: str, cookies: dict | None = None, headers: dict | None=None, stream=True, retry_times=6, chunk_size=262144, timeout=30, size_check = True):
    if not filepath:
        log.error("檔案路徑無效！")
        return False
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    session = requests.Session()
    for attempt in range(1, retry_times + 1):
        if cookies:
            session.cookies.update(cookies)
        try:
            response = session.get(url, headers=headers, stream=stream, timeout=timeout)
            if response.status_code != 200:
                log.warning(f"HTTP 狀態碼錯誤: {response.status_code}，URL: {url}，嘗試次數: {attempt}")
                time.sleep(3)
                continue

            file_size = int(response.headers.get('Content-Length', 0))
            if file_size == 0:
                log.warning(f"伺服器返回空檔案，URL: {url}，嘗試次數: {attempt}")
                time.sleep(3)
                continue

            if os.path.exists(filepath):
                local_size = os.path.getsize(filepath)
                if size_check:
                    # 確認檔案大小一致
                    if local_size != file_size:
                        log.warning(f"檔案異常！檔案路徑: {filepath}")
                        log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                        os.remove(filepath)
                    else:
                        log.info(f"檔案已存在: {filepath}，大小: {local_size / 1024 / 1024:.2f} MB")
                        response.close()
                        return True
                else:
                    log.info(f"檔案已存在: {filepath}，跳過檔案大小檢查")
                    response.close()
                    return True

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # 避免空內容
                        f.write(chunk)
            
            local_size = os.path.getsize(filepath)
            if size_check:
                # 確認檔案大小一致
                if local_size != file_size:
                    log.warning(f"檔案異常！檔案路徑: {filepath}")
                    log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                    os.remove(filepath)
                    time.sleep(3)
                    continue

            log.info(f"下載成功: {filepath}，大小: {local_size / 1024 / 1024:.2f} MB")
            return True

        except Exception as e:
            log.warning(f"下載時發生其他錯誤: {e}，嘗試次數: {attempt}")
            time.sleep(3)

    log.error(f"下載失敗，URL: {url}")
    return False

async def async_download(url: str, filepath: str, session: aiohttp.ClientSession, retry_times=3, chunk_size=262144, timeout=10, size_check = True):
    timeout_context = aiohttp.ClientTimeout(total=timeout)
    for attempt in range(1, retry_times + 1):
        try:
            async with session.get(url, timeout=timeout_context) as response:
                if response.status != 200:
                    log.warning(f"HTTP 狀態碼錯誤: {response.status}，URL: {url}，嘗試次數: {attempt}")
                    await asyncio.sleep(3)
                    continue

                file_size = int(response.headers.get('Content-Length', 0))
                file_ext = response.headers.get('Content-Type', 'application/octet-stream').split(';', 1)[0].split('/', 1)[1].replace("jpeg", "jpg")
                if '{ext}' in filepath:
                    filepath = filepath.format(ext=file_ext)
                if file_size == 0:
                    log.warning(f"伺服器返回空檔案，URL: {url}，嘗試次數: {attempt}")
                    await asyncio.sleep(3)
                    continue

                if os.path.exists(filepath):
                    local_size = os.path.getsize(filepath)
                    if size_check:
                        # 確認檔案大小一致
                        if local_size != file_size:
                            log.warning(f"檔案異常！移除檔案: {filepath}")
                            log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                            os.remove(filepath)
                        else:
                            log.info(f"檔案已存在: {filepath}，符合大小: {local_size / 1024 / 1024:.2f} MB")
                            response.close()
                            return True
                    else:
                        log.info(f"檔案已存在: {filepath}，跳過檔案大小檢查")
                        response.close()
                        return True

                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        if chunk:  # 避免空內容
                            await f.write(chunk)
                
                local_size = os.path.getsize(filepath)
                if size_check:
                    # 確認檔案大小一致
                    if local_size != file_size:
                        log.warning(f"檔案異常！移除檔案: {filepath}")
                        log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                        await asyncio.sleep(3)
                        os.remove(filepath)
                        continue

            log.info(f"下載成功: {filepath}，大小: {local_size / 1024 / 1024:.2f} MB")
            return True
        except asyncio.TimeoutError:
            log.warning(f"下載超時，URL: {url}，嘗試次數: {attempt}")
        except Exception as e:
            log.warning(f"下載時發生其他錯誤: {e}，嘗試次數: {attempt}")
        await asyncio.sleep(1)
        if os.path.exists(filepath):
            os.remove(filepath)
        await asyncio.sleep(3)

    log.error(f"下載失敗，URL: {url}")
    return False

async def save_attachments(folder: str, pid: str, links: list[str]):
    session = aiohttp.ClientSession()
    tasks = []
    for link in links:
        if '=s0?imgmax=0' not in link:
            continue
        filepath = os.path.join(folder, f"{pid}_{len(tasks)}." + '{ext}')
        log.info(f"下載附件：{link}")
        task = async_download(link, filepath, session)
        tasks.append(task)
    await asyncio.gather(*tasks)
    await session.close()



def mediafire_downloader(url: str, folder: str):
    if '/file' == url[-5:]:
        url = url[:-5]
    if '/view/' in url:
        url = url.replace('/view/', '/file/')

    filename = ''
    if '/file/' in url or '/folder/' in url or '/file_premium/' in url:
        filename = unquote(url.split('/')[-1].replace('+', ' '))
    elif 'app.' in url:
        log.info(f"無法取得檔案名稱！URL: {url}")

    mediafire = path_format.get_mdrs()
    command = [mediafire, '-o', folder, url]
    try:
        subprocess.run(command)  
    except subprocess.CalledProcessError as response:
        log.error(f"下載失敗！URL: {url}")
        log.error(f"錯誤訊息：\n{response.stderr.decode('utf-8')}")
    return filename

def download_links(folder: str, links: list[str]) -> tuple[list[post_parse.FileInfo], list[post_parse.FileInfo], list[post_parse.FileInfo]]:
    """return success, error, unknown"""
    success, error, unknown = [], [], []
    for link in links:
        file_info = None
        if 'mediafire' in link:
            log.info(f"下載媒體貼文：{link}")
            filename = mediafire_downloader(link, folder)
            filepath = os.path.join(folder, filename)
            file_info = post_parse.FileInfo(path=filepath, url=link, name=filename)
        if file_info:
            if file_info.size:
                success.append(file_info)
                try:
                    compress.UncompresserFactory.get_uncompresser(filepath).uncompress(filepath)
                except Exception as e:
                    pass
            elif not file_info.name:
                unknown.append(file_info)
            else:
                error.append(file_info)
    return success, error, unknown