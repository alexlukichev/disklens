#include "diskcore/mount_policy.hpp"
#include <sys/param.h>
#include <sys/ucred.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <fstream>
#include <cstring>
#include <iostream>

namespace diskcore {

MountPolicy::MountPolicy() = default;

bool MountPolicy::init(const std::string& root_path) {
    allowed_devices_.clear();
    mount_points_.clear();
    firmlink_targets_.clear();

    struct stat st;
    if (stat(root_path.c_str(), &st) != 0) {
        return false;
    }
    root_dev_ = st.st_dev;
    allowed_devices_.insert(root_dev_);

    // Enumerate mount points
    struct statfs* mounts = nullptr;
    int count = getmntinfo(&mounts, MNT_NOWAIT);
    if (count > 0 && mounts != nullptr) {
        std::string root_mnt_from;
        for (int i = 0; i < count; ++i) {
            if (mounts[i].f_fsid.val[0] == static_cast<int32_t>(root_dev_) ||
                std::strcmp(mounts[i].f_mntonname, root_path.c_str()) == 0) {
                root_mnt_from = mounts[i].f_mntfromname;
                break;
            }
        }

        // On macOS APFS, / and /System/Volumes/Data share the same container disk (e.g., /dev/disk1s5s1 and /dev/disk1s1)
        std::string container_prefix;
        if (root_mnt_from.rfind("/dev/disk", 0) == 0) {
            size_t s_pos = root_mnt_from.find('s', 9);
            if (s_pos != std::string::npos) {
                container_prefix = root_mnt_from.substr(0, s_pos); // e.g. "/dev/disk1"
            }
        }

        for (int i = 0; i < count; ++i) {
            std::string mnt_on = mounts[i].f_mntonname;
            std::string mnt_from = mounts[i].f_mntfromname;

            // If root is "/", allow companion APFS volumes in same container (System & Data)
            if (root_path == "/" && !container_prefix.empty() && mnt_from.rfind(container_prefix, 0) == 0) {
                struct stat mnt_st;
                if (stat(mnt_on.c_str(), &mnt_st) == 0) {
                    allowed_devices_.insert(mnt_st.st_dev);
                }
            } else if (mnt_on != root_path) {
                mount_points_.insert(mnt_on);
            }
        }
    }

    // Read macOS firmlinks list (/usr/share/firmlinks)
    std::ifstream firmlinks_file("/usr/share/firmlinks");
    if (firmlinks_file.is_open()) {
        std::string line;
        while (std::getline(firmlinks_file, line)) {
            if (line.empty() || line[0] == '#') continue;
            size_t tab = line.find('\t');
            if (tab != std::string::npos) {
                std::string target = line.substr(tab + 1);
                firmlink_targets_.insert(target);
            }
        }
    }

    return true;
}

bool MountPolicy::is_allowed_device(dev_t dev) const {
    return allowed_devices_.find(dev) != allowed_devices_.end();
}

bool MountPolicy::is_mount_point(const std::string& path) const {
    return mount_points_.find(path) != mount_points_.end();
}

bool MountPolicy::is_firmlink_target(const std::string& path) const {
    return firmlink_targets_.find(path) != firmlink_targets_.end();
}

} // namespace diskcore
