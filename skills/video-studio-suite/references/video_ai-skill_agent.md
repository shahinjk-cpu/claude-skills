---
name: goi-hon
description: Câu thần chú đổi API key / nhà cung cấp (ảnh, giọng đọc, nhạc, video) — mở popup NGAY để user chọn provider khác hoặc dán key mới. Dùng khi user nói "gọi hồn", "gọi hồn đứa khác", "credit cháy rồi", "cháy credit", "hết credit", "hết tiền rồi", "đổi provider", "đổi nhà cung cấp", "đổi key", "thay key", "key lỗi", "triệu hồi provider", hoặc câu thần chú tương tự.
---

# Gọi hồn provider 🔮

User đọc thần chú → **mở popup ngay**, không hỏi lại, không giải thích trước. Popup tự dẫn từng bước:
**1/3** chọn nhà (có 3 nhà miễn phí + "Khác — tự thêm" cho nhà có API tương thích OpenAI) → **2/3** "Đã có key chưa?" — *Có rồi* → nhập key · *Chưa / chưa biết lấy ở đâu* → hướng dẫn lấy key của đúng nhà đó + nút **🌐 Mở trang lấy key** → bấm **Hoàn tất** → **3/3** ô nhập key (ẩn) + tuỳ chọn đặt làm mặc định. Nội dung hướng dẫn: `_tools/providers.json` (sửa / thêm nhà ở đó).

1. Đáp 1 câu thần chú + chạy popup cùng lúc (popup hiện đủ nhà cung cấp, kể cả nhà đang dùng để dán key mới):
   ```bash
   M=$(python3 "$CLAUDE_PROJECT_DIR/_tools/spells.py" "" manual); echo "🔮 $M"; sh "$CLAUDE_PROJECT_DIR/_tools/pick-provider.sh" image "$M"
   ```
   User nói rõ nhà vừa hỏng (VD "credit OpenAI cháy rồi") → dùng câu riêng của nhà đó: `spells.py openai credit`, và loại nhà đó khỏi danh sách: thêm đối số `openai` cuối lệnh `pick-provider.sh`.
2. Dòng cuối stdout = nhà đã chọn → kiểm key: `python3 "$CLAUDE_PROJECT_DIR/_tools/gen-image.py" --check --provider <nhà>`.
3. Báo đúng 1–2 dòng: "🔮 Đã gọi hồn **[nhà]** (key OK · mặc định / chỉ lần này)". Đang dở việc gen ảnh → chạy lại đúng ảnh bị lỗi bằng `--provider <nhà>`.
4. User bấm Huỷ → "Huỷ phép, giữ nguyên nhà cũ." Không làm gì thêm.

Chọn nhóm theo lời user / việc đang dở (đối số đầu của `pick-provider.sh`):
- `image` (mặc định) — `gen-image.py`: openai, gemini, fal, replicate + miễn phí cloudflare, pollinations, huggingface; cộng nhà user tự thêm (`~/.config/ai-studio/providers-custom.json`, chỉ cho ảnh).
- `voice` — "đổi nhà giọng đọc", "ElevenLabs hết ký tự"… → `gen-voice.py`: elevenlabs, openai_tts + miễn phí gemini_tts, cloudflare_aura, cloudflare_melo.
- `music` — `gen-music.py`: elevenlabs_music, replicate_music.
- `video` — "đổi nhà video", "fal hết credit"… → `gen-video.py`: fal_video, replicate_video, gemini_veo.
Bước 2 kiểm key: ảnh → `gen-image.py --check --provider <nhà>`; nhóm khác → `python3 _tools/key-status.py --all`. Đang dở việc gen → chạy lại đúng file lỗi bằng `--provider <nhà>`.
Key TopView / Higgsfield → `sh "$CLAUDE_PROJECT_DIR/_tools/set-key.sh" TÊN_KEY "gợi ý"` (popup ẩn). Không bao giờ nhận key qua chat.
