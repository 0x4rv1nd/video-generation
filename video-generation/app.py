from flask import Flask, request, jsonify
import subprocess
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
import re

app = Flask(__name__)

# Configuration
VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
FONT_PATH = "Roboto-Italic-VariableFont.ttf"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_video_dimensions(video_path):
    """Get width and height of the input video using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    width = info['streams'][0]['width']
    height = info['streams'][0]['height']
    return width, height

def create_quote_image(text, video_width, video_height, output_img_path):
    """Generate an overlay image with the quote text, centered on transparent background."""
    safe_width = int(video_width * 0.80)
    safe_height = int(video_height * 0.80)

    fontsize = 22
    min_fontsize = 18
    line_spacing = 5

    while fontsize >= min_fontsize:
        font = ImageFont.truetype(FONT_PATH, fontsize)
        wrapper = textwrap.TextWrapper(width=int(safe_width / (fontsize * 0.6)))
        lines = wrapper.wrap(text)
        total_height = len(lines) * (fontsize + line_spacing)
        if total_height <= safe_height:
            break
        fontsize -= 2

    img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    y_text = (video_height - total_height) // 2
    for line in lines:
        text_width, _ = draw.textsize(line, font=font)
        x_text = (video_width - text_width) // 2
        draw.text((x_text, y_text), line, font=font, fill=(255, 255, 255, 255))
        y_text += fontsize + line_spacing

    img.save(output_img_path)

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/generate", methods=["POST"])
def generate():
    """Accepts a plain-text body in the format: "quote" "video.mp4" """
    body_text = request.data.decode('utf-8').strip()

    # Regex to extract: "quote" "video.mp4"
    match = re.match(r'^"([^"]+)"\s+"([^"]+)"$', body_text)
    if not match:
        return jsonify(error="Invalid format. Expected format: \"quote\" \"video.mp4\""), 400

    quote_text = match.group(1)
    video_filename = match.group(2)

    if not quote_text or not video_filename:
        return jsonify(error="Missing quote or video filename"), 400

    input_path = os.path.join(VIDEO_FOLDER, video_filename)
    if not os.path.exists(input_path):
        return jsonify(error="Video not found"), 404

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    img_path = os.path.join(OUTPUT_FOLDER, f"overlay_{ts}.png")
    output_video_path = os.path.join(OUTPUT_FOLDER, f"final_{ts}.mp4")

    video_w, video_h = get_video_dimensions(input_path)
    create_quote_image(quote_text, video_w, video_h, img_path)

    cmd = [
        "ffmpeg", "-i", input_path,
        "-i", img_path,
        "-filter_complex", "overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        "-codec:a", "copy", output_video_path, "-y"
    ]

    try:
        subprocess.run(cmd, check=True)
        public_url = f"{request.url_root}static/output/final_{ts}.mp4"
        return jsonify(video_url=public_url)
    except subprocess.CalledProcessError:
        return jsonify(error="Failed to overlay image"), 500
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

if __name__ == "__main__":
    app.run(debug=True)
