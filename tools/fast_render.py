#!/usr/bin/env python3
"""fast_render — render blur vùng + phụ đề SRT siêu nhanh (ffmpeg + NVENC).

Pipeline được tối ưu cho GPU NVIDIA (RTX 30/40/50):
  NVDEC decode → (blur vùng + burn SRT trên CPU, đa luồng) → NVENC encode

Ví dụ:
  # Burn phụ đề, blur che logo góc trên trái 300x120 tại (20,20)
  python fast_render.py input.mp4 -s sub.srt --blur 20,20,300,120 -o out.mp4

  # Blur chỉ từ giây 10 đến 35, kiểu ô vuông (pixelate), độ mạnh 24
  python fast_render.py input.mp4 --blur 600,40,250,250@10-35 \
      --blur-mode pixel --strength 24 -o out.mp4

  # Batch cả thư mục, 2 file song song (RTX 5070 Ti có 2 chip NVENC)
  python fast_render.py ./videos -s ./subs -o ./out --jobs 2

Chỉ cần Python ≥ 3.8 + ffmpeg trong PATH. Không cần thư viện ngoài.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mkv", ".mov", ".ts", ".webm", ".avi", ".m4v", ".flv"}

NVENC_CODECS = {"h264": "h264_nvenc", "hevc": "hevc_nvenc", "av1": "av1_nvenc"}
CPU_CODECS = {"h264": "libx264", "hevc": "libx265", "av1": "libsvtav1"}


# ---------------------------------------------------------------- ffmpeg utils

def ffmpeg_bin() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        sys.exit("Không tìm thấy ffmpeg trong PATH. Cài tại https://ffmpeg.org "
                 "hoặc: winget install Gyan.FFmpeg")
    return path


_nvenc_cache: dict[str, bool] = {}


def nvenc_works(codec: str) -> bool:
    """Smoke-test thật sự: encode 1 frame đen bằng NVENC.

    Tin cậy hơn việc chỉ đọc `ffmpeg -encoders` vì binary có thể được build
    kèm NVENC nhưng máy không có GPU/driver.
    """
    enc = NVENC_CODECS[codec]
    if enc in _nvenc_cache:
        return _nvenc_cache[enc]
    proc = subprocess.run(
        [ffmpeg_bin(), "-v", "error", "-f", "lavfi", "-i",
         "color=black:s=256x256:d=0.05", "-frames:v", "1",
         "-c:v", enc, "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    _nvenc_cache[enc] = proc.returncode == 0
    return _nvenc_cache[enc]


_DUR_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)")


def probe_duration(path: Path) -> float:
    """Lấy thời lượng (giây). Dùng ffprobe nếu có, fallback parse `ffmpeg -i`."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        proc = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True,
        )
        try:
            return float(proc.stdout.strip())
        except ValueError:
            pass
    proc = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", str(path)],
                          capture_output=True, text=True)
    m = _DUR_RE.search(proc.stderr)
    if not m:
        return 0.0
    h, mi, s, frac = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + float(f"0.{frac}")


def esc_filter_path(path: Path) -> str:
    """Escape đường dẫn cho filter subtitles (Windows: C\\:/x/y.srt)."""
    p = str(path.resolve()).replace("\\", "/")
    return p.replace(":", "\\:").replace("'", "\\'")


# ---------------------------------------------------------------- blur regions

@dataclass
class BlurRegion:
    x: int
    y: int
    w: int
    h: int
    start: float | None = None
    end: float | None = None


