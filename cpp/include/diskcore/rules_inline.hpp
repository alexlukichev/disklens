// Copyright 2026 Alexander Lukichev
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <unordered_set>

namespace diskcore {

struct InlineRule {
    uint16_t id = 0;
    std::string rule_name;
    uint8_t category = 0;
    uint8_t safety = 0; // 0=safe, 1=review, 2=danger
};

class RulesMatcher {
public:
    RulesMatcher();

    // Check directory name + sibling files (e.g. node_modules next to package.json)
    uint16_t match_dir(const std::string& name,
                       const std::unordered_set<std::string>& sibling_names,
                       const std::unordered_set<std::string>& child_names,
                       const std::string& full_path) const;

    // Check file extension (e.g. .dmg, .pkg, .iso)
    uint16_t match_file(const std::string& name) const;

    void add_custom_rule(uint16_t id, const std::string& name, uint8_t cat, uint8_t safety);

private:
    std::unordered_map<std::string, uint16_t> dir_name_rules_;
    std::unordered_map<std::string, uint16_t> extension_rules_;
    std::vector<std::pair<std::string, uint16_t>> path_prefix_rules_;
};

} // namespace diskcore
