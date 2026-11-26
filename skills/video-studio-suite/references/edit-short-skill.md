---
name: edit-short
description: Edit video ngắn dọc 1080×1920 từ một video talking-head: phụ đề highlight từng chữ, motion graphics kiểu paper-card (số đếm, checklist tick, khung thiết bị 3D, quạt màn hình, quy trình lật 3D, biểu đồ, stamp, pill CTA), B-roll lồng khung, SFX, render bằng HyperFrames. Có bước duyệt ảnh mẫu trước khi render. Dùng khi user nói "edit short", "edit dọc", "edit vertical", "edit 9:16", "edit reels", "edit tiktok", hoặc đưa một video nói chuyện và muốn thành short có motion graphics.
---

# Edit Short — video dọc có motion graphics

Đầu vào: một video người nói (ngang hoặc dọc, mp4/mov, HEVC cũng được). Đầu ra: `renders/final.mp4` 1080×1920 30 fps, giọng gốc chuẩn hóa + SFX, phụ đề karaoke tiếng Việt, kèm `captions.srt` và báo cáo QA.

Composition là HTML + GSAP, sinh ra từ `scene-plan.json` bằng `scripts/build.py`, render bằng HyperFrames. Style mặc định là light luxe (ivory, ink, plum, pastel), đổi được trong `template/DESIGN.md` và khối CSS đầu `build.py`.

## Yêu cầu máy

- Node.js 22+, FFmpeg + ffprobe trên PATH.
- Python 3.10+: `pip install faster-whisper playwright pillow numpy` rồi `playwright install chromium`.
- HyperFrames CLI qua `npx hyperframes` (đã test 0.8.10). Trên Windows PowerShell gọi `npx.cmd` nếu gặp lỗi execution policy.
- GPU không bắt buộc nhưng render nhanh hơn nhiều.

## Quy trình

Làm đúng thứ tự. Bước 4 luôn dừng chờ user duyệt.

### 1. Hỏi đầu vào

Gom 1 lượt các thông tin còn thiếu: đường dẫn video gốc, tên video, slug thư mục, có brand/palette riêng không, có video tham chiếu muốn học motion không. Không hỏi lại những gì user đã nói.

### 2. Dựng project + transcript

```powershell
$slug = "ten-video"
Copy-Item -Recurse "<SKILL_DIR>/template" "video-projects/$slug"
cd "video-projects/$slug"
# sửa project.json: id = slug, name = tên video
python scripts/prepare.py "<đường dẫn video gốc>"
python scripts/setup_assets.py
python scripts/transcribe.py
```

`prepare.py` luôn re-encode sang H.264 `-g 30`: Chrome không decode HEVC và khung người nói sẽ trắng.

Đọc `assets/transcript.json`. Sửa lỗi nhận dạng rõ ràng (tên riêng, thuật ngữ tiếng Anh) bằng `caption_fixes` trong `project.json`. Không sửa ý, không thêm lời.

### 3. Chia cảnh + interview B-roll (bắt buộc, không bỏ qua)

Chia video thành 8–12 cảnh theo câu. Mỗi cảnh 2–10 giây. Với từng cảnh cần hình minh hoạ, liệt kê cho user:

- cảnh, giây, câu nói;
- đề xuất mặc định: **motion graphics tự dựng** (component trong `references/scene-plan.md`) hoặc **B-roll thật**;
- nếu B-roll thật: ai quay (user tự quay màn hình / quay web public bằng `capture_broll.py` / clip có sẵn), quay gì, dài tối thiểu bao nhiêu giây.

Chờ user chốt từng cảnh rồi mới viết `scene-plan.json`. Trang cần đăng nhập (Facebook, dashboard) thì user tự quay, không tự đăng nhập bằng automation. B-roll user gửi: re-encode H.264 30 fps `-g 30` vào `assets/`.

### 4. Bản mẫu duyệt

```powershell
python scripts/build.py
python scripts/render_samples.py
npx hyperframes lint .
npx hyperframes validate .
```

