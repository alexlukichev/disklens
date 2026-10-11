#include <nanobind/nanobind.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>
#include "diskcore/session.hpp"

namespace nb = nanobind;
using namespace diskcore;

NB_MODULE(diskcore, m) {
    m.doc() = "High-performance native macOS disk scanner core";

    nb::class_<NodeDisplayInfo>(m, "NodeDisplayInfo")
        .def_ro("id", &NodeDisplayInfo::id)
        .def_ro("parent_id", &NodeDisplayInfo::parent_id)
        .def_prop_ro("name", [](const NodeDisplayInfo& n) {
            return nb::bytes(n.name.data(), n.name.size());
        })
        .def_prop_ro("full_path", [](const NodeDisplayInfo& n) {
            return nb::bytes(n.full_path.data(), n.full_path.size());
        })
        .def_ro("kind", &NodeDisplayInfo::kind)
        .def_ro("flags", &NodeDisplayInfo::flags)
        .def_ro("rule_id", &NodeDisplayInfo::rule_id)
        .def_ro("total_alloc", &NodeDisplayInfo::total_alloc)
        .def_ro("total_logical", &NodeDisplayInfo::total_logical)
        .def_ro("own_alloc", &NodeDisplayInfo::own_alloc)
        .def_ro("own_logical", &NodeDisplayInfo::own_logical)
        .def_ro("file_count", &NodeDisplayInfo::file_count)
        .def_ro("dir_count", &NodeDisplayInfo::dir_count)
        .def_ro("mtime", &NodeDisplayInfo::mtime);

    nb::class_<ScanProgress>(m, "ScanProgress")
        .def_ro("bytes_scanned", &ScanProgress::bytes_scanned)
        .def_ro("items_scanned", &ScanProgress::items_scanned)
        .def_ro("active_workers", &ScanProgress::active_workers)
        .def_ro("pending_dirs", &ScanProgress::pending_dirs)
        .def_ro("errors_count", &ScanProgress::errors_count)
        .def_ro("is_complete", &ScanProgress::is_complete)
        .def_prop_ro("current_path", [](const ScanProgress& p) {
            return nb::bytes(p.current_path.data(), p.current_path.size());
        });

    nb::class_<ErrorRecord>(m, "ErrorRecord")
        .def_prop_ro("path", [](const ErrorRecord& r) {
            return nb::bytes(r.path.data(), r.path.size());
        })
        .def_ro("error_number", &ErrorRecord::error_number)
        .def_prop_ro("message", [](const ErrorRecord& r) {
            return nb::bytes(r.message.data(), r.message.size());
        })
        .def_ro("timestamp", &ErrorRecord::timestamp);

    nb::class_<Session>(m, "Session")
        .def(nb::init<>())
        .def("start_scan", &Session::start_scan,
             nb::arg("root_path"),
             nb::arg("file_threshold_bytes") = 1048576,
             nb::arg("num_threads") = 0,
             nb::call_guard<nb::gil_scoped_release>())
        .def("rescan_subtree", &Session::rescan_subtree,
             nb::arg("node_id"),
             nb::call_guard<nb::gil_scoped_release>())
        .def("stop_scan", &Session::stop_scan,
             nb::call_guard<nb::gil_scoped_release>())
        .def("get_progress", &Session::get_progress)
        .def("is_running", &Session::is_running)
        .def("get_node_info", &Session::get_node_info, nb::arg("node_id"))
        .def("get_full_path", [](const Session& s, NodeId node_id) {
            std::string p = s.get_full_path(node_id);
            return nb::bytes(p.data(), p.size());
        }, nb::arg("node_id"))
        .def("get_sorted_children", &Session::get_sorted_children,
             nb::arg("node_id"),
             nb::arg("sort_key") = "alloc",
             nb::arg("descending") = true)
        .def("drain_errors", &Session::drain_errors, nb::arg("max_count") = 200)
        .def("total_errors", &Session::total_errors)
        .def("node_count", &Session::node_count);
}
