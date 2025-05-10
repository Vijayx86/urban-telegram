import os
import uuid
import shutil
import numpy as np
import cv2
from flask import Flask, render_template, request, send_file
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)

def generate_frames(image, effect_type='blur', duration=10, effect_duration=3, fps=60):
    total_frames = int(duration * fps)
    effect_frames = int(effect_duration * fps)
    frames = []

    height, width, _ = image.shape

    for i in range(total_frames):
        frame = image.copy()
        if i < effect_frames:
            t = i / effect_frames
            if effect_type == 'fade':
                alpha = t
                frame = (frame * alpha).astype(np.uint8)
            elif effect_type == 'blur':
                max_ksize = 151
                k = int((1 - t) * max_ksize)
                if k % 2 == 0:
                    k += 1
                k = max(1, k)
                frame = cv2.GaussianBlur(frame, (k, k), 0)
        frames.append(frame)
    return frames

def save_video(frames, output_path, fps=60):
    height, width, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Use 'avc1' or 'X264' for H.264 if available
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        writer.write(frame)
    
    writer.release()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        uploaded_file = request.files.get("file")
        effect_type = request.form.get("effect", "blur")
        duration = float(request.form.get("duration", 10))
        effect_duration = float(request.form.get("effect_duration", 3))
        fps = int(request.form.get("fps", 60))

        if uploaded_file:
            filename = secure_filename(uploaded_file.filename)

            # Create a unique folder in the current directory
            unique_folder = f"temp_{uuid.uuid4().hex}"
            os.makedirs(unique_folder, exist_ok=True)

            try:
                input_path = os.path.join(unique_folder, f"input_{uuid.uuid4()}_{filename}")
                uploaded_file.save(input_path)

                image = np.array(Image.open(input_path).convert("RGB"))[..., ::-1]  # Convert RGB to BGR
                frames = generate_frames(image, effect_type, duration, effect_duration, fps)

                output_video_path = os.path.join(unique_folder, "effect_video.mp4")
                save_video(frames, output_video_path, fps)

                response = send_file(output_video_path,
                                     as_attachment=True,
                                     download_name="effect_video.mp4",
                                     mimetype="video/mp4")

                @response.call_on_close
                def cleanup_temp_folder():
                    try:
                        shutil.rmtree(unique_folder)
                    except Exception as e:
                        print(f"Error cleaning up folder {unique_folder}: {e}")

                return response

            except Exception as e:
                # Clean up if an error occurs
                if os.path.exists(unique_folder):
                    shutil.rmtree(unique_folder)
                return f"An error occurred: {e}", 500

    return render_template("index.html")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets $PORT automatically
    app.run(host="0.0.0.0", port=port, debug=True)