- `build.py` dừng nếu B-roll ngắn hơn slot.
- `render_samples.py` chụp ảnh hero + ảnh lúc đồ họa vào cho từng cảnh, kiểm tra hình học ở nhiều mốc, ghi `review/index.html`, `review/contact-sheet-*.jpg`, `review/sample-qa.json`.
- Yêu cầu trước khi báo user: lint 0 lỗi, `geometry_failures` rỗng, `javascript_errors` rỗng, cảnh báo tương phản đã xử lý.
- Tự mở contact sheet và vài ảnh hero để xem bằng mắt: chữ không đè nhau, phụ đề 2 dòng, B-roll đúng nội dung, không khung trắng.

Gửi user đường dẫn `review/index.html` và **dừng**. Sửa theo góp ý, chạy lại bước 4 cho tới khi user nói duyệt.

### 5. Âm thanh + render

```powershell
python scripts/sound_mix.py
python scripts/build.py
python scripts/composition_qa.py
npx hyperframes render . --quality high --gpu --browser-gpu --workers 1 --frames-cache-dir "<ổ còn trống>/hf-cache" --output renders/final.mp4
python scripts/final_qa.py
```

- `sound_mix.py` đặt SFX theo cấu trúc cảnh: whoosh ở wipe, pop khi đồ họa/stamp/pill vào, click khi tick, sparkle khi số đếm chạm đích. SFX nằm 12–20 dB dưới giọng. Chạy lại `build.py` để composition dùng `mix-final.wav`.
- `--frames-cache-dir` nên trỏ tới ổ khác ổ hệ thống: cache hỏng trên ổ C từng làm render chết giữa chừng với lỗi ENOENT frame_xxxx.jpg.
- `final_qa.py` phải cho: decode exit 0, 0 khung đen, 0 đoạn đứng hình, lệch âm dưới 1 ms. Xem `renders/frames/FINAL-heroes-*.jpg` và `FINAL-transitions-*.jpg` trước khi báo xong.

### 6. Báo cáo

Gửi đường dẫn MP4, thời lượng, dung lượng, số SFX, kết quả QA, và những gì chưa kiểm được (chưa ai xem hết bằng mắt, chất lượng sau khi nền tảng nén lại).

## Luật kỹ thuật (học từ lỗi thật)

| Lỗi | Cách tránh |
|---|---|
| Khung người nói trắng | Nguồn HEVC. Luôn qua `prepare.py`. |
| Số đếm đứng yên ở 0 khi render | GSAP `onUpdate` không chạy khi seek. Dùng chuỗi giá trị bật tắt theo khung như `counter_frames()` trong `build.py`. |
| Lint `gsap_css_transform_conflict` | Không để `transform: scale(0)` trong CSS rồi tween scale. Dùng `gsap.set` hoặc `fromTo`. |
| Nhãn chữ bị đồ họa 3D đè | Nhãn là phần tử 2D anh em, nằm ngoài vùng `preserve-3d`, cách ≥28 px. |
| Phụ đề nháy hoặc chồng | Mỗi nhóm có `tl.set` opacity 0 cứng khi hết; chữ đổi màu bằng `tl.set` className, không `tl.call`. |
| B-roll đứng hình | Keyframe thưa. Re-encode `-g 30 -keyint_min 30`. |
| Render chết giữa chừng | Đổi `--frames-cache-dir`. |
| Timeline không dừng | Không `repeat:-1`. Float dùng số lần lặp tính từ độ dài cảnh. |

## Tham chiếu

- `references/scene-plan.md`: schema cảnh, bảng component `art`, cách chọn mốc thời gian.
- `template/DESIGN.md`: palette, chữ, bố cục px, luật chuyển động.
- `template/scene-plan.example.json`: plan thật của video 45 giây, 10 cảnh.

Số liệu tham khảo: video 45 giây, 10 cảnh, 57 nhóm phụ đề, 32 SFX, render 5 phút trên laptop RTX 4050 với 1 worker.
