from flask import Flask, request, send_file, jsonify
import subprocess
import os
import uuid
import requests
from urllib.parse import urlparse, unquote
import re

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MUSIC_DIR = os.path.join(BASE_DIR, "music")
TMP_DIR = os.path.join(BASE_DIR, "tmp")

os.makedirs(TMP_DIR, exist_ok=True)

@app.route("/merge", methods=["POST"])
def merge():
    data = request.get_json()

    image_url = data.get("image_url")
    audio_name = data.get("audio_name")

    if not image_url or not audio_name:
        return jsonify({"error": "Missing image_url or audio_name"}), 400

    # Validate and locate audio file
    audio_path = os.path.join(MUSIC_DIR, audio_name)
    if not os.path.isfile(audio_path):
        return jsonify({"error": f"Audio '{audio_name}' not found."}), 404

    # Extract filename from image URL
    parsed_url = urlparse(image_url)
    image_filename = os.path.basename(unquote(parsed_url.path))  # decode %20 etc.
    base_name = os.path.splitext(image_filename)[0]
    output_name = f"{base_name}.mp4"

    # Extract caption from base_name (e.g., replace _ with space, capitalize)
    caption = re.sub(r'[_\-]+', ' ', base_name).strip().capitalize()

    image_path = os.path.join(TMP_DIR, f"{uuid.uuid4().hex}.png")
    output_path = os.path.join(TMP_DIR, output_name)

    try:
        # Download image
        img_data = requests.get(image_url)
        with open(image_path, "wb") as f:
            f.write(img_data.content)

        # FFmpeg command to generate video
        command = [
            "ffmpeg", "-loop", "1", "-i", image_path,
            "-i", audio_path, "-shortest",
            "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p",
            "-y", output_path
        ]
        subprocess.run(command, check=True)

        # Response: video file + caption (to be used in Instagram API later)
        return send_file(output_path, mimetype="video/mp4", as_attachment=True,
                         download_name=output_name)

    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(image_path): os.remove(image_path)
        # (optional) Clean output_path later if needed

@app.route("/", methods=["GET"])
def home():
    return "✅ FFmpeg server is live and ready to create videos!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
