#include <iostream>
#include <vector>
#include <algorithm>
#include "Grid.hpp"

// IMPORTANT: glad must be included before glfw
//gives you access to openGL functions.
#include <glad/glad.h>
//used to create windows and openGL context
#include <GLFW/glfw3.h>

// Callback for window resize, this function is called every time window is resized.
// using glfwSetFramebufferSizeCallback
void framebuffer_size_callback(GLFWwindow* window, int width, int height)
{
    //first 0 is x and second 0 is y. so we start at bottom left corner of the viewport.
    //then we have width and height which specify how wide rendering area is in  pixel and how tall
    //starting from the bottom left.
    //glViewport define where openGL draw its output so without it, it would draw
    //with the old viewport size.
    glViewport(0, 0, width, height);
}

//this function takes the source code and shader type, compiles and returns the shader
//GLuint is the final linked shader program ID 
static GLuint compileShader(GLenum type, const char* src)
{
    GLuint s = glCreateShader(type);
    glShaderSource(s, 1, &src, nullptr);
    glCompileShader(s);

    GLint ok = 0;
    glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
    //if there is an error throw error msg
    if (!ok) {
        char log[1024];
        glGetShaderInfoLog(s, sizeof(log), nullptr, log);
        std::cerr << "Shader compile error:\n" << log << "\n";
    }
    return s;
}
//this function links all the shader together to display things
static GLuint makeProgram(const char* vsSrc, const char* fsSrc)
{
    GLuint vs = compileShader(GL_VERTEX_SHADER, vsSrc);
    GLuint fs = compileShader(GL_FRAGMENT_SHADER, fsSrc);

    GLuint p = glCreateProgram();
    glAttachShader(p, vs);
    glAttachShader(p, fs);
    glLinkProgram(p);

    GLint ok = 0;
    glGetProgramiv(p, GL_LINK_STATUS, &ok);
    //throws error msg
    if (!ok) {
        char log[1024];
        glGetProgramInfoLog(p, sizeof(log), nullptr, log);
        std::cerr << "Program link error:\n" << log << "\n";
    }

    glDeleteShader(vs);
    glDeleteShader(fs);
    return p;
}

// Vertex format: x, y, r, g, b
static void pushTri(std::vector<float>& v,
                    float x0, float y0,
                    float x1, float y1,
                    float x2, float y2,
                    float r, float g, float b)
{
    v.insert(v.end(), { x0, y0, r, g, b });
    v.insert(v.end(), { x1, y1, r, g, b });
    v.insert(v.end(), { x2, y2, r, g, b });
}

static void pushQuad(std::vector<float>& v,
                     float left, float top,
                     float right, float bottom,
                     float r, float g, float b)
{
    // two triangles
    pushTri(v, left,  top,    right, top,    right, bottom, r, g, b);
    pushTri(v, left,  top,    right, bottom, left,  bottom, r, g, b);
}

//we will symbolize what kind of crop is being grown through colors for now
struct RGB { float r, g, b; };

static RGB colorForTile(const Tile& t)
{
    // Pick colors based on tile type/state (tweak freely)
    switch (t.type) {
    case TileType::EMPTY: return { 0.20f, 0.30f, 0.28f }; //if the type ie empty show dark green
    case TileType::SOIL:  return { 0.35f, 0.25f, 0.15f }; //if it is soil, show brown
    case TileType::CROP://if it is a crop to a switch statement to see how much the crop has grown
        switch (t.cropstate) {
        case CropState::EMPTY:   return { 0.20f, 0.45f, 0.20f };
        case CropState::PLANTED: return { 0.20f, 0.60f, 0.25f };
        case CropState::GROWN:   return { 0.35f, 0.80f, 0.35f };
        }
    }
    return { 0.25f, 0.25f, 0.25f };
}

