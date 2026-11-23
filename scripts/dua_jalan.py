import argparse
import asyncio
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
from fractions import Fraction

VOICES = ("id-ID-ArdiNeural", "id-ID-GadisNeural")
FIELDS = ("file", "offset_s", "duration_s", "window_start_s", "window_end_s")
GAP = 0.10
MAX_TEMPO = 1.25


def ffmpeg(*args):
    subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-v", "error", *map(str, args)],
        check=True,
    )


def probe(path):
    return json.loads(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)
    ]))


def audio_duration(path):
    if not path.is_file() or not path.stat().st_size:
        raise ValueError(f"Audio kosong: {path}")
    info = probe(path)
    if not any(stream["codec_type"] == "audio" for stream in info["streams"]):
        raise ValueError(f"Stream audio tidak ditemukan: {path}")
    duration = float(info["format"].get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError(f"Durasi audio tidak valid: {path}")
    return duration


async def synthesize(text, voice, path):
    import edge_tts
    from aiohttp import ClientError, WSServerHandshakeError

    for attempt in range(1, 4):
        try:
            path.unlink(missing_ok=True)
            await asyncio.wait_for(edge_tts.Communicate(text, voice).save(str(path)), 45)
            if not path.is_file() or not path.stat().st_size:
                raise edge_tts.exceptions.NoAudioReceived("Audio kosong")
            return
        except (TimeoutError, ClientError, edge_tts.exceptions.EdgeTTSException) as error:
            detail = str(error) or type(error).__name__
            if isinstance(error, WSServerHandshakeError):
                detail = f"WebSocket HTTP {error.status}: {error.message}"
            print(f"{path.name}, percobaan {attempt}/3: {detail}", flush=True)
            if attempt == 3:
                raise ValueError(f"Edge TTS gagal atau audio kosong: {path.name}") from error
            await asyncio.sleep(2 ** attempt)


async def make_scene(text, short, voice, path, limit):
    clips = [(text, False)]
    if short and short != text:
        clips.append((short, True))
    raw = path.with_suffix(".raw.mp3")
    for line, shortened in clips:
        await synthesize(line, voice, raw)
        length = audio_duration(raw)
        if length <= limit:
            raw.replace(path)
            actual = length
        elif length / limit <= MAX_TEMPO:
            estimate = min(MAX_TEMPO, length / (limit - 0.05))
            for tempo in dict.fromkeys((estimate, MAX_TEMPO)):
                ffmpeg("-y", "-i", raw, "-af", f"atempo={tempo:.6f}", "-c:a", "libmp3lame", path)
                actual = audio_duration(path)
                if actual <= limit:
                    break
            else:
                continue
            print(f"{path.name}: tempo {tempo:.3f}×")
        else:
            continue
        if shortened:
            print(f"{path.name}: naskah diringkas dari {text!r} menjadi {line!r}")
        ffmpeg("-xerror", "-i", path, "-map", "0:a:0", "-f", "null", "-")
        return actual
    raise ValueError(f"{path.name}: durasi melebihi slot {limit:.2f} dtk pada tempo maksimum 1,25×")


def window(offset, start, end, previous):
    if not all(math.isfinite(value) for value in (offset, start, end)):
        raise ValueError("Timing harus berupa angka terbatas")
    if not 0 <= previous <= start <= offset < end or end - offset <= GAP + 0.05:
        raise ValueError(f"Jendela adegan tidak valid: {start}, {offset}, {end}")


async def produce(config, folder, voice):
    if voice not in VOICES:
        raise ValueError(f"Suara tidak valid: {voice!r}. Pilih {', '.join(VOICES)}")
    scenes = json.loads(config.read_text(encoding="utf-8"))["scenes"]
    if not scenes:
        raise ValueError("Daftar adegan kosong")
    prepared = []
    previous = 0
    for number, scene in enumerate(scenes, 1):
        start, end = float(scene["start"]), float(scene["end"])
        window(start, start, end, previous)
        previous = end
        original = scene["text"].strip()
        line = os.environ.get(f"DUA_SCENE_{number:02}", original).strip()
        if not line:
            raise ValueError(f"Naskah adegan {number:02} kosong")
        short = scene.get("short", "").strip() if line == original else ""
        prepared.append((f"scene-{number:02}.mp3", start, end, line, short))

    folder.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=folder.parent) as temp:
        staging = Path(temp)
        with (staging / "timing.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            for name, start, end, line, short in prepared:
                duration = await make_scene(line, short, voice, staging / name, end - start - GAP)
                writer.writerow((name, start, duration, start, end))
                print(f"{name}: {duration:.3f} dtk pada {start:.3f} dtk", flush=True)
        folder.mkdir(exist_ok=True)
        for name, *_ in prepared:
            (staging / name).replace(folder / name)
        (staging / "timing.csv").replace(folder / "timing.csv")


def read_narration(folder):
    clips = []
    previous = 0
    with (folder / "timing.csv").open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            name = row["file"]
            if Path(name).name != name or name != f"scene-{len(clips) + 1:02}.mp3":
                raise ValueError(f"Nama atau urutan klip tidak valid: {name!r}")
            offset, start, end = (float(row[key]) for key in ("offset_s", "window_start_s", "window_end_s"))
            window(offset, start, end, previous)
            previous = end
            path = folder / name
            actual = audio_duration(path)
            reported = float(row["duration_s"])
            if not math.isfinite(reported) or abs(actual - reported) > 0.002:
                raise ValueError(f"{name}: durasi aktual berbeda dari timing.csv")
            if offset + actual > end - GAP + 0.000001:
                raise ValueError(f"{name}: durasi melebihi jendela adegan")
            ffmpeg("-xerror", "-i", path, "-map", "0:a:0", "-f", "null", "-")
            clips.append((path, offset, end))
    if not clips:
        raise ValueError("timing.csv tidak berisi adegan")
    return clips


def video_format(stream):
    return stream["width"], stream["height"], Fraction(stream["avg_frame_rate"])


def mix(master, folder, output, expected_video):
    clips = read_narration(folder)
    duration = clips[-1][2]
    streams = probe(master)["streams"]
    video = next((stream for stream in streams if stream["codec_type"] == "video"), None)
    if video is None or not any(stream["codec_type"] == "audio" for stream in streams):
        raise ValueError("Master harus berisi video dan audio ambience")
    width, height, fps = video_format(video)
    if expected_video and expected_video != f"{width}x{height}@{fps}":
        raise ValueError(f"Format master {width}x{height}@{fps}, diharapkan {expected_video}")
    if abs(float(video.get("duration", 0)) - duration) > 0.001:
        raise ValueError(f"Durasi video master harus sama dengan akhir adegan ({duration:g} dtk)")
    if abs(float(video.get("start_time", 0))) > 0.001:
        raise ValueError("Stream video master harus mulai pada 0 detik")
    if output.resolve() == master.resolve():
        raise ValueError("Path output harus berbeda dari master")

    args = ["-i", master]
    filters = ["[0:a:0]aresample=48000:async=1:first_pts=0,aformat=channel_layouts=stereo,volume=0.75[bed]"]
    for index, (path, offset, _) in enumerate(clips, 1):
        args.extend(("-i", path))
        samples = round(offset * 48000)
        filters.append(
            f"[{index}:a:0]aformat=sample_rates=48000:channel_layouts=stereo,"
            f"adelay={samples}S:all=1[n{index}]"
        )
    inputs = "".join(f"[n{index}]" for index in range(1, len(clips) + 1))
    filters.extend((
        f"{inputs}amix=inputs={len(clips)}:normalize=0,"
        f"apad=whole_dur={duration:g},asplit=2[voice][key]",
        "[bed][key]sidechaincompress=threshold=0.015:ratio=5:attack=12:release=220:detection=rms[ducked]",
        f"[ducked][voice]amix=inputs=2:normalize=0,alimiter=limit=0.82:level=false:latency=true,"
        f"apad=whole_dur={duration:g},atrim=duration={duration:g}[audio]",
    ))
    video_args = ["-c:v", "copy"] if video["codec_name"] == "h264" else [
        "-c:v", "libx264", "-crf", "16", "-preset", "medium",
    ]
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as temp:
        staged = Path(temp) / "render.mp4"
        ffmpeg(*args, "-filter_complex", ";".join(filters), "-map", "0:v:0", "-map", "[audio]",
               *video_args, "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", staged)
        result = probe(staged)
        rendered = next(stream for stream in result["streams"] if stream["codec_type"] == "video")
        audio = next(stream for stream in result["streams"] if stream["codec_type"] == "audio")
        if (video_format(rendered) != (width, height, fps) or rendered["codec_name"] != "h264"
                or audio["codec_name"] != "aac"
                or any(abs(float(stream["duration"]) - duration) > 0.001
                       for stream in (rendered, audio, result["format"]))):
            raise ValueError("Format atau durasi render tidak sesuai master dan timing.csv")
        ffmpeg("-xerror", "-i", staged, "-map", "0:a:0", "-f", "null", "-")
        staged.replace(output)
    print(f"{output}: H.264/AAC, {width}×{height}, {fps} fps, {duration:g} dtk")


def main():
    parser = argparse.ArgumentParser(description="Pipeline narasi DUA JALAN")
    commands = parser.add_subparsers(dest="command", required=True)
    tts = commands.add_parser("tts")
    tts.add_argument("config", type=Path)
    tts.add_argument("folder", type=Path)
    tts.add_argument("--voice", default=os.environ.get("DUA_VOICE", VOICES[0]))
    check = commands.add_parser("verify")
    check.add_argument("folder", type=Path)
    check.add_argument("--count", type=int)
    mixing = commands.add_parser("mix")
    mixing.add_argument("master", type=Path)
    mixing.add_argument("folder", type=Path)
    mixing.add_argument("output", type=Path)
    mixing.add_argument("--expect-video", metavar="WIDTHxHEIGHT@FPS")
    args = parser.parse_args()
    try:
        if args.command == "tts":
            asyncio.run(produce(args.config, args.folder, args.voice))
        elif args.command == "verify":
            clips = read_narration(args.folder)
            if args.count is not None and len(clips) != args.count:
                raise ValueError(f"Diharapkan {args.count} klip, ditemukan {len(clips)}")
            print(f"{len(clips)} klip valid dan dapat didekode")
        else:
            mix(args.master, args.folder, args.output, args.expect_video)
    except (ImportError, OSError, ValueError, KeyError, StopIteration, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error or type(error).__name__}\n")


if __name__ == "__main__":
    main()
