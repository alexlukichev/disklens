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

#include "diskcore/scanner.hpp"
#include <sys/attr.h>
#include <sys/vnode.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <iostream>
#include <unordered_set>

extern "C" {
    void* objc_autoreleasePoolPush(void);
    void objc_autoreleasePoolPop(void* context);
}

namespace diskcore {

namespace {
struct AutoreleasePoolScope {
    void* pool;
    AutoreleasePoolScope() : pool(objc_autoreleasePoolPush()) {}
    ~AutoreleasePoolScope() { if (pool) objc_autoreleasePoolPop(pool); }
};
}

struct AttrBufferHeader {
    uint32_t length;
    attribute_set_t returned;
    attrreference_t name_ref;
    uint32_t err;
    dev_t dev;
    fsobj_type_t obj_type;
    uint64_t file_id;
    struct timespec mtime;
    uint32_t flags;
    uint32_t link_count;
    off_t total_size;
    off_t alloc_size;
} __attribute__((aligned(4), packed));

Scanner::Scanner(NodeStore& store, MountPolicy& mount_policy, RulesMatcher& rules, ErrorRing& errors)
    : store_(store), mount_policy_(mount_policy), rules_(rules), errors_(errors) {}

Scanner::~Scanner() {
    stop_scan();
}

bool Scanner::start_scan(const std::string& root_path, uint64_t file_threshold_bytes, size_t num_threads) {
    stop_scan();

    file_threshold_bytes_ = file_threshold_bytes;
    stop_requested_.store(false);
    bytes_scanned_.store(0);
    items_scanned_.store(0);
    active_workers_.store(0);

    if (!mount_policy_.init(root_path)) {
        errors_.push(root_path, errno, "Failed to initialize mount policy for root");
        return false;
    }

    store_.clear();
    NodeId root_id = store_.allocate_node(kInvalidNodeId, root_path, NodeKind::Directory);
    Node* root_node = store_.get_node(root_id);
    if (root_node) {
        root_node->flags |= NodeFlags::Complete;
    }

    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        normal_queue_.clear();
        focused_queue_.clear();
        normal_queue_.push_back({root_id, root_path, false});
    }

    if (num_threads == 0) {
        unsigned int hw = std::thread::hardware_concurrency();
        num_threads = hw > 0 ? std::min(16u, hw * 2) : 8;
    }

    is_running_.store(true);
    workers_.clear();
    for (size_t i = 0; i < num_threads; ++i) {
        workers_.emplace_back(&Scanner::worker_loop, this, i);
    }
    queue_cv_.notify_all();

    return true;
}

bool Scanner::rescan_subtree(NodeId node_id) {
    Node* node = store_.get_node(node_id);
    if (!node || node->kind != NodeKind::Directory) return false;

    std::string path = store_.get_full_path(node_id);

    // Subtract existing totals from ancestors
    uint64_t curr_alloc = node->total_alloc.load(std::memory_order_relaxed);
    uint64_t curr_logical = node->total_logical.load(std::memory_order_relaxed);
    uint32_t curr_files = node->file_count.load(std::memory_order_relaxed);
    uint32_t curr_dirs = node->dir_count.load(std::memory_order_relaxed);

    store_.add_totals_to_ancestors(node->parent_id,
        -curr_alloc, -curr_logical, -curr_files, -curr_dirs);

    // Reset node
    node->total_alloc.store(0, std::memory_order_relaxed);
    node->total_logical.store(0, std::memory_order_relaxed);
    node->file_count.store(0, std::memory_order_relaxed);
    node->dir_count.store(0, std::memory_order_relaxed);
    node->own_alloc = 0;
    node->own_logical = 0;
    node->children.clear();
    node->flags |= NodeFlags::Rescanning;

    is_running_.store(true);
    if (workers_.empty()) {
        stop_requested_.store(false);
        unsigned int hw = std::thread::hardware_concurrency();
        size_t num_threads = hw > 0 ? std::min(16u, hw * 2) : 8;
        for (size_t i = 0; i < num_threads; ++i) {
            workers_.emplace_back(&Scanner::worker_loop, this, i);
        }
    }

    {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        focused_queue_.push_front({node_id, path, true});
    }
    queue_cv_.notify_all();
    return true;
}

void Scanner::stop_scan() {
    stop_requested_.store(true);
    queue_cv_.notify_all();
    for (auto& w : workers_) {
        if (w.joinable()) {
            w.join();
        }
    }
    workers_.clear();
    is_running_.store(false);
}

bool Scanner::is_running() const {
    return is_running_.load(std::memory_order_relaxed);
}

