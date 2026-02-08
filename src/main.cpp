#include <iostream>
#include "../scripts/Grid.hpp"
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


int main()
{
    Grid testgrid(5,5);
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

    // Minimal shaders for filled squares
    const char* vertexShaderSource = R"(
        #version 330 core
        layout(location = 0) in vec3 aPos;
        void main()
        {
            gl_Position = vec4(aPos, 1.0);
        }
    )";

    const char* fragmentShaderSource = R"(
        #version 330 core
        out vec4 FragColor;
        void main()
        {
            FragColor = vec4(0.2, 0.7, 0.3, 1.0); // green color
        }
    )";

    unsigned int vertexShader = glCreateShader(GL_VERTEX_SHADER);
    glShaderSource(vertexShader, 1, &vertexShaderSource, nullptr);
    glCompileShader(vertexShader);

    unsigned int fragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(fragmentShader, 1, &fragmentShaderSource, nullptr);
    glCompileShader(fragmentShader);

    unsigned int shaderProgram = glCreateProgram();
    glAttachShader(shaderProgram, vertexShader);
    glAttachShader(shaderProgram, fragmentShader);
    glLinkProgram(shaderProgram);

    glDeleteShader(vertexShader);
    glDeleteShader(fragmentShader);

    // Outline shader (black)
    const char* outlineFragmentShaderSource = R"(
        #version 330 core
        out vec4 FragColor;
        void main()
        {
            FragColor = vec4(0.0, 0.0, 0.0, 1.0); // black color
        }
    )";

    unsigned int outlineFragmentShader = glCreateShader(GL_FRAGMENT_SHADER);
    glShaderSource(outlineFragmentShader, 1, &outlineFragmentShaderSource, nullptr);
    glCompileShader(outlineFragmentShader);

    unsigned int outlineShaderProgram = glCreateProgram();
    glAttachShader(outlineShaderProgram, vertexShader); // reuse vertex shader
    glAttachShader(outlineShaderProgram, outlineFragmentShader);
    glLinkProgram(outlineShaderProgram);

    glDeleteShader(outlineFragmentShader);

    // Generate 5x5 grid square vertex data. 1d array of float that store the positions of all squares' vertices.
    std::vector<float> vertices;
float aspect = 800.0f / 600.0f; // window width / height

