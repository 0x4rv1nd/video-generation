from flask import Flask, request, send_file, jsonify
import subprocess
import os
from datetime import datetime
from urllib.parse import quote

app = Flask(__name__)

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route("/generate", methods=["POST"])
def generate_video():
    data = request.json
    quote = data.get("quote", "Your quote goes here")
    video_filename = data.get("video")

    if not video_filename:
        return jsonify({"error": "Video filename not provided"}), 400

    input_video = os.path.join(VIDEO_FOLDER, video_filename)
    if not os.path.isfile(input_video):
        return jsonify({"error": f"Video file '{video_filename}' not found"}), 404

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_video = os.path.join(
        OUTPUT_FOLDER, f"{os.path.splitext(video_filename)[0]}_{timestamp}.mp4"
    )

# Escape single quotes and format line breaks
escaped_quote = quote(quote_text).replace("%0A", r'\n').replace("'", r"\'")

ffmpeg_cmd = [
    "ffmpeg",
    "-i", input_video,
    "-vf",
    (
        f"drawtext=text='{escaped_quote}':"
        "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        "fontcolor=white:fontsize=32:line_spacing=10:"
        "x=(w-text_w)/2:y=(h-text_h)/2:"
        "box=0:"
        "enable='between(t,0,20)'"
    ),
    "-codec:a", "copy",
    output_video,
    "-y"
]


    try:
        subprocess.run(ffmpeg_cmd, check=True)
        return send_file(output_video, mimetype='video/mp4')
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
