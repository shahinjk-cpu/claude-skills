---
name: script-to-video-ai
description: >-
  Hệ thống kỹ năng và quy chuẩn tự hành sản xuất Video AI chất lượng cao từ Kịch bản văn bản.
  Tích hợp Meta Muse (Tạo ảnh nhất quán nhân vật/bối cảnh), Omni Vids (Render video có khẩu hình),
  Bộ não kiểm định thoại 2 chiều (Bidirectional STT Auditor bắt cụt đuôi & lảm nhảm),
  Khóa giọng miền Nam & Kiểm định cao độ giọng trẻ con (Pitch Audit Gatekeeper),
  Snappy Trimming (Gọt sạch dead air), tăng tốc 1.1x giữ nguyên cao độ giọng và tự động đẩy Google Drive.
---

# Script-to-Video AI Production Skill

Hệ thống chuyên sâu tự động hóa toàn diện quy trình chuyển đổi từ **Kịch bản văn bản thuần túy** thành **Video AI 9:16 Full HD** hoàn chỉnh, tối ưu tỷ lệ giữ chân người xem (Audience Retention) trên TikTok, Reels và Shorts.

---

## 🎯 7 NGUYÊN TẮC CỐT LÕI (ALWAYS-ON RULES)

1. **QUY TRÌNH IMAGE-FIRST & MẮT AI SOI DUYỆT:**
   - Luôn tạo ảnh phân cảnh trước bằng mô hình **`meta_muse`**.
   - Bật chế độ kế thừa liên hoàn (`image_chain_mode: "chained"`) để giữ 100% nhất quán về nhân vật, trang phục và bối cảnh.
   - Trích xuất ảnh và dùng Mắt AI (`read_file`) trực tiếp soi đạt chuẩn 10/10 mới được bấm tạo video.

2. **CỔNG KIỂM ĐỊNH THOẠI 2 CHIỀU (BIDIRECTIONAL STT AUDITOR):**
   - **Chiều thuận (Chống nuốt chữ):** Đảm bảo độ phủ từ khóa $\ge 70\%$ và quét đủ 3-5 từ kết thúc câu kịch bản (chống cắt cụt đuôi thoại).
   - **Chiều nghịch (Chống lảm nhảm đuôi):** Quét các từ sau từ khóa kết thúc của kịch bản. Nếu video quá dài khiến AI tự tiện bịa $\ge 2$ từ lạ ➔ Đánh dấu `FAILED` ngay lập tức.
   - **Báo cáo trung thực 100%:** Tuyệt đối cấm làm đẹp số liệu STT hoặc che giấu từ lảm nhảm.
   - **Lệnh chặn cứng (Hard Gatekeeper):** Cấm tuyệt đối ghép video khi có cảnh chưa đạt `PASSED`.

3. **CÔNG THỨC PACING THỜI LƯỢNG CHUẨN XÁC:**
   - Dưới 25 từ: **6s - 8s**
   - 25 - 38 từ: **10s**
   - 39 - 50 từ: **12s**
   - 51 - 65 từ: **15s** (Voice Directing đọc nhanh, dõng dạc)

4. **KHÓA PHƯƠNG NGỮ MIỀN NAM & ĐỒNG BỘ TỪ NGỮ BẢN ĐỊA:**
   - Khi kịch bản yêu cầu giọng miền Nam: Bắt buộc thay thế toàn bộ liên từ/từ nối miền Bắc trong kịch bản và prompt (ví dụ: dùng *"ba với mẹ"* thay vì *"ba và mẹ"*, dùng thán từ *"hả"*, *"nghen"*, *"nhen"*, *"hén"*, *"sao kì dạ"*).
   - Voice Directing song ngữ bắt buộc: `Voice Directing: Giọng phụ nữ miền Nam Sài Gòn ngọt ngào, phát âm chuẩn phương ngữ miền Nam Việt Nam (Authentic Southern Vietnamese Saigon female voice, soft sweet Southern dialect). Cấm tuyệt đối giọng miền Bắc.`

