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
ARC_RADIUS = 200
ARC_WIDTH = 20
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
        # Start with a random velocity for variety in generated videos
        self.vel = pygame.math.Vector2(np.random.randint(-10, 10), np.random.randint(-10, 0))
        self.score = 0
        # Flags to prevent multiple interactions for a single event
        self.last_passed_arc = None
        self.last_collided_arc = None

    def update(self, arcs, notes, frame_num):
        """Update the ball's position, velocity, and handle collisions."""
        global melody_index
        self.vel.y += GRAVITY
        self.pos += self.vel

        for arc in arcs:
            dist_vec = self.pos - arc.pos
            distance = dist_vec.length()
            # Check if the ball is within the radial bounds of the arc
            is_colliding = distance < self.radius + arc.radius and distance > arc.radius - self.radius

            if is_colliding:
                # Check if the collision point is on the arc or in the gap
                angle = math.degrees(math.atan2(-dist_vec.y, dist_vec.x)) % 360
                start_angle = arc.start_angle % 360
                end_angle = arc.end_angle % 360
                on_arc = (start_angle < end_angle and start_angle <= angle <= end_angle) or \
                         (start_angle > end_angle and (angle >= start_angle or angle <= end_angle))

                if on_arc:
                    # Play a note on the first frame of collision with an arc
                    if self.last_collided_arc != arc:
                        note_to_play = MELODY[melody_index]
                        if VIDEO_MODE:
                            audio_events.append((frame_num / FPS, note_to_play))
                        else:
                            notes[note_to_play].play()
                        melody_index = (melody_index + 1) % len(MELODY)
                    self.last_collided_arc = arc

                    # Resolve collision by pushing the ball out and reflecting velocity
                    if distance != 0:
                        overlap = (self.radius + arc.radius - distance) if distance > arc.radius else (self.radius - (arc.radius - distance))
                        self.pos += dist_vec.normalize() * overlap
                    normal = dist_vec.normalize() if dist_vec.length() != 0 else pygame.math.Vector2(0, -1)
                    self.vel = self.vel.reflect(normal) * 0.9 # 0.9 for energy loss
                else: # Ball is in the gap
                    self.last_collided_arc = None
                    # Score a point on the first frame of passing through a gap
                    if self.last_passed_arc != arc:
                        self.score += 1
                        self.last_passed_arc = arc
                        arc.start_breaking()
            else:
                # Reset flags when the ball is no longer colliding with the arc
                if self.last_passed_arc == arc:
                    self.last_passed_arc = None
                if self.last_collided_arc == arc:
                    self.last_collided_arc = None

        # Bounce off the side and top walls
        if self.pos.x - self.radius < 0 or self.pos.x + self.radius > WIDTH:
            self.vel.x *= -1
            self.pos.x = np.clip(self.pos.x, self.radius, WIDTH - self.radius)
        if self.pos.y - self.radius < 0:
            self.vel.y *= -1
            self.pos.y = self.radius


    def draw(self, screen):
        """Draw the ball on the screen."""
        pygame.draw.circle(screen, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)

class CircularArc:
    """Class to represent a rotating circular arc."""
    def __init__(self, x, y, radius, color, start, end, speed):
        self.pos = pygame.math.Vector2(x, y)
        self.radius, self.color, self.start_angle, self.end_angle, self.rotation_speed = radius, color, start, end, speed
        self.is_breaking, self.breaking_timer, self.original_color, self.breaking_color = False, 0, color, YELLOW

    def start_breaking(self):
        """Initiate the breaking effect (color flash)."""
        self.is_breaking, self.breaking_timer = True, 30 # 0.5 seconds at 60fps

    def update(self):
        """Rotate the arc and handle the breaking effect timer."""
        self.start_angle += self.rotation_speed
        self.end_angle += self.rotation_speed
        if self.is_breaking:
            self.breaking_timer -= 1
            if self.breaking_timer <= 0:
                self.is_breaking = False

    def draw(self, screen):
        """Draw the arc on the screen."""
        color = self.breaking_color if self.is_breaking else self.original_color
        rect = pygame.Rect(self.pos.x - self.radius, self.pos.y - self.radius, self.radius * 2, self.radius * 2)
        start_rad, end_rad = math.radians(self.start_angle), math.radians(self.end_angle)
        # Handle drawing arcs that wrap around 360 degrees
        if start_rad > end_rad:
            pygame.draw.arc(screen, color, rect, start_rad, math.radians(360), ARC_WIDTH)
            pygame.draw.arc(screen, color, rect, 0, end_rad, ARC_WIDTH)
        else:
            pygame.draw.arc(screen, color, rect, start_rad, end_rad, ARC_WIDTH)

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
    balls = [Ball(WIDTH // 2 - 100, 100, BALL_RADIUS, RED), Ball(WIDTH // 2 + 100, 100, BALL_RADIUS, BLUE)]
    arcs = [CircularArc(WIDTH // 2, HEIGHT // 2 + 300, ARC_RADIUS, BLUE, 45, 315, 1),
            CircularArc(WIDTH // 2, HEIGHT // 2 + 800, ARC_RADIUS, RED, 90, 270, -1.5)]

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
        for ball in balls:
            ball.update(arcs, notes, frame_num)
        for arc in arcs:
            arc.update()

        # --- Drawing ---
        screen.fill(BACKGROUND_COLOR)
        for ball in balls:
            ball.draw(screen)
        for arc in arcs:
            arc.draw(screen)

        # Draw scores
        score1_text = font.render(f"{balls[0].score}", True, FONT_COLOR)
        score2_text = font.render(f"{balls[1].score}", True, FONT_COLOR)
        screen.blit(score1_text, (50, 50))
        screen.blit(score2_text, (WIDTH - 150, 50))

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
