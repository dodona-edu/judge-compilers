cmake_minimum_required(VERSION 3.13)
project(literals CXX)

set(CMAKE_CXX_STANDARD 17)

# Found through the LLVM_ROOT variable or $LLVM_ROOT/bin on PATH; the image sets no CMAKE_PREFIX_PATH.
find_package(LLVM REQUIRED CONFIG)
llvm_map_components_to_libnames(LLVM_LIBS support)

add_executable(driver driver.cpp submission.cpp)
target_include_directories(driver PRIVATE ${LLVM_INCLUDE_DIRS})
target_link_libraries(driver PRIVATE ${LLVM_LIBS})

configure_file(lit.site.cfg.py.in ${CMAKE_BINARY_DIR}/test/lit.site.cfg.py @ONLY)