ScanProgress Scanner::get_progress() const {
    ScanProgress p;
    p.bytes_scanned = bytes_scanned_.load(std::memory_order_relaxed);
    p.items_scanned = items_scanned_.load(std::memory_order_relaxed);
    p.active_workers = active_workers_.load(std::memory_order_relaxed);
    p.errors_count = static_cast<uint32_t>(errors_.total_errors());

    {
        std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(queue_mutex_));
        p.pending_dirs = static_cast<uint32_t>(normal_queue_.size() + focused_queue_.size());
        p.current_path = current_path_;
    }

    p.is_complete = !is_running_.load(std::memory_order_relaxed);
    return p;
}

void Scanner::worker_loop(size_t worker_id) {
    constexpr size_t kBufSize = 64 * 1024;
    alignas(8) std::vector<char> buffer(kBufSize);

    while (!stop_requested_.load(std::memory_order_relaxed)) {
        ScanTask task;
        {
            std::unique_lock<std::mutex> lock(queue_mutex_);
            queue_cv_.wait_for(lock, std::chrono::milliseconds(50), [&] {
                return stop_requested_.load(std::memory_order_relaxed) ||
                       !focused_queue_.empty() || !normal_queue_.empty();
            });

            if (stop_requested_.load(std::memory_order_relaxed)) break;

            if (!focused_queue_.empty()) {
                task = focused_queue_.front();
                focused_queue_.pop_front();
                current_path_ = task.path;
                active_workers_.fetch_add(1, std::memory_order_relaxed);
            } else if (!normal_queue_.empty()) {
                task = normal_queue_.front();
                normal_queue_.pop_front();
                current_path_ = task.path;
                active_workers_.fetch_add(1, std::memory_order_relaxed);
            } else {
                // If both queues are empty AND no other worker is active, scanning is complete
                if (active_workers_.load(std::memory_order_relaxed) == 0) {
                    is_running_.store(false);
                }
                continue;
            }
        }

        {
            AutoreleasePoolScope pool_scope;
            scan_directory(task, worker_id, buffer.data(), buffer.size());
        }
        active_workers_.fetch_sub(1, std::memory_order_relaxed);
    }
}

