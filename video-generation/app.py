from flask import Flask, request, send_file, jsonify
import subprocess
import os
from datetime import datetime
import textwrap

app = Flask(__name__)

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def calculate_fontsize(quote, max_width=40):
    length = len(quote)
    if length < 100:
        return 60  # Larger font for short quotes
    elif length < 200:
        return 48  # Moderate font size for medium-length quotes
    elif length < 300:
        return 36  # Smaller font for longer quotes
    else:
        return 24  # Very small font for long quotes

def process_quote_for_wrapping(quote, wrap_width=40):
    # Only wrap if no manual line breaks
    if '\n' in quote:
        return quote
    return '\n'.join(textwrap.wrap(quote, width=wrap_width))

@app.route("/generate", methods=["POST"])
def generate_video():
    data = request.json
    quote_text = data.get("quote", "Your quote goes here")
    video_filename = data.get("video")
    if not video_filename:
        return jsonify(error="Video filename not provided"), 400

    input_path = os.path.join(VIDEO_FOLDER, video_filename)
    if not os.path.isfile(input_path):
        return jsonify(error=f"Video file '{video_filename}' not found"), 404

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(video_filename)[0]}_{ts}.mp4")
    quote_path  = os.path.join(OUTPUT_FOLDER, f"quote_{ts}.txt")

    # 1) Prepare the text file
    wrapped = process_quote_for_wrapping(quote_text)
    with open(quote_path, "w", encoding="utf-8") as f:
        f.write(wrapped)

    fontsize = 20

    vf = (
        f"drawtext=textfile={quote_path}:reload=1:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontcolor=white:fontsize={fontsize}:line_spacing=12:"
        f"box=1:boxcolor=black@0.5:boxborderw=20:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:"
        f"enable='between(t,0,20)'"
    )

    try:
        subprocess.run(
            ["ffmpeg", "-i", input_path, "-vf", vf, "-codec:a", "copy", output_path, "-y"],
            check=True,
        )
        return send_file(output_path, mimetype="video/mp4")
    except subprocess.CalledProcessError as e:
        return jsonify(error=str(e)), 500
    finally:
        # always remove the temp text file
        if os.path.exists(quote_path):
            os.remove(quote_path)

if __name__ == "__main__":
    app.run(debug=True)
