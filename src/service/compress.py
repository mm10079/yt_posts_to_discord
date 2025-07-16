import logging
import shutil
import zipfile
import tarfile
import py7zr
import os
import enum

from src.utils import path_format

log = logging.getLogger(__name__)

class CompressType(enum.Enum):
    ZIP = "zip"
    RAR = "rar"
    TAR = "tar"
    GZ = "gz"
    _7Z = "7z"

class Uncompresser:
    def uncompress(self, filepath:str, output = "", decode = ""):
        """解壓縮基礎參數"""
        raise NotImplementedError("子類必須實現 解壓縮方法")
    
    def _ensure_path_exists(self, output):
        """確保目錄存在"""
        os.makedirs(output, exist_ok=True)

    def auto_outpath(self, filepath):
        return os.path.dirname(filepath)

class UncompressZip(Uncompresser):
    def uncompress(self, filepath:str, output = "", decode = ""):
        if not output:
            output = self.auto_outpath(filepath)
        self._ensure_path_exists(output)
        """解壓縮 ZIP 檔案"""
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            if decode == 'shift_jis':
                for file in zip_ref.namelist():
                    decoded_name = file.encode('cp437').decode('shift_jis')
                    target_path = os.path.join(output, decoded_name)
                    with zip_ref.open(file) as source, open(target_path, 'wb') as target:
                        shutil.copyfileobj(source, target)
            else:
                zip_ref.extractall(output)
        log.debug(f"已解壓縮 ZIP 檔案: {filepath}")

class UncompressRar(Uncompresser):
    def uncompress(self, filepath:str, output = "", decode = ""):
        if not output:
            output = self.auto_outpath(filepath)
        self._ensure_path_exists(output)
        if os.name == 'nt':
            unrar = path_format.get_unrar()
            if not os.path.exists(unrar):
                raise Exception("UnRAR.exe 不存在")
            os.system(f'"{unrar}" x -inul "{filepath}" -o+ "{output}"')
        else:
            from unrar import rarfile
            with rarfile.RarFile(filepath, 'r') as rar_ref:
                if decode == 'shift_jis':
                    for file in rar_ref.infolist():
                        decoded_name = file.filename.encode('cp437').decode('shift_jis')
                        target_path = os.path.join(output, decoded_name)
                        with rar_ref.open(file.filename) as source, open(target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                else:
                    rar_ref.extractall(output)
        log.debug(f"已解壓縮 RAR 檔案: {filepath}")

class Uncompress7Z(Uncompresser):
    def uncompress(self, filepath:str, output = "", decode = ""):
        if not output:
            output = self.auto_outpath(filepath)
        self._ensure_path_exists(output)
        """解壓縮 7Z 檔案"""
        with py7zr.SevenZipFile(filepath, mode='r') as z:
            z.extractall(path=output)
        log.debug(f"已解壓縮 7Z 檔案: {filepath}")

class UncompressTar(Uncompresser):
    def uncompress(self, filepath:str, output = "", decode = ""):
        if not output:
            output = self.auto_outpath(filepath)
        self._ensure_path_exists(output)
        """解壓縮 TAR 或 GZ 檔案"""
        with tarfile.open(filepath, 'r:*') as tar_ref:
            tar_ref.extractall(output)
        log.debug(f"已解壓縮 TAR/GZ 檔案: {filepath}")

class UncompresserFactory:
    @staticmethod
    def get_uncompresser(filepath):
        filename = os.path.basename(filepath)
        log.debug(f"開始解壓縮：{filename}")
        if 'zip' in filename:
            return UncompressZip()
        elif 'rar' in filename:
            return UncompressRar()
        elif '7z' in filename:
            return Uncompress7Z()
        elif 'tar' in filename or 'gz' in filename:
            return UncompressTar()
        else:
            raise ValueError(f"不支援的壓縮檔案：{filename}")

def is_valid_compressed_file(file_path, exts):
    """
    驗證檔案是否為有效的可解壓縮檔案。
    :param file_path: 要檢查的檔案路徑
    :return: 如果符合條件，返回 True，否則返回 False
    """
    # 獲取檔案的名稱和副檔名
    file_name = os.path.basename(file_path)
    file_parts = file_name.split('.')

    # 檢查是否為分卷檔案（多層副檔名情況）
    if len(file_parts) > 2 and file_parts[-1].isdigit():
        # 確認前一層副檔名是否在支援的壓縮格式中
        main_ext = file_parts[-2].lower()
        if main_ext not in exts:
            return False

        # 提取分卷號，檢查是否為第一個分卷
        part_number = int(file_parts[-1])
        if part_number > 1:
            return False

    # 單層副檔名檢查
    elif file_parts[-1].lower() not in exts:
        return False

    return True

def compress_to_7z(path: str, output_dir: str|None = None):
    """
    給定一個檔案或資料夾路徑，將其壓縮為 .7z 檔案。
    - 檔案：使用原始檔案名稱（改成 .7z）
    - 資料夾：使用資料夾名稱作為壓縮檔名

    :param path: 要壓縮的路徑（檔案或資料夾）
    :param output_dir: 壓縮檔輸出目錄（預設為與來源相同）
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"指定的路徑不存在：{path}")
    
    base_path = os.path.abspath(path)
    parent_dir = os.path.dirname(base_path)
    name = os.path.basename(base_path)

    if output_dir is None:
        output_dir = parent_dir

    # 決定壓縮檔名稱
    if os.path.isdir(base_path):
        archive_name = f"{name}.7z"
    elif os.path.isfile(base_path):
        name_wo_ext = os.path.splitext(name)[0]
        archive_name = f"{name_wo_ext}.7z"
    else:
        raise ValueError("路徑既不是檔案也不是資料夾")

    archive_path = os.path.join(output_dir, archive_name)

    # 執行壓縮
    with py7zr.SevenZipFile(archive_path, 'w') as archive:
        if os.path.isdir(base_path):
            archive.writeall(base_path, arcname=name)  # 壓縮整個資料夾
        else:
            archive.write(base_path, arcname=name)  # 壓縮單一檔案

    log.info(f"壓縮完成：{archive_path}")
