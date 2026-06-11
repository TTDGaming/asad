# fast_render — render blur + phụ đề SRT siêu nhanh

Tool CLI độc lập (không phụ thuộc web app Asad), bọc quanh **ffmpeg** và tối ưu
cho GPU NVIDIA: **NVDEC decode → blur vùng + burn SRT (CPU đa luồng) → NVENC
encode**. Trên i7-14700KF + RTX 5070 Ti, video 1080p thường render nhanh hơn
realtime nhiều lần.

## Cài đặt

Chỉ cần Python ≥ 3.8 và ffmpeg (bản build có NVENC + libass — bản chuẩn nào
cũng có):

```powershell
winget install Gyan.FFmpeg     # Windows
```

Tool tự smoke-test NVENC lúc khởi động; nếu máy không có GPU NVIDIA sẽ tự
fallback sang CPU (libx264 ultrafast).

## Dùng nhanh

```bash
# Burn phụ đề + blur che logo 300x120 tại toạ độ (20,20)
python tools/fast_render.py input.mp4 -s sub.srt --blur 20,20,300,120 -o out.mp4

# Blur chỉ trong khoảng giây 10→35, kiểu ô vuông (che mặt), nhiều vùng
python tools/fast_render.py input.mp4 \
    --blur 600,40,250,250@10-35 --blur 0,900,400,160 \
    --blur-mode pixel --strength 24 -o out.mp4

# Batch cả thư mục: tự khớp video ↔ .srt cùng tên, chạy 2 file song song
# (RTX 5070 Ti có 2 chip NVENC — 2 job gần như nhân đôi throughput)
python tools/fast_render.py ./videos -s ./subs -o ./out --jobs 2
```

## Tuỳ chọn chính

| Cờ | Mặc định | Ý nghĩa |
|---|---|---|
| `--blur x,y,w,h[@s-e]` | — | Vùng blur (px); lặp lại nhiều lần; `@s-e` giới hạn thời gian (giây) |
| `--blur-mode box\|pixel` | `box` | `box` = mờ mịn (boxblur), `pixel` = ô vuông che (pixelize) |
| `--strength N` | 20 | Bán kính blur / cỡ ô pixel |
| `--codec h264\|hevc\|av1` | `h264` | RTX 50 series encode được cả AV1 |
| `--preset p1…p7` | `p1` | NVENC: p1 nhanh nhất → p7 nét nhất |
| `--cq N` | 23 | Chất lượng (thấp hơn = nét hơn, file to hơn) |
| `--font`, `--font-size`, `--margin`, `--style` | Arial / 24 / 24 | Kiểu phụ đề (ASS force_style) |
| `--jobs N` | 2 | Số file song song khi batch |
| `--cpu` | — | Ép dùng CPU thay vì NVENC |
| `--dry-run` | — | In lệnh ffmpeg để kiểm tra, không chạy |

## Mẹo hiệu suất

- **p1 + cq 23** là điểm "siêu nhanh" mặc định; nếu thấy chất lượng chưa đủ,
  lên `--preset p4` — NVENC vẫn chạy hàng trăm fps ở 1080p, nút thắt thật sự
  là bộ lọc CPU (libass + blur), đã được chia đều cho 20 nhân của 14700KF.
- Batch nhiều file ngắn: `--jobs 2` (hoặc 3–4 nếu file 720p) để bão hoà cả
  hai chip NVENC và toàn bộ nhân CPU.
- `--blur-mode pixel` nhanh hơn `box` một chút và che thông tin tốt hơn.
- Audio luôn được `copy` nguyên trạng — không mất thời gian re-encode.
- Lấy toạ độ vùng blur: mở video trong trình phát (MPC-HC/VLC), chụp màn hình
  và đo bằng Paint; toạ độ tính theo pixel gốc của video.
