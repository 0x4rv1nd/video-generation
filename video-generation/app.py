from flask import Flask, request, send_file, jsonify
import subprocess
import os
from datetime import datetime
import textwrap

app = Flask(__name__)

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Path to the Roboto font you uploaded
ROBOTO_FONT_PATH = "Roboto-Italic-VariableFont.ttf"

def process_quote_for_wrapping(quote, wrap_width=40):
    if '\n' in quote:
        return quote
    return '\n'.join(textwrap.wrap(quote, width=wrap_width))

def calculate_fontsize_from_longest_line(wrapped_quote, base_size=60, max_width_chars=40):
    longest_line_length = max(len(line) for line in wrapped_quote.split('\n'))
    scale_factor = min(1.0, max_width_chars / longest_line_length)
    return int(base_size * scale_factor)

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

    # Process and save wrapped quote
    wrapped = process_quote_for_wrapping(quote_text)
    with open(quote_path, "w", encoding="utf-8") as f:
        f.write(wrapped)

    # Determine font size based on the longest line
    fontsize = calculate_fontsize_from_longest_line(wrapped)

    # Define drawtext filter with fade-in/out (enable from 1s to 5s)
    vf = (
    f"drawtext=textfile={quote_path}:reload=1:"
    f"fontfile={ROBOTO_FONT_PATH}:"
    f"fontcolor=white:fontsize={fontsize}:line_spacing=12:"
    f"box=1:boxcolor=black@0.5:boxborderw=20:"
    f"x=(w-text_w)/2:y=(h-text_h)/2:"
    f"wrap=word:max_text_width=w*0.8:"
    f"enable='between(t,1,5)',"
    f"fade=t=in:st=1:d=1,fade=t=out:st=4:d=1"
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
        if os.path.exists(quote_path):
            os.remove(quote_path)

if __name__ == "__main__":
    app.run(debug=True)
