# from PIL import Image, ImageTk
# import tkinter as tk
# import winsound
# import os
#
# violin = {1: "violin-c4.wav", 2: "violin-d4.wav", 3: "violin-e4.wav", 4: "violin-f4.wav", 5: "violin-g4.wav",
#           6: "violin-a4.wav", 7: "violin-b4.wav", 8: "violin-c5.wav"}
# piano = {1: "piano-c4.wav", 2: "piano-d4.wav", 3: "piano-e4.wav", 4: "piano-f4.wav", 5: "piano-g4.wav",
#          6: "piano-a4.wav", 7: "piano-b4.wav", 8: "piano-c5.wav"}
# piano_im = {0: "piano-none.png", 1: "piano-c4.png", 2: "piano-d4.png", 3: "piano-e4.png", 4: "piano-f4.png",
#             5: "piano-g4.png", 6: "piano-a4.png", 7: "piano-b4.png", 8: "piano-c5.png"}
# backing_track = {1: "backing-track-1.wav", 2: "backing-track-2.wav", 3: "backing-track-3.wav", 4: "backing-track-4.wav"}
#
# class DashboardApp:
#     def __init__(self, root, sound_dict=piano, image_dict=piano_im):
#         self.root = root
#         self.root.title("Dashboard sterowany skryptem")
#         self.root.geometry("800x600")
#
#         # Konfiguracja ścieżek
#         self.base_dir = "."
#         self.images_dir = os.path.join(self.base_dir, "images")
#         self.sounds_dir = os.path.join(self.base_dir, "sound_files")
#
#         # Przypisanie słowników do instancji klasy
#         self.sound_dict = sound_dict
#         self.image_dict = image_dict
#
#         # Tworzenie elementu wyświetlającego obrazek
#         self.image_label = tk.Label(root)
#         self.image_label.pack(expand=True, fill="both")
#
#         # Ładowanie i skalowanie obrazka domyślnego (klucz 0)
#         default_img_name = self.image_dict.get(0, "piano-none.png")
#         self.default_img_path = os.path.join(self.images_dir, default_img_name)
#
#         self.current_image = self.load_and_resize_image(self.default_img_path, size=(400, 400))
#         if self.current_image:
#             self.image_label.config(image=self.current_image)
#
#         # Zmienna do przechowywania ID timera
#         self.timer_id = None
#
#     def load_and_resize_image(self, path, size=(400, 400)):
#         """Pomocnicza metoda do wczytywania i skalowania obrazka przez Pillow."""
#         if os.path.exists(path):
#             pil_image = Image.open(path)
#             pil_image = pil_image.resize(size, Image.Resampling.LANCZOS)
#             return ImageTk.PhotoImage(pil_image)
#         else:
#             print(f"Brak pliku obrazka: {path}")
#             return None
#
#     def trigger_event(self, number, duration_ms=3000):
#         """
#         Funkcja wywoływana, gdy otrzymasz input liczbowy (1-8).
#         """
#         if number not in self.sound_dict or number not in self.image_dict:
#             print("Liczba musi być w zakresie od 1 do 8.")
#             return
#
#         # 1. Zmiana obrazka (pobieranie z folderu images)
#         img_name = self.image_dict[number]
#         img_path = os.path.join(self.images_dir, img_name)
#
#         new_img = self.load_and_resize_image(img_path, size=(400, 400))
#         if new_img:
#             self.new_image = new_img  # Przypisanie do pola, żeby Garbage Collector nie skasował obrazka
#             self.image_label.config(image=self.new_image)
#
#         # 2. Odtworzenie dźwięku .wav (pobieranie z folderu sound_files)
#         sound_name = self.sound_dict[number]
#         sound_path = os.path.join(self.sounds_dir, sound_name)
#
#         if os.path.exists(sound_path):
#             winsound.PlaySound(sound_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
#         else:
#             print(f"Brak pliku dźwiękowego: {sound_path}")
#
#         # 3. Obsługa timera powrotu do stanu domyślnego
#         if self.timer_id is not None:
#             self.root.after_cancel(self.timer_id)
#
#         self.timer_id = self.root.after(duration_ms, self.reset_to_default)
#
#     def reset_to_default(self):
#         """Przywraca domyślny obrazek po upływie czasu."""
#         if self.current_image:
#             self.image_label.config(image=self.current_image)
#         self.timer_id = None
#         print("Powrót do obrazka domyślnego.")
#
#
# # --- Testowanie działania ---
# if __name__ == "__main__":
#     root = tk.Tk()
#     app = DashboardApp(root, sound_dict=piano, image_dict=piano_im)
#
#     # Symulacja wywołania po 2 sekundach dla liczby 3
#     # root.after(2000, lambda: app.trigger_event(3, duration_ms=4000))
#     # Pętla od 1 do 8 (włącznie)
#     # 1. Pierwsza pętla (w górę: 1 do 8)
#     for note in range(1, 9):
#         # Każda kolejna nuta co 1 sekundę (1000ms, 2000ms, ..., 8000ms)
#         root.after(note * 1000, lambda n=note: app.trigger_event(n, duration_ms=900))
#         root.after(note * 100, lambda n=note: app.trigger_event(n, duration_ms=900))
#
#     # 2. Druga pętla (w dół: 8 do 1) - uruchomi się PO pierwszej pętli
#     # Pierwsza pętla kończy się po 8 sekundach (8000ms), więc dodajemy bazowe opóźnienie 8000ms
#     base_delay = 8000
#     for note in range(8, 0, -1):
#         # Czas startu to bazowe 8 sekund + kolejne sekundy dla danej nuty
#         delay = base_delay + (9 - note) * 1000
#         root.after(delay, lambda n=note: app.trigger_event(n, duration_ms=900))
#
#     root.mainloop()

