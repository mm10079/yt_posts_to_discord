import os
from typing import Any, TypeVar, Union, Sequence, Mapping


OriginImageEndPoint = '=s0?imgmax=0'
T = TypeVar("T")

def get_size(path: str) -> int:
    """
    給定一個路徑，回傳：
    - 若為檔案：該檔案大小（位元組）
    - 若為資料夾：資料夾中所有檔案的總大小（位元組）
    """
    if os.path.isfile(path):
        return os.path.getsize(path)
    elif os.path.isdir(path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if os.path.isfile(fp):
                    total_size += os.path.getsize(fp)
        return total_size
    else:
        raise FileNotFoundError(f"找不到路徑：{path}")

def deep_get(
    data: Union[Mapping[str, Any], Sequence[Any]],
    keys: Sequence[Union[str, int]],
    default: T = None,
) -> Union[Any, T]:
    """從嵌套的字典或列表中獲取值。
    支持多層級的鍵或索引，並提供默認值。
    :param data: 要查找的數據，可以是字典或列表。
    :param keys: 鍵或索引的序列，表示要查找的路徑。
    :param default: 如果未找到值，返回的默認值。
    :return: 找到的值或默認值。
    """
    for key in keys:
        if isinstance(data, dict) and isinstance(key, str):
            data = data.get(key, default)
        elif isinstance(data, list) and isinstance(key, int):
            if 0 <= key < len(data) or -len(data) <= key < 0:
                data = data[key]
            else:
                return default
        else:
            return default
    return data if data is not None else default

def get_origin_image_url(url: str) -> str:
    # 確保URL以http或https開頭
    if not url:
        return ''
    if not url.startswith(('http:', 'https:')):
        url = 'https:' + url
    url = url[:url.rfind('=s')] + OriginImageEndPoint
    return url
