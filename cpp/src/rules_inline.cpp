#include "diskcore/rules_inline.hpp"
#include <algorithm>

namespace diskcore {

RulesMatcher::RulesMatcher() {
    // Standard rule IDs:
    // 1: node_modules
    // 2: target (Cargo)
    // 3: .build / build
    // 4: DerivedData
    // 5: Caches
    // 6: .Trash
    // 7: Installers (.dmg, .pkg, .iso)
    // 8: Python cache (__pycache__, .pytest_cache, .mypy_cache, .venv)
    // 9: Pods
    dir_name_rules_["node_modules"] = 1;
    dir_name_rules_["DerivedData"] = 4;
    dir_name_rules_["Caches"] = 5;
    dir_name_rules_[".Trash"] = 6;
    dir_name_rules_["__pycache__"] = 8;
    dir_name_rules_[".pytest_cache"] = 8;
    dir_name_rules_[".mypy_cache"] = 8;
    dir_name_rules_["Pods"] = 9;

    extension_rules_[".dmg"] = 7;
    extension_rules_[".pkg"] = 7;
    extension_rules_[".iso"] = 7;
    extension_rules_[".ipsw"] = 7;
    extension_rules_[".xip"] = 7;
}

uint16_t RulesMatcher::match_dir(const std::string& name,
                                 const std::unordered_set<std::string>& sibling_names,
                                 const std::unordered_set<std::string>& child_names,
                                 const std::string& full_path) const {
    // 1. Direct directory name lookup
    auto it = dir_name_rules_.find(name);
    if (it != dir_name_rules_.end()) {
        if (name == "node_modules") {
            // Sibling package.json or child .package-lock.json / just node_modules
            return 1;
        }
        return it->second;
    }

    // 2. target (Rust Cargo)
    if (name == "target" && (sibling_names.count("Cargo.toml") > 0 || child_names.count("CACHEDIR.TAG") > 0)) {
        return 2;
    }

    // 3. CACHEDIR.TAG tag
    if (child_names.count("CACHEDIR.TAG") > 0) {
        return 5; // Generic cache
    }

    // 4. Python venv
    if (child_names.count("pyvenv.cfg") > 0) {
        return 8; // Python environment
    }

    // 5. Common build dirs
    if (name == ".build" || name == "build") {
        if (sibling_names.count("Package.swift") > 0 ||
            sibling_names.count("CMakeLists.txt") > 0 ||
            sibling_names.count("build.gradle") > 0) {
            return 3;
        }
    }

    // 6. Path prefix checks
    if (full_path.find("/Library/Caches") != std::string::npos ||
        full_path.find("/.cache") != std::string::npos) {
        return 5;
    }

    return 0;
}

uint16_t RulesMatcher::match_file(const std::string& name) const {
    size_t dot = name.rfind('.');
    if (dot != std::string::npos) {
        std::string ext = name.substr(dot);
        std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
        auto it = extension_rules_.find(ext);
        if (it != extension_rules_.end()) {
            return it->second;
        }
    }
    return 0;
}

void RulesMatcher::add_custom_rule(uint16_t id, const std::string& name, uint8_t, uint8_t) {
    dir_name_rules_[name] = id;
}

} // namespace diskcore
