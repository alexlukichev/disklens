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
#include "diskcore/types.hpp"
#include <vector>
#include <string>
#include <mutex>
#include <shared_mutex>
#include <unordered_map>

namespace diskcore {

struct Node {
    NodeId id = 0;
    NodeId parent_id = 0;
    std::string name;
    NodeKind kind = NodeKind::Directory;
    uint16_t flags = 0;
    uint16_t rule_id = 0;
    
    uint64_t own_alloc = 0;
    uint64_t own_logical = 0;
    std::atomic<uint64_t> total_alloc{0};
    std::atomic<uint64_t> total_logical{0};
    std::atomic<uint32_t> file_count{0};
    std::atomic<uint32_t> dir_count{0};
    uint32_t mtime = 0;

    std::vector<NodeId> children;
};

class NodeStore {
public:
    NodeStore();
    ~NodeStore();

    void clear();

    NodeId allocate_node(NodeId parent_id, const std::string& name, NodeKind kind);
    
    Node* get_node(NodeId id);
    const Node* get_node(NodeId id) const;

    NodeDisplayInfo get_display_info(NodeId id) const;
    std::string get_full_path(NodeId id) const;

    std::vector<NodeId> get_sorted_children(NodeId id, SortKey key, bool descending) const;

    void add_totals_to_ancestors(NodeId id, uint64_t alloc_delta, uint64_t logical_delta, uint32_t files_delta, uint32_t dirs_delta);

    size_t size() const;

private:
    mutable std::shared_mutex mutex_;
    std::vector<std::unique_ptr<Node>> nodes_;
    std::atomic<NodeId> next_id_{1};
};

} // namespace diskcore
