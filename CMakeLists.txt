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
