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
#include "diskcore/node_store.hpp"
#include "diskcore/scanner.hpp"
#include "diskcore/mount_policy.hpp"
#include "diskcore/rules_inline.hpp"
#include "diskcore/errors.hpp"
#include <memory>
#include <string>

namespace diskcore {

class Session {
public:
    Session();
    ~Session();

    bool start_scan(const std::string& root_path, uint64_t file_threshold_bytes = 1048576, size_t num_threads = 0);
    bool rescan_subtree(NodeId node_id);
    void stop_scan();

    ScanProgress get_progress() const;
    bool is_running() const;

    NodeDisplayInfo get_node_info(NodeId node_id) const;
    std::string get_full_path(NodeId node_id) const;
    std::vector<NodeId> get_sorted_children(NodeId node_id, const std::string& sort_key, bool descending) const;

    std::vector<ErrorRecord> drain_errors(size_t max_count = 200);
    size_t total_errors() const;

    size_t node_count() const;

private:
    NodeStore store_;
    MountPolicy mount_policy_;
    RulesMatcher rules_;
    ErrorRing errors_;
    Scanner scanner_;
};

} // namespace diskcore
