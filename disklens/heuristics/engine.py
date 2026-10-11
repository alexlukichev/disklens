# Copyright 2026 Alexander Lukichev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Heuristics engine to lookup and present cleanup suggestions.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional


class HeuristicsEngine:
    def __init__(self):
        self.rules: Dict[int, Dict[str, Any]] = {}
        self.load_rules()

    def load_rules(self):
        rules_file = Path(__file__).parent / "rules.json"
        if rules_file.exists():
            with open(rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    self.rules[item["id"]] = item

    def get_rule(self, rule_id: int) -> Optional[Dict[str, Any]]:
        return self.rules.get(rule_id)

    def category_name(self, rule_id: int) -> str:
        r = self.get_rule(rule_id)
        return r["category"] if r else "Normal"

    def safety_level(self, rule_id: int) -> str:
        r = self.get_rule(rule_id)
        return r["safety"] if r else "normal"


_ENGINE = None

def get_engine() -> HeuristicsEngine:
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = HeuristicsEngine()
    return _ENGINE
