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
