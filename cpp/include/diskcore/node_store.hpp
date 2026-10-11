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
