from datetime import datetime
import os
import sys
import logging


def get_time():
    return datetime.now().strftime("%Y-%m-%d %H：%M：%S")

def setup_logging(name=__name__, log_file=None, level=logging.DEBUG):
    log = logging.getLogger(name)
    log.setLevel(level)  # 設定日誌層級
    
    # 清除現有處理器（防止重複添加）
    if log.hasHandlers():
        log.handlers.clear()
    
    # 添加文件日誌處理器
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        log.addHandler(file_handler)  # 直接添加處理器
    
    return log

def set_log_config(name="Main", level=logging.DEBUG):
    
    # 設置基本配置
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)-8s | %(module)-11s.%(funcName)-22s:%(lineno)-4d | %(threadName)s | %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # 設置第三方日誌層級
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('socketserver').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('socket').setLevel(logging.WARNING)
    logging.getLogger('http').setLevel(logging.WARNING)
    
    log = logging.getLogger(name)
    return log
