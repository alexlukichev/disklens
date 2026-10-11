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
