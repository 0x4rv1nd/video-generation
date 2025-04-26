from flask import Flask, request, send_file, jsonify
import subprocess
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap

app = Flask(__name__)

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
FONT_PATH = "Roboto-Italic-VariableFont.ttf"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_video_dimensions(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    width = info['streams'][0]['width']
    height = info['streams'][0]['height']
    return width, height

def generate_text_image(text, output_path, video_width, video_height):
    # Define 1:1 canvas, safe text area (7:16 inside 9:16)
    canvas_size = min(video_width, video_height)
    image_size = (canvas_size, canvas_size)
    safe_width = int(canvas_size * (7 / 9))  # 7:16 safe area horizontally

    img = Image.new("RGBA", image_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Load font
    font_size = 40
    font = ImageFont.truetype(FONT_PATH, font_size)

    # Word wrapping
    wrapped_text = textwrap.fill(text, width=35)

    # Recalculate font size if text is too long
    lines = wrapped_text.count("\n") + 1
    max_lines = 14
    while lines > max_lines:
        font_size -= 2
        font = ImageFont.truetype(FONT_PATH, font_size)
        wrapped_text = textwrap.fill(text, width=35)
        lines = wrapped_text.count("\n") + 1

    # Measure and center
    text_width, text_height = draw.multiline_textsize(wrapped_text, font=font, spacing=10)
    x = (image_size[0] - text_width) / 2
    y = (image_size[1] - text_height) / 2

    # Draw semi-transparent box
    box_padding = 20
    draw.rectangle(
        [x - box_padding, y - box_padding,
         x + text_width + box_padding, y + text_height + box_padding],
        fill=(0, 0, 0, 180)
    )

    # Draw text
    draw.multiline_text((x, y), wrapped_text, font=font, fill="white", spacing=10, align="center")
    img.save(output_path, "PNG")

def overlay_text_on_video(video_path, image_path, output_path):
    cmd = [
        "ffmpeg", "-i", video_path, "-i", image_path,
        "-filter_complex",
        "[1:v]format=rgba,fade=t=in:st=0:d=1:alpha=1,fade=t=out:st=4:d=1:alpha=1[ov];"
        "[0:v][ov]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        "-c:a", "copy", "-y", output_path
    ]
    subprocess.run(cmd, check=True)

@app.route("/generate", methods=["POST"])
def generate_video():
    data = request.json
    quote = data.get("quote", "Your quote here")
    video_filename = data.get("video")

    if not video_filename:
        return jsonify(error="Video filename not provided"), 400

    input_path = os.path.join(VIDEO_FOLDER, video_filename)
    if not os.path.isfile(input_path):
        return jsonify(error=f"Video file '{video_filename}' not found"), 404

    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    image_path = os.path.join(OUTPUT_FOLDER, f"text_{ts}.png")
    output_path = os.path.join(OUTPUT_FOLDER, f"{os.path.splitext(video_filename)[0]}_{ts}.mp4")

    video_width, video_height = get_video_dimensions(input_path)
    generate_text_image(quote, image_path, video_width, video_height)
    overlay_text_on_video(input_path, image_path, output_path)

    return send_file(output_path, mimetype="video/mp4")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
