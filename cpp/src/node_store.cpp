#include "diskcore/node_store.hpp"
#include <algorithm>

namespace diskcore {

NodeStore::NodeStore() {
    clear();
}

NodeStore::~NodeStore() = default;

void NodeStore::clear() {
    std::unique_lock<std::shared_mutex> lock(mutex_);
    nodes_.clear();
    nodes_.reserve(1000000);
    // Index 0 is invalid/null
    nodes_.push_back(nullptr);
    next_id_.store(1, std::memory_order_relaxed);
}

NodeId NodeStore::allocate_node(NodeId parent_id, const std::string& name, NodeKind kind) {
    auto node = std::make_unique<Node>();
    node->name = name;
    node->parent_id = parent_id;
    node->kind = kind;

    std::unique_lock<std::shared_mutex> lock(mutex_);
    NodeId id = static_cast<NodeId>(nodes_.size());
    node->id = id;
    nodes_.push_back(std::move(node));

    if (parent_id != kInvalidNodeId && parent_id < nodes_.size() && nodes_[parent_id]) {
        nodes_[parent_id]->children.push_back(id);
    }
    return id;
}

Node* NodeStore::get_node(NodeId id) {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    if (id > 0 && id < nodes_.size()) {
        return nodes_[id].get();
    }
    return nullptr;
}

const Node* NodeStore::get_node(NodeId id) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    if (id > 0 && id < nodes_.size()) {
        return nodes_[id].get();
    }
    return nullptr;
}

NodeDisplayInfo NodeStore::get_display_info(NodeId id) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    NodeDisplayInfo info;
    if (id == 0 || id >= nodes_.size() || !nodes_[id]) {
        return info;
    }
    const auto& n = *nodes_[id];
    info.id = n.id;
    info.parent_id = n.parent_id;
    info.name = n.name;
    info.kind = static_cast<uint8_t>(n.kind);
    info.flags = n.flags;
    info.rule_id = n.rule_id;
    info.total_alloc = n.total_alloc.load(std::memory_order_relaxed);
    info.total_logical = n.total_logical.load(std::memory_order_relaxed);
    info.own_alloc = n.own_alloc;
    info.own_logical = n.own_logical;
    info.file_count = n.file_count.load(std::memory_order_relaxed);
    info.dir_count = n.dir_count.load(std::memory_order_relaxed);
    info.mtime = n.mtime;
    return info;
}

std::string NodeStore::get_full_path(NodeId id) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    if (id == 0 || id >= nodes_.size() || !nodes_[id]) {
        return "/";
    }

    std::vector<std::string> parts;
    NodeId curr = id;
    while (curr != kInvalidNodeId && curr < nodes_.size() && nodes_[curr]) {
        if (!nodes_[curr]->name.empty() && nodes_[curr]->name != "/") {
            parts.push_back(nodes_[curr]->name);
        }
        curr = nodes_[curr]->parent_id;
    }
    std::reverse(parts.begin(), parts.end());
    std::string path;
    for (const auto& p : parts) {
        if (p.front() == '/') {
            path += p;
        } else {
            if (path.empty() || path.back() != '/') path += "/";
            path += p;
        }
    }
    return path.empty() ? "/" : path;
}

std::vector<NodeId> NodeStore::get_sorted_children(NodeId id, SortKey key, bool descending) const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    if (id == 0 || id >= nodes_.size() || !nodes_[id]) {
        return {};
    }

    std::vector<NodeId> result = nodes_[id]->children;
    std::sort(result.begin(), result.end(), [&](NodeId a_id, NodeId b_id) {
        if (a_id == b_id) return false;
        bool a_valid = (a_id > 0 && a_id < nodes_.size() && nodes_[a_id]);
        bool b_valid = (b_id > 0 && b_id < nodes_.size() && nodes_[b_id]);
        if (!a_valid || !b_valid) {
            return a_valid && !b_valid;
        }

        const auto& a = *nodes_[a_id];
        const auto& b = *nodes_[b_id];

        switch (key) {
            case SortKey::SizeAlloc: {
                auto va = a.total_alloc.load(std::memory_order_relaxed);
                auto vb = b.total_alloc.load(std::memory_order_relaxed);
                if (va != vb) return descending ? (va > vb) : (va < vb);
                break;
            }
            case SortKey::SizeLogical: {
                auto va = a.total_logical.load(std::memory_order_relaxed);
                auto vb = b.total_logical.load(std::memory_order_relaxed);
                if (va != vb) return descending ? (va > vb) : (va < vb);
                break;
            }
            case SortKey::Name: {
                int cmp = strcasecmp(a.name.c_str(), b.name.c_str());
                if (cmp != 0) return descending ? (cmp > 0) : (cmp < 0);
                break;
            }
            case SortKey::Items: {
                auto va = a.file_count.load(std::memory_order_relaxed) + a.dir_count.load(std::memory_order_relaxed);
                auto vb = b.file_count.load(std::memory_order_relaxed) + b.dir_count.load(std::memory_order_relaxed);
                if (va != vb) return descending ? (va > vb) : (va < vb);
                break;
            }
            case SortKey::Modified: {
                if (a.mtime != b.mtime) return descending ? (a.mtime > b.mtime) : (a.mtime < b.mtime);
                break;
            }
        }

        return descending ? (a.id > b.id) : (a.id < b.id);
    });

    return result;
}

void NodeStore::add_totals_to_ancestors(NodeId id, uint64_t alloc_delta, uint64_t logical_delta, uint32_t files_delta, uint32_t dirs_delta) {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    NodeId curr = id;
    while (curr != kInvalidNodeId && curr < nodes_.size() && nodes_[curr]) {
        nodes_[curr]->total_alloc.fetch_add(alloc_delta, std::memory_order_relaxed);
        nodes_[curr]->total_logical.fetch_add(logical_delta, std::memory_order_relaxed);
        nodes_[curr]->file_count.fetch_add(files_delta, std::memory_order_relaxed);
        nodes_[curr]->dir_count.fetch_add(dirs_delta, std::memory_order_relaxed);
        curr = nodes_[curr]->parent_id;
    }
}

size_t NodeStore::size() const {
    std::shared_lock<std::shared_mutex> lock(mutex_);
    return nodes_.size() > 0 ? nodes_.size() - 1 : 0;
}

} // namespace diskcore
