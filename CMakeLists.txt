add_subdirectory(third_party/glfw)
add_library(glad third_party/glad/src/glad.c)
target_include_directories(glad PUBLIC third_party/glad/include)

target_link_libraries(automated_farmer glfw glad)
target_include_directories(automated_farmer PRIVATE third_party/stb)
