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
#include <string>
#include <vector>
#include <unordered_set>
#include <sys/types.h>

namespace diskcore {

class MountPolicy {
public:
    MountPolicy();

    bool init(const std::string& root_path);

    bool is_allowed_device(dev_t dev) const;
    bool is_mount_point(const std::string& path) const;
    bool is_firmlink_target(const std::string& path) const;

    dev_t root_device() const { return root_dev_; }

private:
    dev_t root_dev_ = 0;
    std::unordered_set<dev_t> allowed_devices_;
    std::unordered_set<std::string> mount_points_;
    std::unordered_set<std::string> firmlink_targets_;
};

} // namespace diskcore