void Scanner::scan_directory(const ScanTask& task, size_t, char* buffer, size_t buf_size) {
    int dir_fd = open(task.path.c_str(), O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK);
    if (dir_fd < 0) {
        errors_.push(task.path, errno, "Failed to open directory");
        Node* node = store_.get_node(task.node_id);
        if (node) {
            node->flags |= NodeFlags::Partial | NodeFlags::Error;
        }
        return;
    }

    // Set up attrlist
    struct attrlist attr_list;
    std::memset(&attr_list, 0, sizeof(attr_list));
    attr_list.bitmapcount = ATTR_BIT_MAP_COUNT;
    attr_list.commonattr = ATTR_CMN_RETURNED_ATTRS | ATTR_CMN_NAME | ATTR_CMN_ERROR |
                           ATTR_CMN_DEVID | ATTR_CMN_OBJTYPE | ATTR_CMN_FILEID |
                           ATTR_CMN_MODTIME | ATTR_CMN_FLAGS;
    attr_list.fileattr = ATTR_FILE_LINKCOUNT | ATTR_FILE_TOTALSIZE | ATTR_FILE_ALLOCSIZE;

    uint64_t dir_alloc_total = 0;
    uint64_t dir_logical_total = 0;
    uint32_t dir_files_count = 0;
    uint32_t dir_subdirs_count = 0;
    uint64_t small_files_alloc = 0;
    uint64_t small_files_logical = 0;
    uint32_t small_files_count = 0;

    std::vector<ScanTask> new_subdirs;

    while (!stop_requested_.load(std::memory_order_relaxed)) {
        int count = getattrlistbulk(dir_fd, &attr_list, buffer, buf_size, FSOPT_PACK_INVAL_ATTRS | FSOPT_NOFOLLOW);
        if (count < 0) {
            errors_.push(task.path, errno, "getattrlistbulk error");
            break;
        }
        if (count == 0) {
            break; // Finished directory
        }

        char* entry_ptr = buffer;
        const char* buffer_end = buffer + buf_size;

        for (int i = 0; i < count; ++i) {
            if (entry_ptr + sizeof(uint32_t) > buffer_end) break;
            uint32_t entry_length = 0;
            std::memcpy(&entry_length, entry_ptr, sizeof(uint32_t));
            if (entry_length < sizeof(uint32_t) || entry_ptr + entry_length > buffer_end) break;

            const char* entry_end = entry_ptr + entry_length;
            if (entry_ptr + 4 + sizeof(attribute_set_t) > entry_end) break;
            attribute_set_t returned;
            std::memcpy(&returned, entry_ptr + 4, sizeof(attribute_set_t));
            char* cursor = entry_ptr + 4 + sizeof(attribute_set_t);

            // Error (ATTR_CMN_ERROR) - kernel places this right after ATTR_CMN_RETURNED_ATTRS
            uint32_t entry_err = 0;
            if (returned.commonattr & ATTR_CMN_ERROR) {
                if (cursor + sizeof(uint32_t) > entry_end) break;
                std::memcpy(&entry_err, cursor, sizeof(uint32_t));
                cursor += sizeof(uint32_t);
            }

            // Name (ATTR_CMN_NAME)
            const char* name_str = "";
            if (returned.commonattr & ATTR_CMN_NAME) {
                if (cursor + sizeof(attrreference_t) > entry_end) break;
                attrreference_t name_ref;
                std::memcpy(&name_ref, cursor, sizeof(attrreference_t));
                char* name_target = cursor + name_ref.attr_dataoffset;
                if (name_target >= entry_ptr && name_target < entry_end) {
                    name_str = name_target;
                }
                cursor += sizeof(attrreference_t);
            }

            // Dev ID (ATTR_CMN_DEVID)
            dev_t dev = 0;
            if (returned.commonattr & ATTR_CMN_DEVID) {
                if (cursor + sizeof(dev_t) > entry_end) break;
                std::memcpy(&dev, cursor, sizeof(dev_t));
                cursor += sizeof(dev_t);
            }

            // Obj Type (ATTR_CMN_OBJTYPE)
            fsobj_type_t obj_type = 0;
            if (returned.commonattr & ATTR_CMN_OBJTYPE) {
                if (cursor + sizeof(fsobj_type_t) > entry_end) break;
                std::memcpy(&obj_type, cursor, sizeof(fsobj_type_t));
                cursor += sizeof(fsobj_type_t);
            }

            // Mod Time (ATTR_CMN_MODTIME - bit 10)
            uint32_t mtime_sec = 0;
            if (returned.commonattr & ATTR_CMN_MODTIME) {
                if (cursor + sizeof(struct timespec) > entry_end) break;
                struct timespec ts;
                std::memcpy(&ts, cursor, sizeof(struct timespec));
                mtime_sec = static_cast<uint32_t>(ts.tv_sec);
                cursor += sizeof(struct timespec);
            }

            // Flags (ATTR_CMN_FLAGS - bit 18)
            uint32_t flags = 0;
            if (returned.commonattr & ATTR_CMN_FLAGS) {
                if (cursor + sizeof(uint32_t) > entry_end) break;
                std::memcpy(&flags, cursor, sizeof(uint32_t));
                cursor += sizeof(uint32_t);
            }

            // File ID (ATTR_CMN_FILEID - bit 25)
            if (returned.commonattr & ATTR_CMN_FILEID) {
                if (cursor + sizeof(uint64_t) > entry_end) break;
                cursor += sizeof(uint64_t);
            }

            // Link count (ATTR_FILE_LINKCOUNT)
            if (returned.fileattr & ATTR_FILE_LINKCOUNT) {
                if (cursor + sizeof(uint32_t) > entry_end) break;
                cursor += sizeof(uint32_t);
            }

            // Total size (logical) (ATTR_FILE_TOTALSIZE)
            off_t total_size = 0;
            if (returned.fileattr & ATTR_FILE_TOTALSIZE) {
                if (cursor + sizeof(off_t) > entry_end) break;
                std::memcpy(&total_size, cursor, sizeof(off_t));
                cursor += sizeof(off_t);
            }

            // Alloc size (ATTR_FILE_ALLOCSIZE)
            off_t alloc_size = 0;
            if (returned.fileattr & ATTR_FILE_ALLOCSIZE) {
                if (cursor + sizeof(off_t) > entry_end) break;
                std::memcpy(&alloc_size, cursor, sizeof(off_t));
                cursor += sizeof(off_t);
            }

            if (name_str[0] == '\0' || std::strcmp(name_str, ".") == 0 || std::strcmp(name_str, "..") == 0) {
                entry_ptr += entry_length;
                continue;
            }

            items_scanned_.fetch_add(1, std::memory_order_relaxed);
            bytes_scanned_.fetch_add(alloc_size, std::memory_order_relaxed);

            std::string child_path = (task.path == "/") ? "/" + std::string(name_str) : task.path + "/" + name_str;

            if (entry_err != 0) {
                errors_.push(child_path, entry_err, "Error reading entry attributes");
            }

            // Check symlink (VDIR vs VLNK vs VREG)
            if (obj_type == VLNK) {
                // Do not follow symlinks!
                NodeId sym_id = store_.allocate_node(task.node_id, name_str, NodeKind::Symlink);
                Node* sn = store_.get_node(sym_id);
                if (sn) {
                    sn->own_alloc = alloc_size;
                    sn->own_logical = total_size;
                    sn->mtime = mtime_sec;
                }
                dir_alloc_total += alloc_size;
                dir_logical_total += total_size;
                dir_files_count += 1;
            } else if (obj_type == VDIR) {
                // Check if mount point or excluded boundary
                if (mount_policy_.is_mount_point(child_path) || !mount_policy_.is_allowed_device(dev)) {
                    NodeId stub_id = store_.allocate_node(task.node_id, name_str, NodeKind::MountStub);
                    Node* mn = store_.get_node(stub_id);
                    if (mn) mn->flags |= NodeFlags::Complete;
                    continue;
                }

                // Check firmlink target duplication
                if (mount_policy_.is_firmlink_target(child_path)) {
                    continue;
                }

                NodeId dir_id = store_.allocate_node(task.node_id, name_str, NodeKind::Directory);
                Node* dn = store_.get_node(dir_id);
                if (dn) {
                    dn->mtime = mtime_sec;
                    dn->rule_id = rules_.match_dir(name_str, {}, {}, child_path);
                    if (flags & SF_DATALESS) dn->flags |= NodeFlags::Dataless | NodeFlags::Complete;
                }
                dir_subdirs_count += 1;
                // Avoid recursing into dataless cloud folders (OneDrive, iCloud Drive, etc.)
                if (!(flags & SF_DATALESS)) {
                    new_subdirs.push_back({dir_id, child_path, task.focused});
                }
            } else {
                // Regular file
                dir_alloc_total += alloc_size;
                dir_logical_total += total_size;
                dir_files_count += 1;

                if (static_cast<uint64_t>(alloc_size) >= file_threshold_bytes_) {
                    NodeId file_id = store_.allocate_node(task.node_id, name_str, NodeKind::File);
                    Node* fn = store_.get_node(file_id);
                    if (fn) {
                        fn->own_alloc = alloc_size;
                        fn->own_logical = total_size;
                        fn->total_alloc.store(alloc_size, std::memory_order_relaxed);
                        fn->total_logical.store(total_size, std::memory_order_relaxed);
                        fn->mtime = mtime_sec;
                        fn->rule_id = rules_.match_file(name_str);
                        if (flags & SF_DATALESS) fn->flags |= NodeFlags::Dataless;
                    }
                } else {
                    small_files_alloc += alloc_size;
                    small_files_logical += total_size;
                    small_files_count += 1;
                }
            }

            entry_ptr += entry_length;
        }
    }

    close(dir_fd);

    // If small files exist, create synthetic node for aggregated view
    if (small_files_count > 0) {
        std::string synth_name = "‹" + std::to_string(small_files_count) + " smaller files›";
        NodeId synth_id = store_.allocate_node(task.node_id, synth_name, NodeKind::SmallFilesAggregate);
        Node* sn = store_.get_node(synth_id);
        if (sn) {
            sn->own_alloc = small_files_alloc;
            sn->own_logical = small_files_logical;
            sn->total_alloc.store(small_files_alloc, std::memory_order_relaxed);
            sn->total_logical.store(small_files_logical, std::memory_order_relaxed);
            sn->file_count.store(small_files_count, std::memory_order_relaxed);
        }
    }

    // Update directory's own sizes and propagate deltas up to all ancestors
    Node* dir_node = store_.get_node(task.node_id);
    if (dir_node) {
        dir_node->own_alloc = dir_alloc_total;
        dir_node->own_logical = dir_logical_total;
        dir_node->flags |= NodeFlags::Complete;
    }

    store_.add_totals_to_ancestors(task.node_id,
        dir_alloc_total, dir_logical_total, dir_files_count, dir_subdirs_count);

    // Push discovered subdirectories into queue
    if (!new_subdirs.empty()) {
        std::lock_guard<std::mutex> lock(queue_mutex_);
        for (const auto& sd : new_subdirs) {
            if (task.focused) {
                focused_queue_.push_back(sd);
            } else {
                normal_queue_.push_back(sd);
            }
        }
        queue_cv_.notify_all();
    }
}

} // namespace diskcore
