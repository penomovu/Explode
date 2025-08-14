import pygame
import sys
import math
import numpy as np
import imageio
import os
from scipy.io.wavfile import write as write_wav
import imageio_ffmpeg
import subprocess
import mido
from gui import create_gui

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
VIDEO_DURATION = 10 # seconds
FPS = 60
OUTPUT_DIR = "tiktok_game/output"


# --- Music Constants ---
SAMPLE_RATE = 44100
NOTE_DURATION = 0.15 # seconds

def load_midi_notes(midi_path):
    """Load musical notes from a MIDI file."""
    notes = []
    if not os.path.exists(midi_path):
        print(f"MIDI file not found at {midi_path}. Using default melody.")
        return [72, 69, 71, 67, 69, 65, 67, 64]
    try:
        mid = mido.MidiFile(midi_path)
        for msg in mid:
            if not msg.is_meta and msg.type == 'note_on':
                notes.append(msg.note)
    except Exception as e:
        print(f"Could not read MIDI file {midi_path}: {e}")
        # Fallback to a default melody
        return [72, 69, 71, 67, 69, 65, 67, 64]
    return notes

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

    def update(self, circles, notes, frame_num, audio_events, melody_index_ref, midi_notes):
        """Update the ball's position, velocity, and handle collisions with circles."""
        self.vel.y += GRAVITY
        self.pos += self.vel

        center = pygame.math.Vector2(WIDTH // 2, HEIGHT // 2)

        # --- Collision and Scoring with Circles ---
        for circle in circles:
            if circle.broken:
                continue

            dist_to_center = self.pos.distance_to(center)

            # Check for collision with the circle's arc
            if abs(dist_to_center - circle.radius) < self.radius + CIRCLE_WIDTH / 2:
                ball_angle = math.atan2(self.pos.y - center.y, self.pos.x - center.x)
                if ball_angle < 0:
                    ball_angle += 2 * math.pi

                gap_start = circle.angle
                gap_end = (circle.angle + circle.gap_size) % (2 * math.pi)

                in_gap = False
                if gap_start < gap_end:
                    if gap_start <= ball_angle <= gap_end:
                        in_gap = True
                else:  # Gap wraps around 0
                    if ball_angle >= gap_start or ball_angle <= gap_end:
                        in_gap = True

                if in_gap:
                    # The ball passed through the gap, check if it just crossed
                    if (self.prev_dist_from_center < circle.radius and dist_to_center >= circle.radius) or \
                       (self.prev_dist_from_center > circle.radius and dist_to_center <= circle.radius):
                        self.score += 1
                        circle.broken = True
                else:
                    # Collision with the solid part of the arc
                    normal = (self.pos - center).normalize()
                    self.vel.reflect_ip(normal)
                    self.vel *= 0.9  # Apply damping

                    # Adjust position to prevent sticking
                    if dist_to_center < circle.radius:
                        self.pos = center + normal * (circle.radius - self.radius)
                    else:
                        self.pos = center + normal * (circle.radius + self.radius)

                    # Sound and visual effect
                    circle.start_breaking()
                    if midi_notes:
                        note_index = melody_index_ref[0] % len(midi_notes)
                        note_to_play = midi_notes[note_index]
                        audio_events.append((frame_num / FPS, note_to_play))
                        melody_index_ref[0] += 1

        self.prev_dist_from_center = self.pos.distance_to(center)

        # --- Wall Bouncing ---
        if self.pos.x - self.radius < 0 or self.pos.x + self.radius > WIDTH:
            self.vel.x *= -0.9
            self.pos.x = np.clip(self.pos.x, self.radius, WIDTH - self.radius)
        if self.pos.y - self.radius < 0:
            self.vel.y *= -0.9
            self.pos.y = self.radius
        if self.pos.y + self.radius > HEIGHT:
            self.vel.y *= -0.9
            self.pos.y = HEIGHT - self.radius


    def draw(self, screen):
        """Draw the ball on the screen."""
        pygame.draw.circle(screen, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)

class Circle:
    """Class to represent a rotating circle with a gap."""
    def __init__(self, x, y, radius, color):
        self.pos = pygame.math.Vector2(x, y)
        self.radius = radius
        self.original_color = color
        self.breaking_color = YELLOW
        self.is_breaking = False
        self.breaking_timer = 0
        self.broken = False
        # Add hole and rotation
        self.gap_size = math.radians(60)  # 60-degree gap
        self.angle = np.random.uniform(0, 2 * math.pi)
        self.rotation_speed = np.random.uniform(-0.02, 0.02)

    def start_breaking(self):
        """Initiate the breaking effect (color flash)."""
        self.is_breaking = True
        self.breaking_timer = 15  # Flash for 0.25 seconds at 60fps

    def update(self):
        """Handle the breaking effect timer and rotation."""
        if self.is_breaking:
            self.breaking_timer -= 1
            if self.breaking_timer <= 0:
                self.is_breaking = False
        self.angle += self.rotation_speed
        self.angle %= (2 * math.pi) # Keep angle in [0, 2*pi]

    def draw(self, screen):
        """Draw the circle arc on the screen."""
        if self.broken:
            return

        color = self.breaking_color if self.is_breaking else self.original_color

        # Define the arc for drawing, leaving a gap
        start_angle = self.angle + self.gap_size
        end_angle = self.angle + 2 * math.pi

        rect = pygame.Rect(self.pos.x - self.radius, self.pos.y - self.radius, self.radius * 2, self.radius * 2)
        try:
            # This can fail if the start and end angles are too close
            pygame.draw.arc(screen, color, rect, start_angle, end_angle, CIRCLE_WIDTH)
        except pygame.error:
            # Draw a full circle as a fallback if arc fails
            pygame.draw.circle(screen, color, (int(self.pos.x), int(self.pos.y)), self.radius, CIRCLE_WIDTH)

def generate_final_audio(events, duration, sample_rate, notes, audio_file):
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
    write_wav(audio_file, sample_rate, audio_buffer)


def generate_single_video(video_index):
    """Generate a single video."""
    # Use dummy drivers for video and audio
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
    pygame.init()

    # --- Load and play background music ---
    try:
        pygame.mixer.music.load("tiktok_game/assets/tetris.mid")
        pygame.mixer.music.play(-1)  # Loop indefinitely
    except pygame.error as e:
        print(f"Could not load or play music: {e}")

    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("TikTok Game")
    font = pygame.font.Font(None, 100)
    viral_font = pygame.font.Font(None, 150)

    # Load MIDI notes and pre-generate sounds
    midi_notes = load_midi_notes("tiktok_game/assets/tetris.mid")
    notes = {note_num: Note(note_num) for note_num in set(midi_notes)}

    melody_index_ref = [0] # Use a list to pass by reference
    audio_events = []

    # --- Create Game Objects ---
    ball1 = Ball(WIDTH // 2 - 100, HEIGHT // 2, BALL_RADIUS, RED)
    ball2 = Ball(WIDTH // 2 + 100, HEIGHT // 2, BALL_RADIUS, BLUE)
    balls = [ball1, ball2]

    circles = []
    num_circles = 20
    circle_colors = [BLUE, RED, (0, 255, 0), (255, 165, 0)]
    for i in range(1, num_circles + 1):
        radius = i * (HEIGHT // (num_circles * 2)) # Distribute circles evenly
        color = circle_colors[i % len(circle_colors)]
        circles.append(Circle(WIDTH // 2, HEIGHT // 2, radius, color))

    # --- Set up video writer ---
    video_file = os.path.join(OUTPUT_DIR, f"temp_video_{video_index}.mp4")
    audio_file = os.path.join(OUTPUT_DIR, f"temp_audio_{video_index}.wav")
    final_video_file = os.path.join(OUTPUT_DIR, f"final_video_{video_index}.mp4")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    video_writer = imageio.get_writer(video_file, fps=FPS)

    frame_num = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        # --- Update all game objects ---
        for ball in balls:
            ball.update(circles, notes, frame_num, audio_events, melody_index_ref, midi_notes)
        for circle in circles:
            circle.update()

        # --- Drawing ---
        screen.fill(BACKGROUND_COLOR)
        for ball in balls:
            ball.draw(screen)
        for circle in circles:
            circle.draw(screen)

        # Draw scores
        score1_text = font.render(f"{ball1.score}", True, ball1.color)
        screen.blit(score1_text, (50, 50))
        score2_text = font.render(f"{ball2.score}", True, ball2.color)
        score2_rect = score2_text.get_rect(topright=(WIDTH - 50, 50))
        screen.blit(score2_text, score2_rect)

        # Add "viral" text overlay
        viral_text = viral_font.render("Are you stupid?", True, (0,0,0,180))
        text_rect = viral_text.get_rect(center=(WIDTH/2, HEIGHT/4))
        screen.blit(viral_text, text_rect)

        pygame.display.flip()

        # --- Video Frame Capturing ---
        frame = pygame.surfarray.array3d(screen)
        frame = np.transpose(frame, (1, 0, 2))
        video_writer.append_data(frame)
        frame_num += 1
        if frame_num >= VIDEO_DURATION * FPS:
            running = False

    # --- Post-processing ---
    video_writer.close()
    print(f"Video frames saved to {video_file}")
    generate_final_audio(audio_events, VIDEO_DURATION, SAMPLE_RATE, notes, audio_file)
    print(f"Audio file generated: {audio_file}")

    # Merge video and audio
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg_exe, '-y',
        '-i', video_file, '-i', audio_file,
        '-c:v', 'copy', '-c:a', 'aac', '-strict', 'experimental',
        final_video_file
    ]
    print("Merging video and audio with ffmpeg...")
    subprocess.run(command, check=True)
    print(f"Final video saved to {final_video_file}")

    # Clean up temporary files
    os.remove(video_file)
    os.remove(audio_file)

    pygame.quit()

def generate_videos(num_videos):
    """Generate a specified number of videos."""
    for i in range(num_videos):
        print(f"--- Generating video {i + 1} of {num_videos} ---")
        generate_single_video(i)
    print("--- All videos generated. ---")


if __name__ == "__main__":
    # The main entry point of the application is now the GUI.
    # The GUI will call generate_videos().
    create_gui()
