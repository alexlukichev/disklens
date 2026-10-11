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
#include <cstdint>
#include <string>
#include <vector>
#include <atomic>
#include <memory>

namespace diskcore {

using NodeId = uint32_t;
constexpr NodeId kInvalidNodeId = 0;

enum class NodeKind : uint8_t {
    Directory = 1,
    File = 2,
    Symlink = 3,
    MountStub = 4,
    SmallFilesAggregate = 5
};

struct NodeFlags {
    static constexpr uint16_t Complete       = 1 << 0;
    static constexpr uint16_t Partial        = 1 << 1;
    static constexpr uint16_t Error          = 1 << 2;
    static constexpr uint16_t HardlinkDup    = 1 << 3;
    static constexpr uint16_t Dataless       = 1 << 4;
    static constexpr uint16_t MayShareBlocks = 1 << 5;
    static constexpr uint16_t Rescanning     = 1 << 6;
};

struct NodeDisplayInfo {
    NodeId id = 0;
    NodeId parent_id = 0;
    std::string name;
    std::string full_path;
    uint8_t kind = 0;
    uint16_t flags = 0;
    uint16_t rule_id = 0;
    uint64_t total_alloc = 0;
    uint64_t total_logical = 0;
    uint64_t own_alloc = 0;
    uint64_t own_logical = 0;
    uint32_t file_count = 0;
    uint32_t dir_count = 0;
    uint32_t mtime = 0;
};

struct ScanProgress {
    uint64_t bytes_scanned = 0;
    uint64_t items_scanned = 0;
    uint32_t active_workers = 0;
    uint32_t pending_dirs = 0;
    uint32_t errors_count = 0;
    bool is_complete = false;
    std::string current_path;
};

struct ErrorRecord {
    std::string path;
    int error_number = 0;
    std::string message;
    uint64_t timestamp = 0;
};

enum class SortKey {
    SizeAlloc,
    SizeLogical,
    Name,
    Items,
    Modified
};

} // namespace diskcore
