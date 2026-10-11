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

#include "diskcore/errors.hpp"
#include <chrono>

namespace diskcore {

ErrorRing::ErrorRing(size_t max_size) : max_size_(max_size) {}

void ErrorRing::push(const std::string& path, int error_number, const std::string& message) {
    auto now = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();

    std::lock_guard<std::mutex> lock(mutex_);
    if (records_.size() >= max_size_) {
        records_.pop_front();
    }
    records_.push_back({path, error_number, message, static_cast<uint64_t>(now)});
    count_.fetch_add(1, std::memory_order_relaxed);
}

std::vector<ErrorRecord> ErrorRing::drain(size_t max_records) {
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<ErrorRecord> result;
    size_t to_fetch = std::min(max_records, records_.size());
    result.reserve(to_fetch);
    for (size_t i = 0; i < to_fetch; ++i) {
        result.push_back(std::move(records_.front()));
        records_.pop_front();
    }
    return result;
}

} // namespace diskcore
