import pygame 

#initialize pygame
pygame.init() 

#create the screen to start at 800x600 pixels and resizable allows screen to be adjsuted
screen = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
pygame.display.set_caption("Automated Farmer") #the title of the window is named Automated Farmer

#this code makes it so the window runs until the X is clicked on 
running = True 
while running: 
    for event in pygame.event.get(): 
        if event.type == pygame.QUIT: 
            running = False 
#this will handle if the window is resized by user
        elif event.type == pygame.VIDEORESIZE:
            screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE) 

#Game rendering 
screen.fill((0,0,0)) #will make the screen black
pygame.display.flip() #.flip updates the screen

pygame.quit() #calls when player exits