import base64
import json
from pathlib import Path

img_path = Path("kich_ban_to_video/inputs/product_tra_la_mam_xoi.jpg")
b64_data = base64.b64encode(img_path.read_bytes()).decode("utf-8")
data_uri = f"data:image/jpeg;base64,{b64_data}"

NANG_DAU = "[LOCK: NANG_DAU: beautiful 25yo Vietnamese woman, neat shoulder-length hair behind ears, soft facial features, fair skin, pastel silk lounge homewear]"
ME_CHONG = "[LOCK: ME_CHONG: gentle 55yo Vietnamese woman, kind wise face with subtle wrinkles, neat low bun hair, dark green traditional modern casual outfit]"
BOI_CANH = "[LOCK: BOI_CANH: cozy warm Vietnamese home interior, wooden furniture, gentle sunlight filtering through window, warm ambient lighting]"
STYLE = "vietnamese 3D animation, stylized realism, Pixar-style character design, cinematic lighting, warm ambient glow, expressive facial animations, 8k resolution, vertical 9:16. No text, no subtitles, no logo, no watermark."

config = {
    "mode": "image_to_video",
    "image_chain_mode": "chained",
    "image_model": "meta_muse",
    "video_model": "omni_vids",
    "video_length": 15,
    "aspect_ratio": "9:16",
    "resolution": "720p",
    "remove_logo": True,
    "auto_merge": True,
    "merge_resolution": "1080p",
    "custom_name": "Series Bung Duoi Phinh - Khong Phai Do An",
    "custom_scene_refs": {
        "5": [data_uri, "", "", ""]
    },
    "image_prompts": [
        f"{NANG_DAU} {ME_CHONG} {BOI_CANH}. NANG_DAU sitting at the dining table, holding a glass of plain water, looking down at her bloated lower belly with a confused and helpless expression. ME_CHONG sitting across from her, gently shaking her head with a sharp but caring look. {STYLE}",
        f"{ME_CHONG} {NANG_DAU} {BOI_CANH}. Close up shot of ME_CHONG placing her hands gently on her own lower belly to demonstrate. NANG_DAU stands beside her, looking closely and listening attentively. {STYLE}",
        f"{ME_CHONG} {NANG_DAU} {BOI_CANH}. ME_CHONG pointing her finger gently towards NANG_DAU lower belly. NANG_DAU touches her own belly, nodding with a worried expression. {STYLE}",
        f"{NANG_DAU} {ME_CHONG} {BOI_CANH}. NANG_DAU sitting slouched at a wooden desk, looking at a smartphone, a glass of iced water nearby. ME_CHONG steps up from behind, gently placing a hand on her shoulder. {STYLE}",
        f"{ME_CHONG} {NANG_DAU} {BOI_CANH} [LOCK: SAN_PHAM: exact authentic box of herbal tea Tra La Mam Xoi Moc Tra on table matching reference image]. ME_CHONG smiling warmly, handing a steaming cup of herbal tea to NANG_DAU. The box of herbal tea is placed clearly on the wooden table next to them. NANG_DAU takes the cup, smiling with a relaxed, happy expression. {STYLE}"
    ],
    "video_prompts": [
        "Nàng dâu cầm ly nước lọc uống một ngụm, rồi cúi xuống sờ cái bụng dưới đang nhô ra, mặt mày ngơ ngác bất lực. Mẹ chồng ngồi đối diện, lắc đầu cười nhẹ đầy tinh ý. Voice Directing: Đối thoại gia đình miền Nam Việt Nam chuẩn. Nàng dâu giọng trẻ ngơ ngác oan ức, mẹ chồng giọng điềm tĩnh chắc nịch. Dialogue: \"Con thề luôn á, sáng giờ con uống có ly nước lọc thôi mà cái bụng nó cũng sưng vù lên là sao ta? Uống nước mà cũng sưng vầy thì chắc chắn không phải mỡ thừa đâu, để mẹ coi.\"",
        "Mẹ chồng đứng lên, đặt hai tay lên bụng mình làm mẫu, cử động chậm rãi, dứt khoát. Nàng dâu chớp mắt, gật gù chăm chú nhìn theo tay mẹ. Voice Directing: Giọng nữ miền Nam Việt Nam (mẹ chồng), tông chậm, trầm ấm, mang tính giải thích và chia sẻ kinh nghiệm rành rọt. Dialogue: \"Cái này là người bị lạnh từ trong. Lạnh lâu ngày, khí huyết chậm lại, bụng dưới nó giữ nước giữ hàn.\"",
        "Mẹ chồng chỉ tay nhẹ xuống dưới. Nàng dâu sờ nắn nhẹ bụng mình, chân mày hơi nhíu lại, gật đầu xác nhận triệu chứng mẹ nói là đúng. Voice Directing: Giọng nữ miền Nam Việt Nam (mẹ chồng), nhịp điệu nhanh hơn một chút, nhấn mạnh vào các triệu chứng để cảnh báo nhưng vẫn giữ sự ân cần. Dialogue: \"Ban đầu chỉ phình chút thôi. Để lâu là bụng cứng, lâm râm khó chịu, tới tháng cũng hay trễ.\"",
        "Nàng dâu ngồi sai tư thế, co ro lướt điện thoại. Mẹ chồng từ từ bước tới phía sau, đặt tay lên vai con dâu vỗ nhẹ nhắc nhở. Nàng dâu giật mình nhẹ, ngẩng đầu lên nhìn mẹ. Voice Directing: Giọng nữ miền Nam Việt Nam (mẹ chồng), tông điệu nhắc nhở, răn đe nhẹ nhàng, đầy tình thương. Dialogue: \"Ngồi nhiều, uống nước lạnh, thức khuya… hàn nó dồn hết xuống dưới. Không cần ăn nhiều bụng cũng phình.\"",
        "Mẹ chồng đưa ly trà ấm, khói bốc lên nhè nhẹ. Nàng dâu đón lấy ly trà bằng hai tay, hít hà mùi thơm, khuôn mặt dãn ra, mỉm cười nhẹ nhõm và thả lỏng người. Voice Directing: Giọng nữ miền Nam Việt Nam (mẹ chồng), cực kỳ ấm áp, chậm rãi, mang cảm giác chữa lành, chốt giải pháp rõ ràng dứt khoát. Dialogue: \"Mấy bà xưa hay làm ấm người trước. Uống trà lá mâm xôi đều, bụng ấm lên, khí huyết chạy lại thì người nhẹ, bụng tự xẹp.\""
    ]
}

out_file = Path("kich_ban_to_video/configs/bung_duoi_phinh_pipeline.json")
out_file.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Generated: {out_file} (Size: {out_file.stat().st_size} bytes)")
