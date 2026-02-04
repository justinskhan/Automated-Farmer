# GLFW
add_subdirectory(third_party/glfw)

# GLAD
add_library(glad third_party/glad/src/glad.c)
target_include_directories(glad PUBLIC third_party/glad/include)

# OpenGL (system)
find_package(OpenGL REQUIRED)

# Your app (must exist BEFORE linking)
add_executable(automated_farmer src/main.cpp ...)

# Link everything
target_link_libraries(automated_farmer glfw glad OpenGL::GL)

# stb_image include path
target_include_directories(automated_farmer PRIVATE third_party/stb)

# Linux extras (often needed)
if(UNIX AND NOT APPLE)
  target_link_libraries(automated_farmer dl pthread)
endif()
