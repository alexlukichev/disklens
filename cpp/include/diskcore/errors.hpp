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
#include <deque>

namespace diskcore {

class ErrorRing {
public:
    explicit ErrorRing(size_t max_size = 50000);

    void push(const std::string& path, int error_number, const std::string& message);
    std::vector<ErrorRecord> drain(size_t max_records = 500);
    size_t total_errors() const { return count_.load(std::memory_order_relaxed); }

private:
    size_t max_size_;
    mutable std::mutex mutex_;
    std::deque<ErrorRecord> records_;
    std::atomic<size_t> count_{0};
};

} // namespace diskcore
