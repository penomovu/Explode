import sys
import os

# This is needed so that the script can find the other modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import generate_videos

if __name__ == "__main__":
    print("--- Starting test: Generating one video ---")
    try:
        # We need to make sure the output directory exists, as the GUI would have.
        os.makedirs("tiktok_game/output", exist_ok=True)

        generate_videos(1)
        print("--- Test: Video generation function completed ---")

        # Check if the video file was created
        output_file = "tiktok_game/output/final_video_0.mp4"
        if os.path.exists(output_file):
            print(f"--- Test SUCCESS: Output file '{output_file}' created. ---")
        else:
            print(f"--- Test FAILED: Output file '{output_file}' was not found. ---")
            sys.exit(1) # Exit with error code

    except Exception as e:
        print(f"--- Test FAILED: An exception occurred during video generation ---")
        import traceback
        traceback.print_exc()
        sys.exit(1) # Exit with error code

    print("--- Test script finished successfully. ---")
    sys.exit(0)
