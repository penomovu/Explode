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

The application is now controlled via a graphical user interface (GUI).

To start the application, run:
```bash
python tiktok_game/src/main.py
```

This will open a window with the following options:

### Video Generation
1.  Enter the number of videos you want to create.
2.  Click the "Generate Videos" button.
3.  The application will generate the videos in the background and save them in the `tiktok_game/output/` directory.

### YouTube Uploading
1.  **Authentication (First-time setup):**
    *   Go to the [Google API Console](https://console.developers.google.com/).
    *   Create a new project.
    *   Enable the **YouTube Data API v3**.
    *   Create credentials for an **OAuth client ID**.
    *   Select **Desktop app** as the application type.
    *   Download the JSON credentials file, rename it to `client_secrets.json`, and place it in the root `tiktok_game/` directory of this project.
    *   The first time you try to upload, a browser window will open asking you to authorize the application. After you approve, a `token.pickle` file will be created to store your credentials for future sessions.

2.  **Uploading a Video:**
    *   Click the "Refresh List" button to see the list of generated videos.
    *   Select a video from the list.
    *   Fill in the "Title", "Description", and "Tags" for your video.
    *   Choose a privacy status ("Public", "Private", or "Unlisted").
    *   Click the "Upload Selected Video" button.