5. **BẢO TOÀN GIỌNG TRẺ CON KHI NÓI CHỦ ĐỀ NGƯỜI LỚN & PITCH AUDIT:**
   - **Cách ly mô tả khỏi thoại (Isolate Prompt from Dialogue):** Tuyệt đối không trích dẫn nội dung triết lý/tiền bạc/sính lễ vào phần mô tả hình ảnh hoặc chuyển động (`[PROMPT]`, `[MOTION]`). Giữ mô tả 100% nét ngây thơ hoạt hình.
   - **Voice Directing khóa giọng trẻ em:** `Voice Directing: Giọng bé trai miền Nam trong trẻo, hồn nhiên, ngây thơ, nói giọng con nít ngọng nghịu đáng yêu (Cute toddler boy child voice). Cấm tuyệt đối giọng người lớn, cấm tuyệt đối giọng nữ trưởng thành.`
   - **Kiểm định Cao độ Pitch ($F_0$ Gate):** Giọng trẻ em bắt buộc đạt $F_0 \ge 250$ Hz (thường 280-350 Hz). Nếu $F_0 < 220$ Hz ➔ Flag `FAILED` ngay, cấm ghép video!

6. **KHÓA KHẨU HÌNH ĐƠN NHÂN VẬT & SHOT PING-PONG:**
   - Mỗi video shot chỉ có duy nhất 1 nhân vật mở miệng phát âm hướng về camera. Các nhân vật phụ mím chặt môi lắng nghe.
   - Cảnh đối thoại từ 2 người trở lên bắt buộc tách thành các shot Ping-pong (1A: Người hỏi, 1B: Người đáp) để chống dính khẩu hình 100%.

7. **QUY TRÌNH HẬU KỲ CHUẨN 4 BƯỚC:**
   - **Snappy Trim:** Dò mốc kết thúc âm tiết bằng STT Binary Search, cắt sát đuôi thoại (+0.15s) kèm micro fade-out 0.15s, loại bỏ 100% dead air.
   - **Re-encode Concat:** Ghép nối bằng libx264 để triệt tiêu lỗi corrupt packet.
   - **Speedup 1.1x (Pitch Preserved):** Tăng tốc 1.1x giữ nguyên 100% cao độ giọng tự nhiên.
   - **Google Drive Sync:** Tự động upload lên Google Drive thư mục chỉ định và dọn dẹp file nặng trên máy.

---

## 🛠️ CẤU TRÚC BỘ SKILL

```text
script-to-video-ai-skill/
├── SKILL.md                 # Định nghĩa kỹ năng cho Antigravity AI Agent
├── PROJECT_RULES.md         # Quy tắc cốt lõi bắt buộc của hệ thống (BỘ NÃO)
├── AGENTS.md                # Hướng dẫn hành vi & phong cách làm việc cho Agent
├── GEMINI.md                # Tài liệu quy chuẩn chi tiết & xử lý sự cố
├── requirements.txt         # Thư viện Python cần thiết
├── scripts/                 # Bộ công cụ thực thi tự động:
│   ├── run_render.py        # Gửi job và giám sát pipeline
│   ├── dialogue_auditor.py  # Bộ não kiểm định thoại STT 2 chiều & Pitch Audit
│   ├── snappy_trimmer.py    # Cắt tỉa dead air bằng STT Binary Search
│   ├── add_footer.py        # Đóng dấu Footer thích ứng độ phân giải
│   ├── gdrive_uploader.py   # Upload video lên Google Drive tự động
│   └── audio_verifier.py    # Hỗ trợ phân tích âm thanh
├── configs/                 # File cấu hình mẫu
│   └── sample_pipeline.json
└── README.md                # Hướng dẫn cài đặt & triển khai từ A - Z
```
