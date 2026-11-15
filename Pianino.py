import os
import pygame

# Window settings
WIDTH, HEIGHT = 800, 600

# Colors & Clock
WHITE = (255, 255, 255)

# Słowniki (Dictionaries)
violin = {
    1: "violin-c4.wav",
    2: "violin-d4.wav",
    3: "violin-e4.wav",
    4: "violin-f4.wav",
    5: "violin-g4.wav",
    6: "violin-a4.wav",
    7: "violin-b4.wav",
    8: "violin-c5.wav",
}
piano = {
    1: "piano-c4.wav",
    2: "piano-d4.wav",
    3: "piano-e4.wav",
    4: "piano-f4.wav",
    5: "piano-g4.wav",
    6: "piano-a4.wav",
    7: "piano-b4.wav",
    8: "piano-c5.wav",
}
piano_im = {
    0: "piano-none.png",
    1: "piano-c4.png",
    2: "piano-d4.png",
    3: "piano-e4.png",
    4: "piano-f4.png",
    5: "piano-g4.png",
    6: "piano-a4.png",
    7: "piano-b4.png",
    8: "piano-c5.png",
}
backing_track = {
    1: "BackingTrack_Cmaj2.wav",
    # 2: "backing-track-2.wav",
    # 3: "backing-track-3.wav",
    # 4: "backing-track-4.wav",
}


class DashboardApp:

  def __init__(
      self,
      sound_dict=piano,
      image_dict=piano_im,
      backing_track_dict=backing_track,
      screen=None,
  ):
    pygame.init()
    if pygame.mixer.get_init() is None:
      pygame.mixer.init()
    pygame.mixer.set_num_channels(16)

    self.screen = screen
    if self.screen is None:
      self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
      pygame.display.set_caption("Dashboard sterowany w Pygame")

    self.running = True

    # Konfiguracja ścieżek
    self.base_dir = os.path.dirname(os.path.abspath(__file__))
    self.images_dir = os.path.join(self.base_dir, "images")
    self.sounds_dir = os.path.join(self.base_dir, "sound_files")

    self.sound_dict = sound_dict
    self.image_dict = image_dict
    self.backing_track_dict = backing_track_dict

    self.images = {}
    for number, image_name in self.image_dict.items():
      image_path = os.path.join(self.images_dir, image_name)
      self.images[number] = self.load_and_resize_image(
          image_path, size=(400, 400)
      )

    self.sounds = {}
    for number, sound_name in self.sound_dict.items():
      sound_path = os.path.join(self.sounds_dir, sound_name)
      if os.path.exists(sound_path):
        try:
          self.sounds[number] = pygame.mixer.Sound(sound_path)
        except Exception as e:
          print(f"Błąd ładowania dźwięku {sound_path}: {e}")
      else:
        print(f"Brak pliku dźwiękowego: {sound_path}")

    # Wczytanie obrazka domyślnego (klucz 0)
    default_img_name = self.image_dict.get(0, "piano-none.png")
    self.default_image = self.images.get(0)
    if self.default_image is None:
      self.default_img_path = os.path.join(self.images_dir, default_img_name)
      self.default_image = self.load_and_resize_image(self.default_img_path)
    self.current_image = self.default_image

    # Timer do powrotu do stanu domyślnego (przechowuje znacznik czasu w ms)
    self.reset_timer_ticks = 0

  def load_and_resize_image(self, path, size=(400, 400)):
    """Pomocnicza metoda do wczytywania i skalowania obrazka przez Pygame."""
    if os.path.exists(path):
      try:
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, size)
      except Exception as e:
        print(f"Błąd ładowania obrazka {path}: {e}")
        return None
    else:
      print(f"Brak pliku obrazka: {path}")
      # Tworzenie pustej zastępczej powierzchni, jeśli plik nie istnieje
      fallback = pygame.Surface(size)
      fallback.fill((200, 200, 200))
      return fallback

  def trigger_event(self, number, duration_ms=3000):
    """Funkcja wywoływana, gdy otrzymasz input liczbowy (1-8)."""
    if number not in self.sound_dict or number not in self.image_dict:
      print("Liczba musi być w zakresie od 1 do 8.")
      return

    # 1. Zmiana obrazka
    loaded_img = self.images.get(number)
    if loaded_img:
      self.current_image = loaded_img

    # 2. Odtworzenie wcześniej załadowanego dźwięku .wav
    sound = self.sounds.get(number)
    if sound is not None:
      channel = pygame.mixer.find_channel()
      if channel:
        channel.play(sound)
      else:
        sound.play()
    else:
      print(f"Nie można odtworzyć dźwięku dla nuty {number}.")

    # 3. Ustawienie czasu powrotu do stanu domyślnego
    self.reset_timer_ticks = pygame.time.get_ticks() + duration_ms

  def trigger_event_with_backing_track(self, number, duration_ms=3000):
      """Wywołuje trigger_event i odtwarza backing track w tle."""
      if number not in self.backing_track_dict and number in self.sound_dict and number in self.image_dict:
        self.trigger_event(number, duration_ms)
        return
      # Odtwarzanie backing track w tle
      backing_track_name = self.backing_track_dict.get(number)
      if backing_track_name:
          backing_track_path = os.path.join(self.sounds_dir, backing_track_name)
          if os.path.exists(backing_track_path):
              try:
                  pygame.mixer.music.load(backing_track_path)
                  pygame.mixer.music.play()
                  self.reset_timer_ticks = pygame.time.get_ticks() + duration_ms
                  return pygame.time.get_ticks()
              except Exception as e:
                  print(f"Błąd odtwarzania backing track {backing_track_path}: {e}")
          else:
              print(f"Brak pliku backing track: {backing_track_path}")
      self.reset_timer_ticks = pygame.time.get_ticks() + duration_ms
      return None

  def update(self, number=None, duration_ms=900):
    """Process one frame; optionally trigger a note or backing track."""
    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        self.running = False
      elif event.type == pygame.KEYDOWN:
        if pygame.K_1 <= event.key <= pygame.K_8:
          number = event.key - pygame.K_0

    if not self.running:
      return False

    if number is not None:
      self.trigger_event_with_backing_track(number, duration_ms)

    if (
        self.reset_timer_ticks > 0
        and pygame.time.get_ticks() >= self.reset_timer_ticks
    ):
      self.current_image = self.default_image
      self.reset_timer_ticks = 0
      print("Powrót do obrazka domyślnego.")

    self.draw()
    pygame.display.flip()
    return self.running

  def draw(self, surface=None):
    """Rysuje aktualny obrazek na środku ekranu."""
    if surface is None:
      surface = self.screen
    surface.fill(WHITE)
    if self.current_image:
      # Wyśrodkowanie obrazka 400x400 na oknie 800x600
      rect = self.current_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
      surface.blit(self.current_image, rect)


def main():
  app = DashboardApp()
  clock = pygame.time.Clock()

  while app.update():
    clock.tick(60)

  pygame.quit()


if __name__ == "__main__":
  main()