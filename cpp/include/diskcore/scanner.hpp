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
#include "diskcore/node_store.hpp"
#include "diskcore/mount_policy.hpp"
#include "diskcore/rules_inline.hpp"
#include "diskcore/errors.hpp"
#include <thread>
#include <atomic>
#include <deque>
#include <mutex>
#include <condition_variable>

namespace diskcore {

class Scanner {
public:
    Scanner(NodeStore& store, MountPolicy& mount_policy, RulesMatcher& rules, ErrorRing& errors);
    ~Scanner();

    bool start_scan(const std::string& root_path, uint64_t file_threshold_bytes, size_t num_threads = 0);
    bool rescan_subtree(NodeId node_id);
    void stop_scan();

    ScanProgress get_progress() const;
    bool is_running() const;

private:
    struct ScanTask {
        NodeId node_id;
        std::string path;
        bool focused = false;
    };

    void worker_loop(size_t worker_id);
    void scan_directory(const ScanTask& task, size_t worker_id, char* buffer, size_t buf_size);

    NodeStore& store_;
    MountPolicy& mount_policy_;
    RulesMatcher& rules_;
    ErrorRing& errors_;

    std::atomic<bool> stop_requested_{false};
    std::atomic<bool> is_running_{false};
    std::atomic<uint32_t> active_workers_{0};
    std::atomic<uint64_t> bytes_scanned_{0};
    std::atomic<uint64_t> items_scanned_{0};

    uint64_t file_threshold_bytes_ = 1024 * 1024; // 1 MB default

    std::deque<ScanTask> normal_queue_;
    std::deque<ScanTask> focused_queue_;
    std::string current_path_;
    std::mutex queue_mutex_;
    std::condition_variable queue_cv_;

    std::vector<std::thread> workers_;
};

} // namespace diskcore
