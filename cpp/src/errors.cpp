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
