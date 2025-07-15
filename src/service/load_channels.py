import os
import json
import logging

from dataclasses import asdict

from src import BASE_DIR
from src.app_types import params
from src.config import setting

log = logging.getLogger(__name__)

channels_folder = os.path.join(BASE_DIR, 'channels')

def create_default_channel(args_config):
    log.info("檢測到未存在channels資料夾，自動建立...")
    os.mkdir(channels_folder)
    os.mkdir(os.path.join(channels_folder, 'disable'))
    from dataclasses import asdict
    with open(os.path.join(channels_folder, 'disable', 'default.json'), 'w', encoding='utf8') as f:
        f.write(json.dumps(asdict(args_config), ensure_ascii=False, indent=4))

def loading_configs() -> list[params.FileParams]:
    """如果有輸入url變數，則以輸入變數執行，如無，則從Channels資料夾讀取"""
    configs = []
    args_config = setting.get_config()
    if args_config.url:
        configs.append(params.FileParams(**asdict(args_config)))
    else:
        if os.path.exists(channels_folder):
            log.info(f"開始匯入頻道列表，路徑：{channels_folder}")
            for channel in os.listdir(channels_folder):
                channel_path = os.path.join(channels_folder, channel)
                if os.path.splitext(channel_path)[1] == '.json':
                    log.info(f"匯入：{channel}.json")
                    try:
                        with open(channel_path, 'r', encoding='utf8') as f:
                            file_config = json.load(f)
                            file_config["config_name"] = os.path.basename(channel_path)
                            configs.append(params.FileParams(**file_config))
                    except Exception as e:
                        log.error(f"匯入失敗：{channel}.json，原因：{e}")
            log.info(f"匯入結束，總數：{len(configs)}\n")
                    
    if not configs:
        log.error("未找到任何配置文件")
        if not os.path.exists(channels_folder):
            create_default_channel(args_config)
        raise Exception("未找到任何配置文件")
    return configs