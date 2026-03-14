# Automated Farmer – Code-to-Grow Game :>

A programming-driven automation game where players write Python code to control a farmer in a grid-based world. The game is built with a C++ simulation engine, OpenGL rendering, Python scripting, and SQL persistence.

---

## 📦 Requirements

- **CMake** ≥ 3.16
- **C++ Compiler** with C++17 support
- **OpenGL 3.3 Core**
- **Python 3.10+**
- **Git**
- **Pygame
- **Noting that you need pygame installed locally at least for me -JK 

### Libraries (already included in repo)

- GLFW
- GLAD (OpenGL 3.3 Core)
- stb_image

---

## 🔧 How to Build (All Teammates)

From the **project root**:

```bash
mkdir build
cd build
cmake ..
cmake --build .
```

To run the program:

```bash
./automated_farmer

Justin - You can also use the following
cmake --build . --config Release
 .\Release\automated_farmer.exe
```

Clean Rebuild:

```bash
rm -rf build
mkdir build
cd build
cmake ..
cmake --build .
```

## ✅ Build Sanity Check

Your setup is correct if:

- The project builds with no errors
- A window titled **“OpenGL Test”** opens
- The screen clears to a solid color
- The window closes cleanly
