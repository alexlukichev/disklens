# Copyright 2026 Alexander Lukichev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

cmake_minimum_required(VERSION 3.20)
project(disklens_core LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_OSX_DEPLOYMENT_TARGET "13.0" CACHE STRING "macOS deployment target")

find_package(Python 3.10 COMPONENTS Interpreter Development.Module REQUIRED)
find_package(nanobind CONFIG REQUIRED)

nanobind_add_module(diskcore
    cpp/bindings.cpp
    cpp/src/session.cpp
    cpp/src/scanner.cpp
    cpp/src/node_store.cpp
    cpp/src/mount_policy.cpp
    cpp/src/rules_inline.cpp
    cpp/src/errors.cpp
)

target_include_directories(diskcore PRIVATE cpp/include)

target_compile_options(diskcore PRIVATE
    -Wall -Wextra -Wpedantic
    -O3
)

target_link_libraries(diskcore PRIVATE
    "-framework CoreServices"
)

# Output library into disklens/ package directory
install(TARGETS diskcore DESTINATION disklens)