// half-width and half-height of each square
float squareWidth = 0.05f;
float squareHeight = 0.05f;
float gridWidth  = testgrid.getGridWidth()  * 2 * squareWidth;
float gridHeight = testgrid.getGridHeight() * 2 * squareHeight;
float startX = -gridWidth / 2.0f;  // center the grid horizontally
float startY = -gridHeight / 2.0f; // center the grid vertically

    for (int row = 0; row < testgrid.getGridHeight(); row++)
    {
        for (int col = 0; col < testgrid.getGridWidth(); col++)
        {
            float offsetX = startX + col * 2 * squareWidth;
            float offsetY = startY + row * 2 * squareHeight;

            // top left
            vertices.push_back(-squareWidth + offsetX);
            vertices.push_back( squareHeight + offsetY);
            vertices.push_back(0.0f);

            // bottom left
            vertices.push_back(-squareWidth + offsetX);
            vertices.push_back(-squareHeight + offsetY);
            vertices.push_back(0.0f);

            // bottom right
            vertices.push_back(squareWidth + offsetX);
            vertices.push_back(-squareHeight + offsetY);
            vertices.push_back(0.0f);

            // top left
            vertices.push_back(-squareWidth + offsetX);
            vertices.push_back( squareHeight + offsetY);
            vertices.push_back(0.0f);

            // bottom right
            vertices.push_back(squareWidth + offsetX);
            vertices.push_back(-squareHeight + offsetY);
            vertices.push_back(0.0f);

            // top right
            vertices.push_back(squareWidth + offsetX);
            vertices.push_back( squareHeight + offsetY);
            vertices.push_back(0.0f);
        }
    }

    // Outline vertices (just corners of each square)
    std::vector<float> outlineVertices;
    for (int row = 0; row < testgrid.getGridHeight(); row++)
    {
        for (int col = 0; col < testgrid.getGridWidth(); col++)
        {
            float offsetX = startX + col * 2 * squareWidth;
            float offsetY = startY + row * 2 * squareHeight;

            // top-left
            outlineVertices.push_back(-squareWidth + offsetX);
            outlineVertices.push_back( squareHeight + offsetY);
            outlineVertices.push_back(0.0f);
            // bottom-left
            outlineVertices.push_back(-squareWidth + offsetX);
            outlineVertices.push_back(-squareHeight + offsetY);
            outlineVertices.push_back(0.0f);
            // bottom-right
            outlineVertices.push_back(squareWidth + offsetX);
            outlineVertices.push_back(-squareHeight + offsetY);
            outlineVertices.push_back(0.0f);
            // top-right
            outlineVertices.push_back(squareWidth + offsetX);
            outlineVertices.push_back( squareHeight + offsetY);
            outlineVertices.push_back(0.0f);
        }
    }

    unsigned int VAO, VBO;
    glGenVertexArrays(1, &VAO);
    glGenBuffers(1, &VBO);

    glBindVertexArray(VAO);
    glBindBuffer(GL_ARRAY_BUFFER, VBO);
    glBufferData(GL_ARRAY_BUFFER, vertices.size() * sizeof(float), vertices.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    unsigned int outlineVAO, outlineVBO;
    glGenVertexArrays(1, &outlineVAO);
    glGenBuffers(1, &outlineVBO);

    glBindVertexArray(outlineVAO);
    glBindBuffer(GL_ARRAY_BUFFER, outlineVBO);
    glBufferData(GL_ARRAY_BUFFER, outlineVertices.size() * sizeof(float), outlineVertices.data(), GL_STATIC_DRAW);
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 3 * sizeof(float), (void*)0);
    glEnableVertexAttribArray(0);
    glBindBuffer(GL_ARRAY_BUFFER, 0);
    glBindVertexArray(0);

    //Set viewport.
    glViewport(0, 0, 800, 600);
    //register a callback function that GLFW calls every time the window is resized.
    glfwSetFramebufferSizeCallback(window, framebuffer_size_callback);

    //returns true if window is asked to close (user click the x button) or call
    //glfwWindowShouldClose(window,true)
    while (!glfwWindowShouldClose(window))
    {
        //if input key for the window is pressed, we close the window.
        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            glfwSetWindowShouldClose(window, true);

        //sets the background color to be teal, RGBA. doesn't paint anything yet and just set color OPENGL will use next time you clear the screen.
        glClearColor(0.1f, 0.2f, 0.25f, 1.0f);
        //fill framebuffer with the color you set with clearcolor and GL_COLOR_BUFFER_BIT means clear the color  buffer (what the user sees) otherwise old drawing from previous frame is still visible.
        glClear(GL_COLOR_BUFFER_BIT);

        // Draw all squares
        glUseProgram(shaderProgram);
        glBindVertexArray(VAO);
        glDrawArrays(GL_TRIANGLES, 0, vertices.size() / 3);
        glBindVertexArray(0);

        // Draw outlines
        glUseProgram(outlineShaderProgram);
        glBindVertexArray(outlineVAO);
        for(int i = 0; i < testgrid.getGridHeight() * testgrid.getGridWidth(); i++)
        {
            glDrawArrays(GL_LINE_LOOP, i*4, 4); // each square has 4 corners
        }
        glBindVertexArray(0);

        //every frame, swap front(what user currently see) and back(where openGL draw next frame) buffer.
        glfwSwapBuffers(window);
        //process all pending event from operating system like close request, keyboard input, etc.
        glfwPollEvents();
    }

    //delete VAO and VBO, 1 meaning number of them and second param is the pointer to the VAO you want to delete.
    glDeleteVertexArrays(1, &VAO);
    glDeleteBuffers(1, &VBO);
    glDeleteVertexArrays(1, &outlineVAO);
    glDeleteBuffers(1, &outlineVBO);

    //close all GLFW windows and free resources allocated by GLFW.
    glfwTerminate();
    return 0;
}
