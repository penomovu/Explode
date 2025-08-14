import tkinter as tk
from tkinter import ttk, messagebox
from youtube_uploader import get_authenticated_service, upload_video
import threading
import os

OUTPUT_DIR = "tiktok_game/output"

def start_video_generation_thread():
    from main import generate_videos
    """Wrapper to run video generation in a separate thread to keep the GUI responsive."""
    try:
        num_videos = int(num_videos_entry.get())
        if num_videos <= 0:
            messagebox.showerror("Error", "Please enter a positive number of videos.")
            return

        generate_button.config(state=tk.DISABLED)
        upload_button.config(state=tk.DISABLED)

        messagebox.showinfo("Process Started", f"Generating {num_videos} video(s)... This may take a while.")

        def video_generation_task():
            try:
                generate_videos(num_videos)
                messagebox.showinfo("Success", f"Finished generating {num_videos} video(s).")
                refresh_video_list()
            except Exception as e:
                messagebox.showerror("Error", f"An error occurred during video generation: {e}")
            finally:
                generate_button.config(state=tk.NORMAL)
                upload_button.config(state=tk.NORMAL)

        thread = threading.Thread(target=video_generation_task)
        thread.start()

    except ValueError:
        messagebox.showerror("Error", "Please enter a valid number.")

def start_upload_thread():
    """Wrapper to run the upload process in a separate thread."""
    selected_video_index = video_listbox.curselection()
    if not selected_video_index:
        messagebox.showerror("Error", "Please select a video to upload.")
        return

    video_filename = video_listbox.get(selected_video_index)
    video_path = os.path.join(OUTPUT_DIR, video_filename)

    title = title_entry.get()
    description = desc_entry.get("1.0", tk.END).strip()
    tags = [tag.strip() for tag in tags_entry.get().split(",")]
    privacy = privacy_var.get().lower()

    if not title:
        messagebox.showerror("Error", "Please enter a video title.")
        return

    upload_button.config(state=tk.DISABLED)
    generate_button.config(state=tk.DISABLED)

    messagebox.showinfo("Process Started", f"Uploading '{video_filename}' to YouTube... Please follow the authentication steps in your browser if prompted.")

    def upload_task():
        try:
            youtube_service = get_authenticated_service()
            if youtube_service:
                video_id = upload_video(youtube_service, video_path, title, description, tags, privacy_status=privacy)
                if video_id:
                    messagebox.showinfo("Success", f"Video uploaded successfully! Video ID: {video_id}")
                else:
                    messagebox.showerror("Error", "Upload failed. Check the console for details.")
            else:
                messagebox.showerror("Error", "Could not authenticate with YouTube. Check console for details.")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred during upload: {e}")
        finally:
            upload_button.config(state=tk.NORMAL)
            generate_button.config(state=tk.NORMAL)

    thread = threading.Thread(target=upload_task)
    thread.start()


def refresh_video_list():
    """Clears and repopulates the listbox with videos from the output directory."""
    video_listbox.delete(0, tk.END)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    try:
        files = [f for f in os.listdir(OUTPUT_DIR) if f.startswith("final_video_") and f.endswith(".mp4")]
        for f in sorted(files):
            video_listbox.insert(tk.END, f)
    except Exception as e:
        print(f"Error refreshing video list: {e}")


def create_gui():
    """Creates and runs the main GUI window."""
    global num_videos_entry, generate_button, upload_button, video_listbox, title_entry, desc_entry, tags_entry, privacy_var

    root = tk.Tk()
    root.title("TikTok Video Generator & Uploader")

    main_frame = ttk.Frame(root, padding="10")
    main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

    # --- Generation Frame ---
    gen_frame = ttk.LabelFrame(main_frame, text="Step 1: Generate Videos", padding="10")
    gen_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))

    ttk.Label(gen_frame, text="Number of videos:").grid(row=0, column=0, sticky=tk.W, pady=5)
    num_videos_entry = ttk.Entry(gen_frame, width=10)
    num_videos_entry.grid(row=0, column=1, sticky=tk.W, pady=5)
    num_videos_entry.insert(0, "1")

    generate_button = ttk.Button(gen_frame, text="Generate Videos", command=start_video_generation_thread)
    generate_button.grid(row=0, column=2, padx=5, pady=5)

    # --- Upload Frame ---
    upload_frame = ttk.LabelFrame(main_frame, text="Step 2: Select Video for Upload", padding="10")
    upload_frame.grid(row=1, column=0, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))

    video_listbox = tk.Listbox(upload_frame, height=8, exportselection=False)
    video_listbox.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E))
    refresh_button = ttk.Button(upload_frame, text="Refresh List", command=refresh_video_list)
    refresh_button.grid(row=1, column=0, columnspan=2, pady=5)

    # --- Metadata Frame ---
    meta_frame = ttk.LabelFrame(main_frame, text="Step 3: Set Video Details", padding="10")
    meta_frame.grid(row=1, column=1, pady=10, sticky=(tk.W, tk.E, tk.N, tk.S))

    ttk.Label(meta_frame, text="Title:").grid(row=0, column=0, sticky=tk.W, pady=2)
    title_entry = ttk.Entry(meta_frame, width=40)
    title_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=2)

    ttk.Label(meta_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, pady=2)
    desc_entry = tk.Text(meta_frame, height=4, width=40)
    desc_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=2)

    ttk.Label(meta_frame, text="Tags (comma-separated):").grid(row=2, column=0, sticky=tk.W, pady=2)
    tags_entry = ttk.Entry(meta_frame, width=40)
    tags_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=2)

    ttk.Label(meta_frame, text="Privacy:").grid(row=3, column=0, sticky=tk.W, pady=2)
    privacy_var = tk.StringVar(value="Private")
    privacy_menu = ttk.OptionMenu(meta_frame, privacy_var, "Private", "Private", "Public", "Unlisted")
    privacy_menu.grid(row=3, column=1, sticky=tk.W, pady=2)

    upload_button = ttk.Button(meta_frame, text="Upload Selected Video", command=start_upload_thread)
    upload_button.grid(row=4, column=0, columnspan=2, pady=10)

    # --- Initial State ---
    refresh_video_list()

    root.mainloop()

if __name__ == "__main__":
    create_gui()
