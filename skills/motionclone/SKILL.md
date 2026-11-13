---
name: motionclone
description: Training-free motion cloning for controllable video generation (ICLR 2025). Extract and clone camera motion and object motion from reference videos for Text-to-Video (T2V) and Image-to-Video (I2V) without video inversion or model fine-tuning.
metadata:
  version: 1.0.0
---

# MotionClone: Training-Free Motion Cloning for Controllable Video Generation

`MotionClone` is a training-free framework (ICLR 2025) that enables motion cloning from reference videos for versatile motion-controlled video generation, including **Text-to-Video (T2V)** and **Image-to-Video (I2V)**, without requiring computationally expensive video inversion or model fine-tuning.

Local implementation repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\MotionClone`

## Core Mechanism

- **Sparse Temporal Attention Weights**: Dominant components in temporal-attention maps drive primary motion synthesis, while non-dominant components represent noise. MotionClone isolates sparse temporal attention weights as motion representations.
- **Single-Step Denoising Motion Extraction**: Bypasses inverted latent DDIM optimization by extracting motion guidance vectors directly in a single forward denoising step from reference video frames.
- **Dual Motion Guidance**:
  1. **Global Camera Motion**: Pans, tilts, rolls, zooms, tracking shots, and aerial sweeps.
  2. **Local Object Motion**: Skeletal kinematics, character movement, trajectory paths, and physical gestures.

## CLI & Pipeline Workflows

### 1. Text-to-Video (T2V) Motion Transfer
To transfer motion from a reference video to a prompt-generated video:
```bash
python t2v_video_sample.py \
  --inference_config configs/inference/t2v.yaml \
  --pretrained_model_path models/StableDiffusion/stable-diffusion-v1-5 \
  --reference_video_path reference_videos/example_camera_pan.mp4 \
  --prompt "A medieval knight walking through a dark mystic forest, cinematic 4k" \
  --generated_videos_save_dir generated_videos/t2v_output \
  --W 512 --H 512 --L 16
```

### 2. Image-to-Video (I2V) Motion Transfer
To animate a static input image according to the motion of a reference video:
```bash
python i2v_video_sample.py \
  --inference_config configs/inference/i2v.yaml \
  --pretrained_model_path models/StableDiffusion/stable-diffusion-v1-5 \
  --condition_image_path condition_images/character.png \
  --reference_video_path reference_videos/character_dance.mp4 \
  --prompt "A warrior in samurai armor swinging a katana, hyperrealistic" \
  --generated_videos_save_dir generated_videos/i2v_output \
  --W 512 --H 512 --L 16
```

## Key Configuration Parameters

- `motion_guidance_weight` (default `0.8` - `1.2`): Controls how strongly the reference motion is enforced. Higher values prioritize reference motion fidelity over prompt appearance.
- `sparsity_ratio` (default `0.1` - `0.2`): Percentage of top temporal attention weights retained for motion representation.
- `guidance_steps` (default `15` - `25`): Denoising timestep range where motion guidance gradients are actively injected into the UNet attention layers.
- `without_xformers`: Set flag if xFormers is unavailable; otherwise xFormers is enabled by default for GPU memory efficiency.

## Best Practices

1. **Resolution & Frame Length**: Default to 512x512 resolution and 16 frames for stable temporal consistency on 16GB-24GB VRAM GPUs.
2. **Clean Reference Clips**: Reference videos with minimal compression artifacts and clear subject/camera trajectories yield the cleanest motion maps.
3. **Prompt Alignment**: Ensure the subject in the prompt can physically replicate the reference motion (e.g., matching a quadruped animal motion to a vehicle will produce warping).
