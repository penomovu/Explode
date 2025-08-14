import pygame
import sys
import math
import numpy as np
import imageio
import os
from scipy.io.wavfile import write as write_wav
import imageio_ffmpeg
import subprocess

# --- Constants ---
WIDTH, HEIGHT = 1080, 1920 # TikTok video dimensions
BACKGROUND_COLOR = (255, 255, 255)
BALL_RADIUS = 30
GRAVITY = 0.5
CIRCLE_WIDTH = 15
FONT_COLOR = (0, 0, 0)

# Colors
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0) # Color for the "breaking" effect

# --- Video Generation ---
VIDEO_MODE = True # Set to False for interactive mode
VIDEO_DURATION = 10 # seconds
FPS = 60
OUTPUT_DIR = "tiktok_game/output"
VIDEO_FILE = os.path.join(OUTPUT_DIR, "temp_video.mp4")
AUDIO_FILE = os.path.join(OUTPUT_DIR, "temp_audio.wav")
FINAL_VIDEO_FILE = os.path.join(OUTPUT_DIR, "final_video.mp4")


# --- Music Constants ---
SAMPLE_RATE = 44100
NOTE_DURATION = 0.15 # seconds

# --- Melody (C Major scale pattern) ---
# A simple, game-like melody to be played on bounces.
MELODY = [72, 69, 71, 67, 69, 65, 67, 64] # MIDI note numbers
melody_index = 0
audio_events = [] # To store (timestamp, note_id) for video generation


# --- Sound Generation ---
def midi_to_freq(midi_note):
    """Convert a MIDI note number to a frequency in Hz."""
    return 440 * (2 ** ((midi_note - 69) / 12))

def generate_sine_wave(frequency, duration, sample_rate):
    """Generate a sine wave for a given frequency and duration."""
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    wave = np.sin(frequency * t * 2 * np.pi)
    wave *= 32767 # Scale to 16-bit signed integer range
    return wave.astype(np.int16)

class Note:
    """A playable note generated from a MIDI number."""
    def __init__(self, midi_note):
        frequency = midi_to_freq(midi_note)
        patt = generate_sine_wave(frequency, NOTE_DURATION, SAMPLE_RATE)
        self.wave = patt # Store the mono wave for audio generation
        # Pygame needs a C-contiguous, 2D array for stereo
        stereo_patt = np.ascontiguousarray(np.array([patt, patt]).T)
        self.sound = pygame.sndarray.make_sound(stereo_patt)

    def play(self):
        self.sound.play()

