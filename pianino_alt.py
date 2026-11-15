import time

import pygame


volumes = {
    "Master": 1.0,
    "Music": 0.7,
    "Sound Effects": 0.8,
    "Ambient": 0.5,
}
volume_names = tuple(volumes)
volume_transition = None


def change_volume(volume_index):
    """Start a four-second adjustment; indices are one-based."""
    global volume_transition

    if (
        not isinstance(volume_index, int)
        or isinstance(volume_index, bool)
        or not 1 <= volume_index <= len(volume_names)
    ):
        raise ValueError(f"volume_index must be between 1 and {len(volume_names)}")

    selected_volume = volume_names[volume_index - 1]
    start_values = volumes.copy()
    changes = {
        name: 0.24 if name == selected_volume else -0.08
        for name in volume_names
    }

    limit_progress = 1.0
    limiting_volumes = {}
    for name, change in changes.items():
        if change > 0:
            progress_to_limit = (1.0 - start_values[name]) / change
            limit_value = 1.0
        else:
            progress_to_limit = start_values[name] / -change
            limit_value = 0.0

        if progress_to_limit < limit_progress:
            limit_progress = progress_to_limit
            limiting_volumes = {name: limit_value}
        elif abs(progress_to_limit - limit_progress) <= 1e-12:
            limiting_volumes[name] = limit_value

    volume_transition = {
        "start_time": time.monotonic(),
        "start_values": start_values,
        "changes": changes,
        "limit_progress": limit_progress,
        "limiting_volumes": limiting_volumes,
    }


def update_volume_transition(now=None):
    global volume_transition

    if volume_transition is None:
        return

    if now is None:
        now = time.monotonic()

    elapsed_progress = min(
        max((now - volume_transition["start_time"]) / 4.0, 0.0),
        1.0,
    )
    progress = min(elapsed_progress, volume_transition["limit_progress"])

    for name, change in volume_transition["changes"].items():
        start_value = volume_transition["start_values"][name]
        volumes[name] = min(1.0, max(0.0, start_value + change * progress))

    if elapsed_progress >= volume_transition["limit_progress"]:
        for name, limit_value in volume_transition["limiting_volumes"].items():
            volumes[name] = limit_value
        volume_transition = None
    elif elapsed_progress >= 1.0:
        volume_transition = None


def main():
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((700, 450))
    pygame.display.set_caption("Audio Settings")

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 32)
    small_font = pygame.font.Font(None, 24)

    sliders = {
        "Master": pygame.Rect(180, 110, 350, 8),
        "Music": pygame.Rect(180, 190, 350, 8),
        "Sound Effects": pygame.Rect(180, 270, 350, 8),
        "Ambient": pygame.Rect(180, 350, 350, 8),
    }

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        update_volume_transition()

        pygame.mixer.music.set_volume(volumes["Master"] * volumes["Music"])
        screen.fill((30, 30, 40))

        title = font.render("AUDIO SETTINGS", True, (255, 255, 255))
        screen.blit(title, (260, 35))

        for name, rect in sliders.items():
            label = small_font.render(name, True, (220, 220, 220))
            screen.blit(label, (80, rect.y - 8))

            pygame.draw.rect(screen, (80, 80, 90), rect, border_radius=5)

            filled_width = int(rect.width * volumes[name])
            filled_rect = pygame.Rect(
                rect.x, rect.y, filled_width, rect.height
            )
            pygame.draw.rect(
                screen, (0, 190, 130), filled_rect, border_radius=5
            )

            handle_x = int(rect.x + volumes[name] * rect.width)
            pygame.draw.circle(
                screen, (255, 255, 255), (handle_x, rect.centery), 12
            )

            percentage = small_font.render(
                f"{int(volumes[name] * 100)}%",
                True,
                (255, 255, 255),
            )
            screen.blit(percentage, (550, rect.y - 8))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
