from flask import Flask, request, send_file, jsonify
import subprocess
import os
import textwrap
import json
from datetime import datetime

app = Flask(__name__)

# Paths
VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
ROBOTO_FONT_PATH = "Roboto-Italic-VariableFont.ttf"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_video_dimensions(video_path):
    """Use ffprobe to get video width and height."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    width = info['streams'][0]['width']
    height = info['streams'][0]['height']
    return width, height

def determine_wrap_width(video_width, quote_length):
    """Adjust wrap width depending on video width and quote length."""
    if video_width >= 1080:
        base = 35
    elif video_width >= 720:
        base = 30
    else:
        base = 25

    if quote_length > 200:
        return base - 5
    elif quote_length > 120:
        return base - 3
    else:
        return base

def process_quote_for_wrapping(quote, wrap_width):
    """Wrap text and count number of lines."""
    if '\n' in quote:
        lines = []
        for line in quote.splitlines():
            lines.extend(textwrap.wrap(line, width=wrap_width))
    else:
        lines = textwrap.wrap(quote, width=wrap_width)
    return '\n'.join(lines), len(lines)

def calculate_vertical_offset(lines_count, font_size, line_spacing):
    """Center text vertically in video."""
    total_text_height = lines_count * font_size + (lines_count - 1) * line_spacing
    return f"(h-{total_text_height})/2"

def get_dynamic_font_and_spacing(lines_count, video_height):
    """Dynamically determine font size and spacing."""
    max_ratio = 0.55  # Use up to 55% of screen height
    available_height = video_height * max_ratio

    lines_count = max(1, lines_count)
    font_size = int(available_height / (lines_count + (lines_count - 1) * 0.25))
    font_size = max(18, min(font_size, 60))
    line_spacing = int(font_size * 0.2)

    return font_size, line_spacing

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
    quote_path = os.path.join(OUTPUT_FOLDER, f"quote_{ts}.txt")

    # Get video size
    video_width, video_height = get_video_dimensions(input_path)
    print(f"Video size: {video_width}x{video_height}")

    wrap_width = determine_wrap_width(video_width, len(quote_text))
    wrapped_quote, lines_count = process_quote_for_wrapping(quote_text, wrap_width)

    # Clamp long quotes
    if lines_count > 14:
        return jsonify(error="Quote is too long to fit in the video. Please shorten it."), 400

    with open(quote_path, "w", encoding="utf-8") as f:
        f.write(wrapped_quote)

    fontsize, line_spacing = get_dynamic_font_and_spacing(lines_count, video_height)
    y_offset = calculate_vertical_offset(lines_count, fontsize, line_spacing)

    # Drawtext filter
    vf_drawtext = (
        f"drawtext=textfile={quote_path}:reload=1:"
        f"fontfile={ROBOTO_FONT_PATH}:"
        f"fontcolor=white:fontsize={fontsize}:line_spacing={line_spacing}:"
        f"box=1:boxcolor=black@0.5:boxborderw=20:"
        f"x=(w-text_w)/2:y={y_offset}:"
        f"enable='between(t,0,20)'"
    )

    # Fade filters
    vf_fade = "fade=t=in:st=0:d=1,fade=t=out:st=4:d=1"
    vf = f"{vf_drawtext},{vf_fade}"

    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", vf,
        "-codec:a", "copy", output_path,
        "-y"
    ]

    try:
        print("Running FFmpeg command:\n", " ".join(cmd))
        subprocess.run(cmd, check=True)
        return send_file(output_path, mimetype="video/mp4")
    except subprocess.CalledProcessError as e:
        return jsonify(error=str(e)), 500
    finally:
        if os.path.exists(quote_path):
            os.remove(quote_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
