from flask import Flask, request, send_file, jsonify
import subprocess
import os
import textwrap
import json
from datetime import datetime
from PIL import ImageFont

app = Flask(__name__)

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
ROBOTO_FONT_PATH = "Roboto-Italic-VariableFont.ttf"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

STATIC_FONT_SIZE = 42  # Default font size (will be dynamically adjusted)
LINE_SPACING = 10  # Consistent line spacing

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

def calculate_safe_text_area(video_width, video_height):
    """Calculate the width and height for the text area (7:16 of the video)."""
    text_area_width = int(video_width * (9 / 16))
    text_area_height = video_height  # full height of video
    return text_area_width, text_area_height

def determine_font_size_and_wrap_width(video_width, video_height, text):
    """Determine the optimal font size and wrap width based on video size."""
    text_area_width, text_area_height = calculate_safe_text_area(video_width, video_height)
    
    # Start with a default font size
    fontsize = STATIC_FONT_SIZE
    wrap_width = text_area_width // fontsize  # Start with a calculated line width
    
    # Try to dynamically adjust the font size and wrap width
    font = ImageFont.truetype(ROBOTO_FONT_PATH, fontsize)
    
    while wrap_text(text, wrap_width, fontsize, font)[1] > text_area_height * 0.8:
        fontsize -= 1  # Decrease the font size until the text fits
        wrap_width = text_area_width // fontsize  # Adjust wrap width as we change font size
        font = ImageFont.truetype(ROBOTO_FONT_PATH, fontsize)
    
    return fontsize, wrap_width

def wrap_text(text, wrap_width, fontsize, font):
    """Manually wrap text for FFmpeg drawtext."""
    wrapped_text = textwrap.wrap(text, width=wrap_width)
    lines_count = len(wrapped_text)
    return "\n".join(wrapped_text), lines_count

def calculate_vertical_offset(lines_count, font_size, line_spacing, video_height):
    """Calculate y offset for vertical centering of text."""
    total_text_height = lines_count * font_size + (lines_count - 1) * line_spacing
    return f"(h-{total_text_height})/2"

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

    # Determine optimal font size and wrap width based on video size
    fontsize, wrap_width = determine_font_size_and_wrap_width(video_width, video_height, quote_text)
    wrapped_quote, lines_count = wrap_text(quote_text, wrap_width, fontsize, ImageFont.truetype(ROBOTO_FONT_PATH, fontsize))

    # Write wrapped quote to file
    with open(quote_path, "w", encoding="utf-8") as f:
        f.write(wrapped_quote)

    # Calculate vertical offset for text
    y_offset = calculate_vertical_offset(lines_count, fontsize, LINE_SPACING, video_height)

    # Drawtext filter
    vf_drawtext = (
        f"drawtext=textfile={quote_path}:reload=1:"
        f"fontfile={ROBOTO_FONT_PATH}:"
        f"fontcolor=white:fontsize={fontsize}:line_spacing={LINE_SPACING}:"
        f"box=1:boxcolor=black@0.5:boxborderw=20:"
        f"x=(w-text_w)/2:y={y_offset}:"
        f"enable='between(t,0,20)'"
    )

    # Fade in and fade out filter
    vf_fade = "fade=t=in:st=0:d=1,fade=t=out:st=4:d=1"

    # Combine filters
    vf = f"{vf_drawtext},{vf_fade}"

    # Run FFmpeg command
    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", vf,
        "-codec:a", "copy", output_path,
        "-y"
    ]

    try:
        print("Running command:", " ".join(cmd))
        subprocess.run(cmd, check=True)
        return send_file(output_path, mimetype="video/mp4")
    except subprocess.CalledProcessError as e:
        return jsonify(error=str(e)), 500
    finally:
        if os.path.exists(quote_path):
            os.remove(quote_path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
