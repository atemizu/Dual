# Copyright 2026 Dual contributors.
# Created on 2026-10-24. Licensed under GPL-3.0; see the LICENSE file.
#
# Builds dual-translate-host with llama.cpp linked in statically:
#   cmake -S . -B out -DLLAMA_SOURCE=<llama.cpp checkout> -DCMAKE_BUILD_TYPE=Release
#   cmake --build out --target dual-translate-host

cmake_minimum_required(VERSION 3.20)
project(dual_translate_host C CXX)

set(LLAMA_SOURCE "" CACHE PATH "llama.cpp source checkout")
if(NOT EXISTS "${LLAMA_SOURCE}/include/llama.h")
  message(FATAL_ERROR "Set LLAMA_SOURCE to a llama.cpp checkout")
endif()

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_COMMON OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TESTS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_SERVER OFF CACHE BOOL "" FORCE)
set(LLAMA_BUILD_APP OFF CACHE BOOL "" FORCE)
set(LLAMA_OPENSSL OFF CACHE BOOL "" FORCE)
# Runs on any machine of the architecture, not only the one that built it.
set(GGML_NATIVE OFF CACHE BOOL "" FORCE)
if(APPLE)
  set(GGML_METAL ON CACHE BOOL "" FORCE)
  set(GGML_METAL_EMBED_LIBRARY ON CACHE BOOL "" FORCE)
  # Accelerate's BLAS needs macOS 13.3, Dual 13.0; Metal does the work anyway.
  set(GGML_BLAS OFF CACHE BOOL "" FORCE)
endif()
add_subdirectory("${LLAMA_SOURCE}" llama EXCLUDE_FROM_ALL)

find_package(Threads REQUIRED)
add_executable(dual-translate-host dual_translate_host.cc)
target_include_directories(dual-translate-host PRIVATE "${LLAMA_SOURCE}/vendor")
target_link_libraries(dual-translate-host PRIVATE llama Threads::Threads ${CMAKE_DL_LIBS})
