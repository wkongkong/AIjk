import json
from typing import Any, Dict


def parse_json_string(json_str: str) -> Dict[str, Any]:
    """解析JSON字符串"""
    if not json_str or json_str == '{}':
        return {}
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return {}


def is_empty_value(value: Any) -> bool:
    """判断值是否为空"""
    if pd.isna(value):
        return True
    if isinstance(value, str) and value.strip() == '':
        return True
    return False


import pandas as pd
