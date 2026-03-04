cmake_minimum_required(VERSION 3.16)
project(automated_farmer LANGUAGES C CXX)

# Use C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create executable
add_executable(automated_farmer
    src/main.cpp
    scripts/Grid.cpp
)
# Telling compiler where to find headers
target_include_directories(automated_farmer PRIVATE
    ${CMAKE_SOURCE_DIR}/scripts
)

# GLFW
add_subdirectory(third_party/glfw)

# GLAD
add_library(glad third_party/glad/src/glad.c)
target_include_directories(glad PUBLIC third_party/glad/include)

# OpenGL (system)
find_package(OpenGL REQUIRED)

# Link libraries
target_link_libraries(automated_farmer
    glfw
    glad
    OpenGL::GL
)

# stb_image
target_include_directories(automated_farmer PRIVATE third_party/stb)

# macOS requires this for OpenGL 3.3
if(APPLE)
    target_compile_definitions(automated_farmer PRIVATE GL_SILENCE_DEPRECATION)
endif()
