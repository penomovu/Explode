# TikTok Bouncing Ball Game

This project is a recreation of a viral TikTok video format, as described in the YouTube video "recoder ces tiktoks débiles pour voir si ça paie". It's a Python application using Pygame that simulates balls bouncing between rotating circular arcs, plays music on each bounce, and can automatically generate videos of the gameplay.

## Features

*   Physics-based simulation of bouncing balls with gravity.
*   Rotating circular arcs with gaps.
*   A scoring system that rewards balls for passing through gaps.
*   Two competing balls of different colors.
*   Programmatically generated music that plays on each bounce.
*   Automated video generation of the gameplay, with a "viral" text overlay.

## Project Structure

*   `src/main.py`: The main source code for the game.
*   `requirements.txt`: A list of the Python packages required to run the project.
*   `output/`: The directory where the generated videos are saved.
*   `assets/`: This directory is currently unused but was intended for music and sound files.

## Installation

1.  Clone the repository.
2.  Install the required Python packages using pip:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The application has two modes, controlled by the `VIDEO_MODE` constant in `src/main.py`.

### Interactive Mode

To play the game interactively, set `VIDEO_MODE = False` in `src/main.py`. Then run the script:

```bash
python src/main.py
```

### Video Generation Mode

To automatically generate a video, set `VIDEO_MODE = True`. This is the default setting. When you run the script in this mode, it will simulate the game for a fixed duration and save the output as `output/final_video.mp4`.

```bash
python src/main.py
```
