#include "diskcore/session.hpp"

namespace diskcore {

Session::Session() : scanner_(store_, mount_policy_, rules_, errors_) {}

Session::~Session() {
    stop_scan();
}

bool Session::start_scan(const std::string& root_path, uint64_t file_threshold_bytes, size_t num_threads) {
    return scanner_.start_scan(root_path, file_threshold_bytes, num_threads);
}

bool Session::rescan_subtree(NodeId node_id) {
    return scanner_.rescan_subtree(node_id);
}

void Session::stop_scan() {
    scanner_.stop_scan();
}

ScanProgress Session::get_progress() const {
    return scanner_.get_progress();
}

bool Session::is_running() const {
    return scanner_.is_running();
}

NodeDisplayInfo Session::get_node_info(NodeId node_id) const {
    return store_.get_display_info(node_id);
}

std::string Session::get_full_path(NodeId node_id) const {
    return store_.get_full_path(node_id);
}

std::vector<NodeId> Session::get_sorted_children(NodeId node_id, const std::string& sort_key, bool descending) const {
    SortKey key = SortKey::SizeAlloc;
    if (sort_key == "logical" || sort_key == "size_logical") {
        key = SortKey::SizeLogical;
    } else if (sort_key == "name") {
        key = SortKey::Name;
    } else if (sort_key == "items") {
        key = SortKey::Items;
    } else if (sort_key == "modified" || sort_key == "mtime") {
        key = SortKey::Modified;
    }
    return store_.get_sorted_children(node_id, key, descending);
}

std::vector<ErrorRecord> Session::drain_errors(size_t max_count) {
    return errors_.drain(max_count);
}

size_t Session::total_errors() const {
    return errors_.total_errors();
}

size_t Session::node_count() const {
    return store_.size();
}

} // namespace diskcore