# --- Game Classes ---
class Ball:
    """Class to represent a bouncing ball."""
    def __init__(self, x, y, radius, color):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = radius
        self.color = color
        # Start with a random velocity
        self.vel = pygame.math.Vector2(np.random.randint(-5, 5), np.random.randint(-5, 5))
        self.score = 0
        # Store the previous distance from the center to detect circle crossings
        self.prev_dist_from_center = self.pos.distance_to(pygame.math.Vector2(WIDTH // 2, HEIGHT // 2))

    def update(self, circles, notes, frame_num):
        """Update the ball's position, velocity, and handle circle crossings."""
        global melody_index
        self.vel.y += GRAVITY
        self.pos += self.vel

        # --- Circle Crossing Detection ---
        center = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)
        current_dist_from_center = self.pos.distance_to(center)

        for circle in circles:
            # Check if the ball crossed the circle's radius in the last frame
            if (self.prev_dist_from_center < circle.radius and current_dist_from_center >= circle.radius) or \
               (self.prev_dist_from_center > circle.radius and current_dist_from_center <= circle.radius):

                # Trigger visual effect and sound
                circle.start_breaking()
                note_to_play = MELODY[melody_index]
                if VIDEO_MODE:
                    audio_events.append((frame_num / FPS, note_to_play))
                else:
                    notes[note_to_play].play()
                melody_index = (melody_index + 1) % len(MELODY)

                # Increment score
                self.score += 1

        self.prev_dist_from_center = current_dist_from_center

        # --- Wall Bouncing ---
        if self.pos.x - self.radius < 0 or self.pos.x + self.radius > WIDTH:
            self.vel.x *= -0.9
            self.pos.x = np.clip(self.pos.x, self.radius, WIDTH - self.radius)
        if self.pos.y - self.radius < 0:
            self.vel.y *= -0.9
            self.pos.y = self.radius
        if self.pos.y + self.radius > HEIGHT:
            self.vel.y *= -0.9 # Energy loss on bounce
            self.pos.y = HEIGHT - self.radius


    def draw(self, screen):
        """Draw the ball on the screen."""
        pygame.draw.circle(screen, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)

class Circle:
    """Class to represent a circle."""
    def __init__(self, x, y, radius, color):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = radius
        self.original_color = color
        self.breaking_color = YELLOW
        self.is_breaking = False
        self.breaking_timer = 0

    def start_breaking(self):
        """Initiate the breaking effect (color flash)."""
        self.is_breaking = True
        self.breaking_timer = 30  # 0.5 seconds at 60fps

    def update(self):
        """Handle the breaking effect timer."""
        if self.is_breaking:
            self.breaking_timer -= 1
            if self.breaking_timer <= 0:
                self.is_breaking = False

    def draw(self, screen):
        """Draw the circle on the screen."""
        color = self.breaking_color if self.is_breaking else self.original_color
        pygame.draw.circle(screen, color, (int(self.pos.x), int(self.pos.y)), self.radius, CIRCLE_WIDTH)

def generate_final_audio(events, duration, sample_rate, notes):
    """Generate a WAV file from the recorded audio events."""
    total_samples = int(duration * sample_rate)
    audio_buffer = np.zeros(total_samples, dtype=np.int16)
    # "Paste" the note waves onto the audio buffer at the correct timestamps
    for timestamp, note_num in events:
        start_sample = int(timestamp * sample_rate)
        note_wave = notes[note_num].wave
        end_sample = start_sample + len(note_wave)
        if end_sample < total_samples:
            audio_buffer[start_sample:end_sample] += note_wave
    write_wav(AUDIO_FILE, sample_rate, audio_buffer)


def main():
    """Main function to run the game and video generation."""
    # Use dummy drivers for video and audio in video generation mode
    if VIDEO_MODE:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"

    pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TikTok Game")
    font = pygame.font.Font(None, 100)
    viral_font = pygame.font.Font(None, 150)

    # Pre-generate the sounds for all notes in the melody
    notes = {note_num: Note(note_num) for note_num in set(MELODY)}

    # --- Create Game Objects ---
    ball = Ball(WIDTH // 2, HEIGHT // 2, BALL_RADIUS, RED)

    circles = []
    num_circles = np.random.randint(3, 7) # Random number of circles
    circle_colors = [BLUE, RED, (0, 255, 0), (255, 165, 0)]
    for i in range(1, num_circles + 1):
        radius = i * 100
        color = circle_colors[i % len(circle_colors)]
        circles.append(Circle(WIDTH // 2, HEIGHT // 2, radius, color))


    video_writer = None
    if VIDEO_MODE:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        video_writer = imageio.get_writer(VIDEO_FILE, fps=FPS)

    clock = pygame.time.Clock()
    frame_num = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Update all game objects ---
        ball.update(circles, notes, frame_num)
        for circle in circles:
            circle.update()

        # --- Drawing ---
        screen.fill(BACKGROUND_COLOR)
        ball.draw(screen)
        for circle in circles:
            circle.draw(screen)

        # Draw score
        score_text = font.render(f"{ball.score}", True, FONT_COLOR)
        screen.blit(score_text, (50, 50))

        # Add "viral" text overlay in video mode
        if VIDEO_MODE:
            viral_text = viral_font.render("Are you stupid?", True, (0,0,0,180))
            text_rect = viral_text.get_rect(center=(WIDTH/2, HEIGHT/4))
            screen.blit(viral_text, text_rect)

        pygame.display.flip()

        # --- Video Frame Capturing ---
        if VIDEO_MODE:
            frame = pygame.surfarray.array3d(screen)
            # Pygame and imageio have different coordinate systems
            frame = np.transpose(frame, (1, 0, 2))
            video_writer.append_data(frame)
            frame_num += 1
            # Stop after the desired duration
            if frame_num >= VIDEO_DURATION * FPS:
                running = False

        # In interactive mode, tick the clock to control FPS
        if not VIDEO_MODE:
            clock.tick(FPS)

    # --- Post-processing for Video Generation ---
    if VIDEO_MODE and video_writer:
        video_writer.close()
        print(f"Video frames saved to {VIDEO_FILE}")
        generate_final_audio(audio_events, VIDEO_DURATION, SAMPLE_RATE, notes)
        print(f"Audio file generated: {AUDIO_FILE}")

        # Merge video and audio using the ffmpeg executable from imageio-ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        command = [
            ffmpeg_exe,
            '-y',
            '-i', VIDEO_FILE,
            '-i', AUDIO_FILE,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-strict', 'experimental',
            FINAL_VIDEO_FILE
        ]

        print("Merging video and audio with ffmpeg...")
        subprocess.run(command, check=True)
        print(f"Final video saved to {FINAL_VIDEO_FILE}")

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
