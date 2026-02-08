#include <iostream>

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

        //every frame, swap front(what user currently see) and back(where openGL draw next frame) buffer.
        glfwSwapBuffers(window);
        //process all pending event from operating system like close request, keyboard input, etc.
        glfwPollEvents();
    }

    //close all GLFW windows and free resources allocated by GLFW.
    glfwTerminate();
    return 0;
}
