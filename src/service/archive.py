import os
import json
import sqlite3
import logging
from dataclasses import asdict, fields

log = logging.getLogger(__name__)

python_to_sqlite = {
    int: "INTEGER",
    float: "REAL",
    str: "TEXT",
    bool: "BOOLEAN",
    dict: "TEXT",   # 這些實際是 JSON 儲存
    list: "TEXT",
}

def replace_illegal_characters(word):
    # 将表名中的非法字符替换为空格
    word = word.replace('-', '').replace(',', '').replace('.', '').replace('"', '').replace('=', '').replace(' ', '')
    word = word.replace('()', '<>')
    return word

def serialize_value(value):
    '''將值序列化為字符串'''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    elif isinstance(value, bool):
        return str(value)
    return value
    
class database:
    '''使用dataclass作為儲存格式'''
    def __init__(self, path: str, table_name: str, dataclass_cls: type):
        self.path = path
        self.table_name = replace_illegal_characters(table_name)
        self.dataclass_cls = dataclass_cls
        self.skip_auto_key = ""
        self.create_new_table()

    def create_new_table(self):
        log.info(f'選擇儲存表："{self.table_name}"')
        columns = []
        for col, py_type in self.dataclass_cls.__annotations__.items():
            sql_type = python_to_sqlite.get(py_type, "TEXT")  # 預設為 TEXT
            sql_command = self.dataclass_cls.__dataclass_fields__[col].metadata.get("sql", "")
            if 'PRIMARY KEY AUTOINCREMENT' in sql_command:
                self.skip_auto_key = col
            columns.append(f"{col} {sql_type} {sql_command}".strip())
        command = f"CREATE TABLE IF NOT EXISTS {self.table_name} ({', '.join(columns)})"
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with sqlite3.connect(self.path) as conn:
            conn.cursor().execute(command)

    def save_new_post(self, item):
        data = asdict(item)
        if self.skip_auto_key in data.keys():
            # 刪除自增主鍵
            del data[self.skip_auto_key]
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = [serialize_value(v) for v in data.values()]
        sql = f'INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})'
        with sqlite3.connect(self.path) as conn:
            conn.execute(sql, values)

    def get_values_from_key(self, key: str) -> list:
        """ 取得指定key的所有值
        並自動轉換成對應的 Python 類型
        """
        values = []
        for col, py_type in self.dataclass_cls.__annotations__.items():
            if col == key:
                break
        with sqlite3.connect(self.path) as conn:
            for data in conn.cursor().execute(f"SELECT {key} FROM {self.table_name}"):
                raw_value = data[0]
                if py_type == bool:
                    if raw_value == 'True':
                        values.append(True)
                    else:
                        values.append(False)
                elif py_type in (list, dict):
                    values.append(json.loads(raw_value))
                else:
                    values.append(py_type(raw_value))
        return values

    def get_specific_list(self, keyword, data_value) -> list:
        with sqlite3.connect(self.path) as conn:
            cursor = conn.execute(
                f'SELECT * FROM {self.table_name} WHERE {keyword} = ?',
                (serialize_value(data_value),)
            )
            col_names = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()

            # 預先建立欄位型別對照表
            field_types = {f.name: f.type for f in fields(self.dataclass_cls)}

            results = []
            for row in data:
                row_dict = dict(zip(col_names, row))

                for name, val in row_dict.items():
                    expected_type = field_types.get(name)
                    if expected_type is None:
                        continue

                    # 將資料轉換成對應的 dataclass 欄位型別
                    if expected_type == bool:
                        row_dict[name] = val in ('1', 1, 'True', 'true', True)
                    elif expected_type == list or expected_type == dict:
                        try:
                            row_dict[name] = json.loads(val)
                        except (TypeError, json.JSONDecodeError):
                            row_dict[name] = [] if expected_type == list else {}
                    else:
                        # 可擴充其他型別（如 datetime 等）
                        row_dict[name] = val

                results.append(self.dataclass_cls(**row_dict))

            return results
    def insert_post_data(self, select_column:str, select_value, insert_column:str, insert_data):
        """
        更新指定貼文的資料
        """
        log.info(f'儲存貼文資料： "{select_column}" "{select_value}" "{insert_column}" "{insert_data}"')
        with sqlite3.connect(self.path) as conn:
            conn.cursor().execute(f'UPDATE {self.table_name} SET {insert_column} = ? WHERE {select_column} = ?',(serialize_value(insert_data),select_value,))