static void buildMeshesFromGrid(
    const Grid& grid,
    int farmerX, int farmerY,
    std::vector<float>& outTileVerts,
    std::vector<float>& outBorderVerts,
    std::vector<float>& outFarmerVerts)
{
    outTileVerts.clear();
    outBorderVerts.clear();
    outFarmerVerts.clear();

    const int W = grid.getGridWidth();
    const int H = grid.getGridHeight();

    //layout for the gird, set to be centered
    const float gridSize = 1.4f;   //height and width for tiles can be adjusted -JK
    const float gap = 0.0f;       //gap between the tiles, set to 0 for no gap - JK
    const float cellSize = (gridSize - gap * (W - 1)) / W;

    const float startX = -gridSize / 2.0f;
    const float startY =  gridSize / 2.0f; //the player will start on the top left by default

    // border thickness in NDC units (thin rectangles)
    const float borderT = 0.01f;
    const RGB borderC{ 0.05f, 0.05f, 0.05f };

    outTileVerts.reserve(W * H * 6 * 5);
    outBorderVerts.reserve(W * H * 4 * 6 * 5); // 4 skinny quads per tile

    for (int y = 0; y < H; y++) {
        for (int x = 0; x < W; x++) {

            float left   = startX + x * (cellSize + gap);
            float top    = startY - y * (cellSize + gap);
            float right  = left + cellSize;
            float bottom = top  - cellSize;

            const Tile& t = grid.getTile(x, y);
            RGB c = colorForTile(t);

            // Slight checker variation so you can see tiles easier even if same type
            if ((x + y) % 2 == 0) { c.r += 0.02f; c.g += 0.02f; c.b += 0.02f; }

            // Tile fill
            pushQuad(outTileVerts, left, top, right, bottom, c.r, c.g, c.b);

            // Borders (4 skinny quads)
            // Top
            pushQuad(outBorderVerts,
                     left, top, right, top - borderT,
                     borderC.r, borderC.g, borderC.b);

            // Bottom
            pushQuad(outBorderVerts,
                     left, bottom + borderT, right, bottom,
                     borderC.r, borderC.g, borderC.b);

            // Left
            pushQuad(outBorderVerts,
                     left, top, left + borderT, bottom,
                     borderC.r, borderC.g, borderC.b);

            // Right
            pushQuad(outBorderVerts,
                     right - borderT, top, right, bottom,
                     borderC.r, borderC.g, borderC.b);
        }
    }

    // Farmer marker (small quad inside its tile)
    farmerX = std::clamp(farmerX, 0, W - 1);
    farmerY = std::clamp(farmerY, 0, H - 1);

    float fLeft   = startX + farmerX * (cellSize + gap);
    float fTop    = startY - farmerY * (cellSize + gap);
    float fRight  = fLeft + cellSize;
    float fBottom = fTop  - cellSize;

    const float inset = 0.06f;
    fLeft += inset; fRight -= inset;
    fTop  -= inset; fBottom += inset;

    pushQuad(outFarmerVerts, fLeft, fTop, fRight, fBottom, 0.35f, 0.75f, 0.40f);
}

int main()
{
    //start GLFW library which must be called before using any GLFW functions.
    if (!glfwInit())
    {
        std::cerr << "Failed to initialize GLFW\n";
        return -1;
    }

    //Tell GLFW which OpenGL version we want before creating the window
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    //core profile has modern openGL and no deprecated functions
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);

    //on macOS, must set GLFW_OPENGL_FORWARD_COMPAT to be true for core profile >=3
    //so it doesn't allow deprecated functions at all.
#ifdef __APPLE__
    glfwWindowHint(GLFW_OPENGL_FORWARD_COMPAT, GL_TRUE);
#endif

    //Create window of size 800x600 and title "Automated-Farmer"
    GLFWwindow* window = glfwCreateWindow(800, 600, "Automated-Farmer", nullptr, nullptr);
    //if failed to create the window.
    if (!window)
    {
        std::cerr << "Failed to create GLFW window\n";
        glfwTerminate();
        return -1;
    }

    //tells GLFW that the openGL commands you run should affect this window's context(store everything openGL needs to draw like resources, state, etc)
    glfwMakeContextCurrent(window);

    //Load OpenGL functions using GLAD
    if (!gladLoadGLLoader((GLADloadproc)glfwGetProcAddress))
    {
        std::cerr << "Failed to initialize GLAD\n";
        return -1;
    }

    //Set viewport.
    glViewport(0, 0, 800, 600);
    //register a callback function that GLFW calls every time the window is resized.
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

