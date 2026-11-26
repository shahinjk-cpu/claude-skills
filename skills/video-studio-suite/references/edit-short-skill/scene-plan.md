# scene-plan.json — schema và thư viện component

Mỗi cảnh là một object. Thời gian tính bằng giây trên video nguồn. Cảnh nối liền nhau: `b` của cảnh này bằng `a` của cảnh sau, cảnh cuối kết thúc đúng thời lượng nguồn. Ví dụ đầy đủ: `template/scene-plan.example.json`.

## Trường chung

| Trường | Bắt buộc | Ý nghĩa |
|---|---|---|
| `id` | có | tên ngắn, không dấu |
| `a`, `b` | có | giây bắt đầu và kết thúc |
| `mode` | có | `split` (đồ họa trên, người nói dưới), `full` hoặc `close` (người nói lớn, không đồ họa; `close` zoom 1.12) |
| `eyebrow` | có | nhãn nhỏ viết hoa trên tiêu đề |
| `title`, `accent` | có | tiêu đề 2 dòng; `accent` màu plum, để `""` nếu chỉ 1 dòng |
| `art` | có | component đồ họa, xem bảng dưới; `none` cho `full`/`close` |
| `label` | không | dòng chữ 2D dưới vùng đồ họa, chỉ có tác dụng ở `split` |
| `heroes` | có | danh sách giây dùng chụp ảnh duyệt, chọn lúc đồ họa đã vào hết |
| `stamps` | không | `[{text, t, x, y, rot}]` tem viền ink pop tại giây `t`, toạ độ px trên khung 1080×1920 |
| `pills` | không | `[{text, t, style: "plum"|"paper"}]` pill CTA pop dưới tiêu đề |

## Component `art`

| `art` | Dùng khi lời thoại nói về | Trường riêng | Chuyển động |
|---|---|---|---|
| `counter` | một con số lớn ở hook | `counter: {from, to, unit, start, duration}` thay cho tiêu đề | số chạy theo từng khung, sparkle khi chạm đích |
| `checklist-empty` | "hệ thống làm được gì", mở danh sách | `card_eyebrow`, `tiles: [[màu, ký tự] x3]` | 3 hàng trượt vào, tile pop |
| `device` | màn hình thật (fanpage, app, web) | `video` (tên file trong assets, không đuôi), `offset` | khung thiết bị nghiêng 3D, xoay chậm |
| `devicefan` | nhiều sản phẩm/video mẫu | `videos: [3 tên file]` | 3 màn hình dọc xòe ra, float nhẹ |
| `posts` | đăng đều, thông báo mới | `posts: [{title, meta}] x3` | 3 thẻ thông báo trượt lên lần lượt |
| `reels` | lưới video ngắn | `cards: [{tint, tag, title}] x3` | 3 thẻ reel xòe, thanh tiến độ chạy |
| `workflow` | quy trình 3 bước | `card_eyebrow`, `steps: [{text, tick, flip?, icon?, mock, mock_title?, repos?, done_text?}] x3` | checklist tick theo `tick`, khung phải lật 3D tại `flip` |
| `chart` | tăng trưởng, kết quả | `counter: {from, to, unit, start, duration, note?}`, `card_eyebrow` | cột mọc, đường vẽ nét, số chạy |
| `none` | cảnh người nói lớn | | chỉ tiêu đề, stamp, pill |

`mock` trong `workflow`: `github` (danh sách repo, đổi bằng `repos: ["owner/name", ...]`), `reader` (AI đọc tài liệu), `editor` (trình dựng video). Bước đầu tiên không có `flip`.

`tint` và màu tile: `lavender`, `sky`, `sage`, `peach`.

## Chọn mốc thời gian

- `tick`, `flip`, `t` của stamp/pill: đặt bằng giây của **từ khoá** trong `assets/transcript.json`, trễ 0.1–0.3 s.
- `counter.start + duration` nên kết thúc ngay khi người nói đọc xong con số.
- Cảnh ngắn dưới 2 s: chỉ dùng `device` hoặc `none`, không đủ thời gian cho component nhiều bước.
- Video B-roll phải đủ dài: `offset + (b - a) ≤ thời lượng file`. `build.py` dừng lại nếu thiếu.
