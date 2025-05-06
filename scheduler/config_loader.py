# parses config.json or other config from database

import json
from typing import Any, Dict


class ConfigLoader:
    @staticmethod
    def load(config_path: str) -> Dict[str, Any]:
        with open(config_path, 'r') as f:
            return json.load(f)