"""Render a local Episode 01 master or a clearly labeled test fixture."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile

from dua_jalan import ffmpeg, probe, video_format

ROOT = Path(__file__).resolve().parents[1]
FILENAME = "DUA-JALAN-EP01-Dompet-Rp50-Juta.mp4"


def render(fixture):
    visual = json.loads((ROOT / "episodes/ep01-visuals.json").read_text(encoding="utf-8"))
    public = ROOT / "public"
    if not fixture and not (public / visual["reference"]).is_file():
        raise ValueError(f"Gambar resmi Nara V1 diperlukan di public/{visual['reference']}")
    montage = visual["storyboardArt"]
    art = []
    for scene in visual["scenes"]:
        if (public / scene["art"]).is_file():
            art.append({"file": scene["art"]})
        elif (public / montage).is_file():
            art.append({"file": montage, "panel": scene["panel"]})
        else:
            art.append(None)
    out = ROOT / "outputs" / (f"FIXTURE-{FILENAME}" if fixture else FILENAME)
    out.parent.mkdir(exist_ok=True)
    remotion = ROOT / "node_modules/.bin" / ("remotion.cmd" if os.name == "nt" else "remotion")
    with tempfile.TemporaryDirectory(dir=out.parent) as folder:
        stage = Path(folder)
        props = stage / "props.json"
        props.write_text(json.dumps({"fixture": fixture, "sceneArt": art}), encoding="utf-8")
        video = stage / "picture.mp4"
        staged = stage / "master.mp4"
        command = [
            str(remotion), "render", "src/index.jsx", "Ep01Fixture" if fixture else "Ep01",
            str(video), f"--props={props}", "--codec=h264", "--concurrency=2",
        ]
        if browser := os.environ.get("REMOTION_BROWSER_EXECUTABLE"):
            command.append(f"--browser-executable={browser}")
        subprocess.run(command, cwd=ROOT, check=True)
        ffmpeg(
            "-i", video, "-f", "lavfi", "-i",
            "anoisesrc=r=48000:a=0.15:c=pink:d=15:s=51",
            "-af", "highpass=f=300,lowpass=f=3400,aformat=channel_layouts=stereo",
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-movflags", "+faststart", staged,
        )
        info = probe(staged)
        picture, = (s for s in info["streams"] if s["codec_type"] == "video")
        audio, = (s for s in info["streams"] if s["codec_type"] == "audio")
        if (
            picture["codec_name"] != "h264" or audio["codec_name"] != "aac"
            or video_format(picture) != (1080, 1920, 24)
            or int(picture["nb_frames"]) != 360
            or any(abs(float(s["duration"]) - 15) > 0.001 for s in (picture, audio, info["format"]))
        ):
            raise ValueError("Render harus H.264/AAC, 1080 × 1920, 24 fps dan tepat 15 detik")
        ffmpeg("-xerror", "-i", staged, "-map", "0:a:0", "-f", "null", "-")
        staged.replace(out)
    print(f"{out}: H.264/AAC · 1080 × 1920 · 24 fps · 360 frame · 15,000 detik")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", action="store_true", help="Render komposisi uji berlabel dan tanpa aset resmi")
    options = parser.parse_args()
    try:
        render(options.fixture)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Render gagal: {error}\n")
