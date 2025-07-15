import os
import sys
from datetime import datetime

def format_path(date_format="%Y%m%d"):
    return datetime.now().strftime(date_format)

def get_mdrs():
    if getattr(sys, 'frozen', False):
        # ✅ getattr 安全存取，避免靜態報錯
        base_path = getattr(sys, '_MEIPASS', os.getcwd())
    else:
        base_path = os.getcwd()
    if os.name == "nt":
        return os.path.join(base_path, 'data', 'mdrs.exe')
    else:
        return os.path.join(base_path, 'data', 'mdrs')
