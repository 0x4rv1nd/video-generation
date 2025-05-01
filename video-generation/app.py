from flask import Flask, request, send_file, jsonify
import subprocess
import os
import json
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import textwrap
import re

app = Flask(__name__)

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
FONT_PATH = "Roboto-Italic-VariableFont.ttf"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def get_video_dimensions(video_path):
    cmd = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration", "-of", "json", video_path
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    info = json.loads(result.stdout)
    width = info['streams'][0]['width']
    height = info['streams'][0]['height']
    duration = float(info['streams'][0]['duration'])
    return width, height, duration

def create_quote_image(text, video_width, video_height, output_img_path):
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
    body_text = request.data.decode('utf-8').strip()
    
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

    video_w, video_h, video_duration = get_video_dimensions(input_path)
    create_quote_image(quote_text, video_w, video_h, img_path)

    fade_duration = 1  # seconds
    fade_out_start = max(video_duration - fade_duration, 0)

    cmd = [
        "ffmpeg",
        "-i", input_path,
        "-loop", "1", "-i", img_path,
        "-filter_complex",
        f"[1:v]format=rgba,fade=t=in:st=0:d={fade_duration}:alpha=1,"
        f"fade=t=out:st={fade_out_start}:d={fade_duration}:alpha=1[ov];"
        f"[0:v][ov]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2:shortest=1",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-y", output_video_path
    ]

    try:
        subprocess.run(cmd, check=True)
        return send_file(output_video_path, mimetype="video/mp4")
    except subprocess.CalledProcessError as e:
        return jsonify(error="Failed to overlay image"), 500
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

if __name__ == "__main__":
    app.run(debug=True)
