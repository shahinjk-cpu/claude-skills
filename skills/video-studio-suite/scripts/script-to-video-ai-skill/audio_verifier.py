"""
Audio Speech & Energy Verifier for Pipeline Outputs
Kiểm tra tự động biểu đồ âm thanh từng giây, đảm bảo:
1. Không bị cắt cụt thoại ở giây cuối (chống nuốt chữ).
2. Không bị thừa khoảng lặng chết > 1s ở đuôi video.
"""
import wave
import subprocess
import numpy as np
from pathlib import Path

def verify_scene_audio(video_path: Path):
    temp_wav = video_path.with_suffix('.verify.wav')
    subprocess.run([
        'ffmpeg', '-y', '-i', str(video_path),
        '-vn', '-ac', '1', '-ar', '16000', str(temp_wav)
    ], capture_output=True)

    if not temp_wav.exists():
        return False, "Không trích xuất được audio"

    try:
        with wave.open(str(temp_wav), 'r') as wf:
            n = wf.getnframes()
            sr = wf.getframerate()
            data = np.frombuffer(wf.readframes(n), dtype=np.int16)
            dur = n / sr
            bs = int(sr * 0.1) # 0.1s block
            energies = [np.sqrt(np.mean(data[b:b+bs].astype(float)**2)) for b in range(0, len(data), bs) if len(data[b:b+bs]) > 0]
            max_e = max(energies) if energies else 1
            thresh = max_e * 0.15

            # Kiểm tra 0.8s cuối cùng
            tail_blocks = energies[-8:] if len(energies) >= 8 else energies
            is_tail_speaking = any(e > thresh * 1.2 for e in tail_blocks)

            # Kiểm tra khoảng lặng cuối
            silence_tail_sec = 0.0
            for e in reversed(energies):
                if e < thresh:
                    silence_tail_sec += 0.1
                else:
                    break

        temp_wav.unlink(missing_ok=True)
        return {
            "duration": round(dur, 2),
            "is_cut_off": is_tail_speaking,
            "trailing_silence": round(silence_tail_sec, 2)
        }
    except Exception as e:
        temp_wav.unlink(missing_ok=True)
        return {"error": str(e)}

if __name__ == "__main__":
    out_dir = Path("kich_ban_to_video/outputs")
    for v in sorted(out_dir.glob("scene_*_video.mp4")):
        res = verify_scene_audio(v)
        print(f"{v.name}: {res}")
