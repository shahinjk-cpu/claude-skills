# 内置资产可商用授权与来源清单 (Assets Attribution)

本清单声明 `short-video-studio/assets/` 与内置生成器产出的全部可商用字体、CC0 背景音乐、物理音效、程序化动效拟音、3D LUT 及代码渲染运行时的版权归属与商业使用许可。

---

## 一、 随仓内置 4 款可商用字体 (`assets/fonts/`)

流水线、28 套字幕模板与知识讲解动画统一优先加载随仓内置的以下 **4 款免费可商用字体**（全部采用 **SIL Open Font License 1.1** 或官方全平台免费商用授权）：

| 随仓字体文件 | 字体名称 | 授权协议 | 来源项目 |
| :--- | :--- | :--- | :--- |
| `assets/fonts/AlimamaShuHeiTi-Bold.otf` | **阿里妈妈数黑体 (Alimama ShuHeiTi)** | 阿里巴巴免费可商用授权 | 阿里妈妈智造字官网发布，全平台免费商用（约 1.0 MB） |
| `assets/fonts/SmileySans-Oblique.ttf` | **得意黑 (Smiley Sans)** | SIL OFL 1.1 | atelier-anchor 开源发布（约 2.5 MB） |
| `assets/fonts/SourceHanSerifCN-Bold.otf` | **思源宋体粗体 (Source Han Serif CN Bold)** | SIL OFL 1.1 | Adobe & Google 开源发布（约 11 MB） |
| `assets/fonts/SourceHanSerifCN-Heavy.otf` | **思源宋体特粗 (Source Han Serif CN Heavy)** | SIL OFL 1.1 | Adobe & Google 开源发布（约 11 MB） |

> 注：
> 1. 所有导出与 `#22` 质检均通过 `common.is_verified_commercial_font()` **严格拦截无商用授权的系统私有字体（如苹方/华文黑体/微软雅黑）**；若用户本机额外合法安装了思源黑体（Source Han Sans CN / Noto Sans CJK SC，SIL OFL 1.1），系统也会按白名单识别放行（该字体未随仓打包以控制体积）。
> 2. **字体子集化授权说明（`scripts/subset_fonts.py`）**：知识讲解动画与 4K 代码封面通过 `fonttools` 按项目实际用字生成轻量子集用于无头渲染提速；生成子集严格保留原开源字体授权声明，仅随当前项目页面本地使用，不修改字体版权声明。

---

## 二、 CC0 真实录制背景音乐、物理材质音效与程序化动效拟音

### 1. CC0 1.0 真实录制配乐与物理音效 (`assets/sound_vibe/`)
实拍流水线与 24 套风格谱统一采用由 `scripts/vibe_sound.py` 管理的 **Creative Commons 0 (CC0 1.0 公共领域)** 免版税真实录音素材（来源均为 Freesound CC0 公共领域录音，BGM 统一转为 48kHz AAC `.m4a` 并经真实波形起拍校准 `onset_offset_sec` / `beat_times_sec` / `downbeat_times_sec`；物理音效为 48kHz 16-bit PCM WAV）：

| 代表流派样式 | 真实 BGM 来源 (Freesound ID · CC0) | 物理材质 SFX 来源 (Freesound ID · CC0) |
| :--- | :--- | :--- |
| `style_14`（默认门店轨） | `fs:680113` Pop Guitar Loop Thing | `fs:585257` Swoosh-1 / `fs:704935` Wooden Tap / `fs:411462` Bubble Pop |
| `style_02` | `fs:69195` Mix05 90BPM Hip-Hop Loop | `fs:585257` Swoosh-1 / `fs:512389` Bass Impact / `fs:878248` Micro Swish |
| `style_03` | `fs:713517` Perspire Guitar & Piano Loop | `fs:623709` Soft Ambience Swoosh / `fs:369710` Wood Knock / `fs:704935` Wooden Tap |
| `style_11` / `style_12`（含博主轨） | `fs:629153` Dusty Lofi Melody Loop 75 BPM | `fs:878248` Micro Swish / `fs:411462` Bubble Pop / `fs:528561` Soft UI Click |
| `style_06` | `fs:668907` Cinematic Emotional Piano (92bpm) | `fs:623709` Soft Ambience Swoosh / `fs:676375` Minolta Film Camera Shutter |
| `style_05` | `fs:347815` Warm Breeze Loop | `fs:82379` Paper Flip (Olympus LS-10) / `fs:369710` Wood Knock |
| `style_15` | `fs:531463` Waterfall Synth Loop | `fs:378085` Mechanical Key / `fs:528561` Soft UI Click / `fs:217181` Till Receipt Printer |

### 2. 无版权程序化动效拟音 (`scripts/synth_motion_sfx.py`)
面向知识讲解动画与动态图解界面转场，内置 **15 种 48kHz 立体声原创数学合成动效拟音**（`whoosh_in`、`whoosh_out`、`swish`、`pop`、`pop_low`、`tick`、`click`、`drag`、`shrink`、`impact`、`riser`、`chime`、`peel`、`stretch`、`glide`），全部由本仓代码实时合成，无任何第三方采样版权负担（CC0 1.0）。

> 注：如果文案流程使用在线 `edge-tts` 或本机语音朗读生成配音，仅面向演示与内部测试；`compliance_guard.py` 会在 `asset_license_manifest.json` 显式输出 `tts_commercial_notice` 告警，正式商业投放前建议替换为真人实拍口播或已采购商用授权语音。

---

## 三、 调色预设 (`17³` 3D LUTs) 与代码/动画运行时

| 资产路径 | 说明 | 来源 | 授权协议 |
| :--- | :--- | :--- | :--- |
| `assets/luts/warm_store.cube`、`clean_creator.cube` | 门店暖调 / 博主清透通用 3D LUT (`17³`) | 仓库维护脚本 `dev_tools/generate_builtin_assets.py` 生成 | **CC0 1.0 可商用** |
| `assets/style_spectrum/luts/style_01.cube` ~ `style_24.cube` | 24 套风格谱色彩映射矩阵 (`17³`) | 基于白盒色彩锚点由 `write_cube_lut` 生成 | **CC0 1.0 可商用** |
| `assets/style_spectrum/style_spectrum_library.json`、`assets/subtitle_templates/templates.json` | 24 套 v2.1 量化风格谱与 28 套字幕模板 | 本项目原创结构化配置（100% 绑定随仓开源商用字体，零私有字体） | **MIT / CC0 可商用** |
| `assets/style_spectrum/animation_sfx_pairs.json`、`sfx_intent_taxonomy.json`、`typography_cover_rules.json` | 83 组动画×音效配对、29 类语义音效表、四色排版与 3:4 封面四构图规则 | 公共领域剪辑排版数学与 CC0 音效角色映射 | **MIT / CC0 可商用** |
| `assets/canvas_runtime/stage.js`、`anim_starter.html`、`cover_4k.html` | 确定性知识讲解动画舞台引擎与双比例 4K 代码封面模板 | 本项目原创 Canvas 2D / HTML 代码 | **MIT / CC0 可商用** |

- 7 种修辞动态补镜（`kinetic_text / data_chart / flow_diagram / proportion / day_night / chips / versus`）均由 `scripts/generate_code_broll.py`（无头 Chrome HTML + Pillow 兜底）现场原创绘制，无第三方 UI 素材版权负担。