import os
import pygame

# Initialize Pygame and the mixer
pygame.init()
pygame.mixer.init()

# Increase the audio channel count so sounds can overlap without cutting each other off
pygame.mixer.set_num_channels(16)

# Window settings
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Dashboard sterowany w Pygame")

# Colors & Clock
WHITE = (255, 255, 255)
clock = pygame.time.Clock()

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
    1: "backing-track-1.wav",
    2: "backing-track-2.wav",
    3: "backing-track-3.wav",
    4: "backing-track-4.wav",
}


class DashboardApp:

  def __init__(self, sound_dict=piano, image_dict=piano_im):
    # Konfiguracja ścieżek
    self.base_dir = "."
    self.images_dir = os.path.join(self.base_dir, "images")
    self.sounds_dir = os.path.join(self.base_dir, "sound_files")

    self.sound_dict = sound_dict
    self.image_dict = image_dict

    # Wczytanie obrazka domyślnego (klucz 0)
    default_img_name = self.image_dict.get(0, "piano-none.png")
    self.default_img_path = os.path.join(self.images_dir, default_img_name)

    self.default_image = self.load_and_resize_image(
        self.default_img_path, size=(400, 400)
    )
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
    img_name = self.image_dict[number]
    img_path = os.path.join(self.images_dir, img_name)
    loaded_img = self.load_and_resize_image(img_path, size=(400, 400))
    if loaded_img:
      self.current_image = loaded_img

    # 2. Odtworzenie dźwięku .wav na wolnym kanale (pozwala na nakładanie dźwięków)
    sound_name = self.sound_dict[number]
    sound_path = os.path.join(self.sounds_dir, sound_name)

    if os.path.exists(sound_path):
      try:
        sound = pygame.mixer.Sound(sound_path)
        channel = pygame.mixer.find_channel()
        if channel:
          channel.play(sound)
        else:
          # Jeśli wszystkie kanały są zajęte, użyj domyślnego
          sound.play()
      except Exception as e:
        print(f"Błąd odtwarzania dźwięku {sound_path}: {e}")
    else:
      print(f"Brak pliku dźwiękowego: {sound_path}")

    # 3. Ustawienie czasu powrotu do stanu domyślnego
    self.reset_timer_ticks = pygame.time.get_ticks() + duration_ms

  def update(self):
    """Sprawdza, czy minął czas wyświetlania obrazka i wraca do domyślnego."""
    if (
        self.reset_timer_ticks > 0
        and pygame.time.get_ticks() >= self.reset_timer_ticks
    ):
      self.current_image = self.default_image
      self.reset_timer_ticks = 0
      print("Powrót do obrazka domyślnego.")

  def draw(self, surface):
    """Rysuje aktualny obrazek na środku ekranu."""
    surface.fill(WHITE)
    if self.current_image:
      # Wyśrodkowanie obrazka 400x400 na oknie 800x600
      rect = self.current_image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
      surface.blit(self.current_image, rect)


def main():
  app = DashboardApp(sound_dict=piano, image_dict=piano_im)
  running = True

  # --- Symulacja sekwencji uruchomienia (odpowiednik root.after w Tkinter) ---
  # Używamy niestandardowych zdarzeń czasowych Pygame do testowej sekwencji
  TIMED_EVENT_START = pygame.USEREVENT + 1

  # Zaplanowanie testowych wywołań (identycznych jak Twoja pętla)
  # Pierwsza pętla: 1 do 8 co 1000ms
  for note in range(1, 9):
    delay_ms = note * 1000
    pygame.time.set_timer(
        TIMED_EVENT_START + note, delay_ms, 1
    )  # Jednorazowy timer

  # Druga pętla: 8 do 1 od 9000ms
  base_delay = 8000
  for idx, note in enumerate(range(8, 0, -1)):
    delay_ms = base_delay + ((idx + 1) * 1000)
    pygame.time.set_timer(TIMED_EVENT_START + 100 + note, delay_ms, 1)

  print("Aplikacja Pygame uruchomiona. Zamykanie okna przerywa działanie.")

  while running:
    current_time = pygame.time.get_ticks()

    for event in pygame.event.get():
      if event.type == pygame.QUIT:
        running = False

      # Obsługa testowych timerów sekwencji
      elif event.type >= TIMED_EVENT_START:
        event_id = event.type - TIMED_EVENT_START
        if event_id < 100:
          app.trigger_event(event_id, duration_ms=900)
        else:
          note_val = event_id - 100
          app.trigger_event(note_val, duration_ms=900)

      # Opcjonalnie: kliknięcie klawiszy 1-8 na klawiaturze do testu manualnego
      elif event.type == pygame.KEYDOWN:
        if pygame.K_1 <= event.key <= pygame.K_8:
          num = event.key - pygame.K_0
          app.trigger_event(num, duration_ms=900)

    # Aktualizacja logiki timera obrazka
    app.update()

    # Renderowanie grafiki
    app.draw(screen)
    pygame.display.flip()

    clock.tick(60)

  pygame.quit()


if __name__ == "__main__":
  main()