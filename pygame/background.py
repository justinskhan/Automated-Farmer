#This file will hold the background code  for the game 
import pygame


class Background:

    def __init__(
        self,
        color: tuple[int, int, int] = (0, 0, 0), #we use RGB for our color 
        image_path: str | None = None, #lets you pass an image as a string or none at all
    ):
        self.color = color #stores color or image
        self.image: pygame.Surface | None = None

        #if there is an image then convert the image to the screen size otherwise throw error
        if image_path:
            try:
                raw = pygame.image.load(image_path).convert()
                self.image = raw
            except FileNotFoundError:
                print(f"[Background] Image not found: {image_path}. Falling back to color.")

    #function to set an solid color background
    def set_color(self, color: tuple[int, int, int]) -> None:
        """Switch to a solid-color background."""
        self.color = color
        self.image = None

    #function to set an image background
    def set_image(self, image_path: str) -> None:
        try:
            raw = pygame.image.load(image_path).convert()
            self.image = raw
        except FileNotFoundError:
            print(f"[Background] Image not found: {image_path}")

    #creates the actual background for the game
    def draw(self, surface: pygame.Surface) -> None:
        if self.image:
            scaled = pygame.transform.scale(self.image, surface.get_size())
            surface.blit(scaled, (0, 0))
        else:
            surface.fill(self.color)