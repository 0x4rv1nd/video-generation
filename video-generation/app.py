from flask import Flask, request, send_file, jsonify
import subprocess
import os
from datetime import datetime
import textwrap
import atexit

app = Flask(__name__)

VIDEO_FOLDER = "videos"
OUTPUT_FOLDER = "static/output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def calculate_fontsize(quote, max_width=40):
    length = len(quote)
    if length < 80:
        return 48
    elif length < 150:
        return 40
    elif length < 220:
        return 32
    else:
        return 26

def process_quote(quote, wrap_width=40):
    # Check if the user added line breaks manually
    if '\n' in quote:
        # Preserve user formatting
        escaped = quote.replace("'", r"\'").replace(":", r'\:').replace("\n", r'\\n')
    else:
        # Auto-wrap the text
        wrapped = '\n'.join(textwrap.wrap(quote, width=wrap_width))
        escaped = wrapped.replace("'", r"\'").replace(":", r'\:').replace("\n", r'\\n')
    return escaped

@app.route("/generate", methods=["POST"])
def generate_video():
    data = request.json
    quote_text = data.get("quote", "Your quote goes here")
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

    # Save the quote to a temporary text file
    quote_path = os.path.join(OUTPUT_FOLDER, f"quote_{timestamp}.txt")
    with open(quote_path, "w", encoding="utf-8") as f:
        f.write(quote_text)

    # Set fontsize based on quote length
    fontsize = calculate_fontsize(quote_text)

    ffmpeg_cmd = [
        "ffmpeg",
        "-i", input_video,
        "-vf",
        (
            f"drawtext=textfile='{quote_path}':"
            "fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
            f"fontcolor=white:fontsize={fontsize}:line_spacing=12:"
            "box=1:boxcolor=black@0.5:boxborderw=20:"
            "x=(w-text_w)/2:y=(h-text_h)/2:"
            "escape=char:"
            "enable='between(t,0,20)'"
        ),
        "-codec:a", "copy",
        output_video,
        "-y"
    ]

    try:
        # Run FFmpeg command
        subprocess.run(ffmpeg_cmd, check=True)
        
        # Automatically delete the quote text file after processing
        os.remove(quote_path)
        
        return send_file(output_video, mimetype='video/mp4')
    except subprocess.CalledProcessError as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    # Register clean-up on exit
    atexit.register(lambda: os.remove(quote_path) if os.path.exists(quote_path) else None)
    app.run(debug=True)