//creating shader program
    const char* vsSrc = R"(
        #version 330 core
        layout(location = 0) in vec2 aPos;
        layout(location = 1) in vec3 aColor;
        out vec3 vColor;
        void main() {
            vColor = aColor;
            gl_Position = vec4(aPos, 0.0, 1.0);
        }
    )";

    const char* fsSrc = R"(
        #version 330 core
        in vec3 vColor;
        out vec4 FragColor;
        void main() {
            FragColor = vec4(vColor, 1.0);
        }
    )";

    GLuint program = makeProgram(vsSrc, fsSrc);

    //creating one viewport
    GLuint vao = 0, vbo = 0;
    glGenVertexArrays(1, &vao);
    glGenBuffers(1, &vbo);

    glBindVertexArray(vao);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);

    // Set up attributes once
    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 5 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 5 * sizeof(float), (void*)(2 * sizeof(float)));
    glEnableVertexAttribArray(1);

    glBindVertexArray(0);

//creating our 3x3 grid
    Grid grid(3, 3);

    //showing tiles with different colors
    grid.getTile(1, 1).type = TileType::SOIL;
    grid.getTile(2, 0).type = TileType::CROP;
    grid.getTile(2, 0).cropstate = CropState::PLANTED;

    int farmerX = 0;
    int farmerY = 0;

    bool wPrev = false, aPrev = false, sPrev = false, dPrev = false;
    std::vector<float> tileVerts;
    std::vector<float> borderVerts;
    std::vector<float> farmerVerts;

//while the window is open
    while (!glfwWindowShouldClose(window))
    {
        //if input key for the window is pressed, we close the window.
        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            glfwSetWindowShouldClose(window, true);

        //movement system using WASD inputs
        bool w = glfwGetKey(window, GLFW_KEY_W) == GLFW_PRESS;
        bool a = glfwGetKey(window, GLFW_KEY_A) == GLFW_PRESS;
        bool s = glfwGetKey(window, GLFW_KEY_S) == GLFW_PRESS;
        bool d = glfwGetKey(window, GLFW_KEY_D) == GLFW_PRESS;

        if (w && !wPrev) farmerY = std::max(0, farmerY - 1);
        if (s && !sPrev) farmerY = std::min(grid.getGridHeight() - 1, farmerY + 1);
        if (a && !aPrev) farmerX = std::max(0, farmerX - 1);
        if (d && !dPrev) farmerX = std::min(grid.getGridWidth() - 1, farmerX + 1);

        wPrev = w; aPrev = a; sPrev = s; dPrev = d;

        //sets the background color to be teal
        glClearColor(0.1f, 0.2f, 0.25f, 1.0f);
        //fill framebuffer with the color you set with clearcolor 
        glClear(GL_COLOR_BUFFER_BIT);

        glUseProgram(program);

        buildMeshesFromGrid(grid, farmerX, farmerY, tileVerts, borderVerts, farmerVerts);

        glBindVertexArray(vao);
        glBindBuffer(GL_ARRAY_BUFFER, vbo);

        //draw tiles
        glBufferData(GL_ARRAY_BUFFER, tileVerts.size() * sizeof(float), tileVerts.data(), GL_DYNAMIC_DRAW);
        glDrawArrays(GL_TRIANGLES, 0, (GLsizei)(tileVerts.size() / 5));

        //draw borders (skinny quads)
        glBufferData(GL_ARRAY_BUFFER, borderVerts.size() * sizeof(float), borderVerts.data(), GL_DYNAMIC_DRAW);
        glDrawArrays(GL_TRIANGLES, 0, (GLsizei)(borderVerts.size() / 5));

        //draw farmer marker
        glBufferData(GL_ARRAY_BUFFER, farmerVerts.size() * sizeof(float), farmerVerts.data(), GL_DYNAMIC_DRAW);
        glDrawArrays(GL_TRIANGLES, 0, (GLsizei)(farmerVerts.size() / 5));

        glBindVertexArray(0);

        //every frame, swap front and back buffer
        glfwSwapBuffers(window);
        //process all pending event from operating system like close requestkeyboard input
        glfwPollEvents();
    }

    //cleaning up
    glDeleteBuffers(1, &vbo);
    glDeleteVertexArrays(1, &vao);
    glDeleteProgram(program);

    //close all GLFW windows and free resources allocated by GLFW
    glfwTerminate();
    return 0;
}