def parse_blur(spec: str) -> BlurRegion:
    """'x,y,w,h' hoặc 'x,y,w,h@start-end' (giây, end bỏ trống = hết video)."""
    timing = None
    if "@" in spec:
        spec, timing = spec.split("@", 1)
    try:
        x, y, w, h = (int(v) for v in spec.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--blur '{spec}' sai định dạng, cần x,y,w,h hoặc x,y,w,h@s-e")
    # Làm tròn về số chẵn: crop trên nv12/yuv420p cần toạ độ chia hết cho 2.
    x, y, w, h = (v - v % 2 for v in (x, y, w, h))
    region = BlurRegion(x, y, max(w, 2), max(h, 2))
    if timing:
        s, _, e = timing.partition("-")
        region.start = float(s) if s else 0.0
        region.end = float(e) if e else None
    return region


def blur_filter(mode: str, strength: int, region: BlurRegion) -> str:
    if mode == "pixel":
        # Kích thước ô vuông; không vượt quá nửa cạnh vùng.
        px = max(2, min(strength, region.w // 2, region.h // 2))
        return f"pixelize=w={px}:h={px}"
    # boxblur: 2 lượt cho mượt; bán kính bị giới hạn bởi nửa cạnh vùng.
    radius = max(1, min(strength, region.w // 2 - 1, region.h // 2 - 1))
    return f"boxblur=lr={radius}:lp=2"


# ---------------------------------------------------------------- filter graph

def build_filtergraph(blurs: list[BlurRegion], srt: Path | None,
                      style: str, mode: str, strength: int, gpu: bool) -> str:
    parts: list[str] = []
    cur = "[0:v]"
    if gpu:
        parts.append(f"{cur}hwdownload,format=nv12[v0]")
        cur = "[v0]"
    for i, b in enumerate(blurs):
        enable = ""
        if b.start is not None:
            end = b.end if b.end is not None else 9e8
            enable = f":enable='between(t,{b.start},{end})'"
        parts.append(f"{cur}split=2[bm{i}][bc{i}]")
        parts.append(
            f"[bc{i}]crop={b.w}:{b.h}:{b.x}:{b.y},"
            f"{blur_filter(mode, strength, b)}[bb{i}]")
        parts.append(f"[bm{i}][bb{i}]overlay={b.x}:{b.y}{enable}[vb{i}]")
        cur = f"[vb{i}]"
    if srt is not None:
        parts.append(
            f"{cur}subtitles=filename='{esc_filter_path(srt)}'"
            f":force_style='{style}'[vsub]")
        cur = "[vsub]"
    if gpu:
        parts.append(f"{cur}format=nv12,hwupload_cuda[vout]")
    else:
        parts.append(f"{cur}format=yuv420p[vout]")
    return ";".join(parts)


def build_style(args: argparse.Namespace) -> str:
    style = (f"FontName={args.font},FontSize={args.font_size},Bold=1,"
             f"BorderStyle=1,Outline=2,Shadow=0,MarginV={args.margin},"
             f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000")
    if args.style:
        style += "," + args.style
    return style


# ---------------------------------------------------------------- render core

def build_command(inp: Path, out: Path, graph: str, gpu: bool,
                  args: argparse.Namespace) -> list[str]:
    cmd = [ffmpeg_bin(), "-y", "-hide_banner", "-nostats",
           "-progress", "pipe:1"]
    if gpu:
        cmd += ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda",
                "-extra_hw_frames", "8"]
    cmd += ["-i", str(inp),
            "-filter_complex", graph,
            "-filter_complex_threads", str(os.cpu_count() or 8),
            "-map", "[vout]", "-map", "0:a?",
            "-c:a", "copy"]
    if gpu:
        cmd += ["-c:v", NVENC_CODECS[args.codec],
                "-preset", args.preset, "-tune", "hq",
                "-rc", "vbr", "-cq", str(args.cq), "-b:v", "0",
                "-multipass", "0"]
    else:
        cmd += ["-c:v", CPU_CODECS[args.codec],
                "-preset", "ultrafast" if args.codec == "h264" else "fast",
                "-crf", str(args.cq)]
    if args.faststart:
        cmd += ["-movflags", "+faststart"]
    cmd += [str(out)]
    return cmd


_PROG_RE = re.compile(rb"(\w+)=\s*([^\s]+)")


def render_one(inp: Path, srt: Path | None, out: Path,
               args: argparse.Namespace, gpu: bool,
               show_bar: bool = True) -> tuple[Path, bool, float, str]:
    """Chạy 1 job render. Trả về (input, ok, giây-đã-chạy, thông-điệp)."""
    graph = build_filtergraph(args.blur, srt, build_style(args),
                              args.blur_mode, args.strength, gpu)
    cmd = build_command(inp, out, graph, gpu, args)
    if args.dry_run:
        print(" ".join(f'"{c}"' if " " in c else c for c in cmd))
        return inp, True, 0.0, "dry-run"

    duration = probe_duration(inp)
    t0 = time.monotonic()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    fps = speed = "?"
    assert proc.stdout is not None
    for raw in proc.stdout:
        kv = dict(_PROG_RE.findall(raw))
        if b"fps" in kv:
            fps = kv[b"fps"].decode()
        if b"speed" in kv:
            speed = kv[b"speed"].decode()
        if show_bar and b"out_time_us" in kv and duration > 0:
            try:
                done = int(kv[b"out_time_us"]) / 1e6 / duration
            except ValueError:
                continue
            done = min(done, 1.0)
            bar = "#" * int(done * 30)
            sys.stdout.write(f"\r  [{bar:<30}] {done * 100:5.1f}%  "
                             f"fps={fps:<7} speed={speed:<8}")
            sys.stdout.flush()
    proc.wait()
    elapsed = time.monotonic() - t0
    if show_bar:
        sys.stdout.write("\n")
    if proc.returncode != 0:
        err = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
        tail = "\n".join(err.strip().splitlines()[-4:])
        return inp, False, elapsed, tail
    mult = f"{duration / elapsed:.1f}x realtime" if duration else ""
    return inp, True, elapsed, mult


# ---------------------------------------------------------------- batch / main

def find_srt(video: Path, srt_arg: Path | None) -> Path | None:
    """Tìm file .srt cùng tên: ưu tiên thư mục --srt, rồi cạnh video."""
    candidates = []
    if srt_arg is not None:
        if srt_arg.is_file():
            return srt_arg
        candidates.append(srt_arg / f"{video.stem}.srt")
    candidates.append(video.with_suffix(".srt"))
    return next((c for c in candidates if c.exists()), None)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", type=Path,
                    help="File video hoặc thư mục (batch mode)")
    ap.add_argument("-o", "--out", type=Path, required=True,
                    help="File output, hoặc thư mục khi batch")
    ap.add_argument("-s", "--srt", type=Path, default=None,
                    help="File .srt, hoặc thư mục chứa .srt cùng tên (batch)")
    ap.add_argument("--blur", type=parse_blur, action="append", default=[],
                    metavar="x,y,w,h[@s-e]",
                    help="Vùng blur; lặp lại được; @s-e giới hạn thời gian (giây)")
    ap.add_argument("--blur-mode", choices=["box", "pixel"], default="box",
                    help="box = mờ mịn, pixel = ô vuông che (mặc định: box)")
    ap.add_argument("--strength", type=int, default=20,
                    help="Độ mạnh blur / cỡ ô pixel (mặc định: 20)")
    ap.add_argument("--codec", choices=["h264", "hevc", "av1"], default="h264",
                    help="Codec output (mặc định: h264 — tương thích nhất)")
    ap.add_argument("--preset", default="p1",
                    choices=[f"p{i}" for i in range(1, 8)],
                    help="NVENC preset: p1 nhanh nhất → p7 nét nhất (mặc định: p1)")
    ap.add_argument("--cq", type=int, default=23,
                    help="Chất lượng CQ/CRF, thấp = nét hơn (mặc định: 23)")
    ap.add_argument("--font", default="Arial")
    ap.add_argument("--font-size", type=int, default=24)
    ap.add_argument("--margin", type=int, default=24,
                    help="Khoảng cách phụ đề tới mép dưới (mặc định: 24)")
    ap.add_argument("--style", default="",
                    help="Thêm ASS force_style thô, ví dụ 'Italic=1,MarginL=40'")
    ap.add_argument("--jobs", type=int, default=2,
                    help="Số file render song song khi batch (mặc định: 2 — "
                         "RTX 5070 Ti có 2 chip NVENC)")
    ap.add_argument("--cpu", action="store_true",
                    help="Ép dùng CPU (libx264) thay vì NVENC")
    ap.add_argument("--faststart", action="store_true",
                    help="+faststart cho mp4 phát streaming (chậm hơn chút lúc cuối)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Chỉ in lệnh ffmpeg, không chạy")
    args = ap.parse_args()

    if not args.blur and args.srt is None:
        ap.error("Cần ít nhất --blur hoặc --srt (không có gì để render).")

    gpu = (not args.cpu) and nvenc_works(args.codec)
    if not args.cpu and not gpu:
        print("⚠ NVENC không khả dụng (thiếu GPU/driver?) — fallback CPU "
              f"({CPU_CODECS[args.codec]}).", file=sys.stderr)
    elif gpu:
        print(f"✔ NVENC OK → {NVENC_CODECS[args.codec]}, preset {args.preset}")

    if args.input.is_dir():
        videos = sorted(p for p in args.input.iterdir()
                        if p.suffix.lower() in VIDEO_EXTS)
        if not videos:
            sys.exit(f"Không thấy video nào trong {args.input}")
        args.out.mkdir(parents=True, exist_ok=True)
        jobs = max(1, args.jobs)
        print(f"Batch {len(videos)} file, {jobs} job song song…")
        ok = failed = 0
        t0 = time.monotonic()
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(render_one, v, find_srt(v, args.srt),
                            args.out / f"{v.stem}.mp4", args, gpu,
                            show_bar=False): v
                for v in videos
            }
            for fut in as_completed(futures):
                inp, success, elapsed, msg = fut.result()
                mark = "✔" if success else "✘"
                print(f"  {mark} {inp.name}  ({elapsed:.1f}s)  {msg}")
                ok += success
                failed += not success
        print(f"Xong: {ok} OK, {failed} lỗi, tổng {time.monotonic() - t0:.1f}s")
        sys.exit(1 if failed else 0)

    srt = find_srt(args.input, args.srt) if args.srt else None
    if args.srt and srt is None:
        sys.exit(f"Không tìm thấy file SRT: {args.srt}")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    print(f"Render {args.input.name} → {args.out}")
    _, success, elapsed, msg = render_one(args.input, srt, args.out, args, gpu)
    if not success:
        sys.exit(f"✘ ffmpeg lỗi:\n{msg}")
    print(f"✔ Xong sau {elapsed:.1f}s  {msg}")


if __name__ == "__main__":
    main()
