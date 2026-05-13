cmake_minimum_required(VERSION 3.16)

project(automated_farmer LANGUAGES C CXX)

# Use C++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Create executable
add_executable(automated_farmer
    src/main.cpp
    src/FarmerSprite.cpp        # <-- added
    scripts/Grid.cpp
    scripts/Farmer.cpp
)

# Telling compiler where to find headers
target_include_directories(automated_farmer PRIVATE
    ${CMAKE_SOURCE_DIR}/scripts
    ${CMAKE_SOURCE_DIR}/src     # <-- added
)

# GLFW
add_subdirectory(third_party/glfw)

# GLAD
add_library(glad third_party/glad/src/glad.c)
target_include_directories(glad PUBLIC third_party/glad/include)

# OpenGL (system)
find_package(OpenGL REQUIRED)

# GLM (header-only math for sprite transforms)  <-- added
find_package(glm QUIET)
if(NOT glm_FOUND)
    # Fallback: if GLM isn't system-installed, point to third_party/glm
    target_include_directories(automated_farmer PRIVATE
        ${CMAKE_SOURCE_DIR}/third_party/glm
    )
endif()

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
