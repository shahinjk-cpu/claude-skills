---
name: short-video-studio
description: 策划、剪辑和交付面向实体门店获客或个人账号增长的短视频。适用于从真实素材策划选题、编写口播和拍摄任务卡、剪辑已有实拍，或用代码制作图解与产品演示。以锁定音轨为剪辑骨架，支持成片质检、MP4 与可编辑工程导出，以及发布数据复盘。
---

# short-video-studio 短视频制片工作室

服务**不懂拍摄、不懂剪辑、不懂包装**的用户，把专业短视频编导方法论与工业级「先音后画」后期工程封装为一条龙智能工作室。

> **路径与按需读取约定**：本文中的相对路径（`scripts/...`、`references/...`、`assets/...`）均以本 `SKILL.md` 所在 Skill 目录为根。**与用户互动对话时必读** [references/interactive-coach-protocol.md](references/interactive-coach-protocol.md)；策划与写稿时**优先读取精简速查手册** [references/methodology-cheatsheet.md](references/methodology-cheatsheet.md)；仅在做 4 周账号体系规划或专项脚本深度设计时，再按需查阅完整总库 [references/建立可循环的内容系统.md](references/建立可循环的内容系统.md)。

---

## 一、 互动对话最高铁律：5 类用户分流 + 每轮必带【四要素掌控感进度卡】

### 1.1 首次进入对话：按 5 类真实用户先猜后确认（不问大空题、不说行话）
根据用户第一句话自动识别其所属类型，用**一句话先猜后确认**，同时亮出他专属的总步数（详细话术与点单菜单见 [references/interactive-coach-protocol.md](references/interactive-coach-protocol.md)）：
1. **实体店从零拍（`store_from_zero`，共 5 步，属 `store` 轨，默认 `style_14`）**：还没拍素材，想拉同城客人私信或进店 → `定话题写说话词 → 照手机清单开拍 → 听声音定节奏 → 看粗剪画面 → 拿成品与封面`。
2. **个人博主口播提质感（`creator_talking`，共 4 步，属 `creator` 轨，默认 `style_11` / `08` / `09` / `16`）**：有观点或已录好说话视频，想要小窗口、超大号重点字、金句卡片 → `定台词或收素材 → 听声音定节奏 → 选画面样式看粗剪 → 拿成品与封面`。
3. **手机存货一键挑剪（`footage_organizer`，共 3 步）**：已拍了一堆随手拍片段堆在文件夹里，懒得自己挑和剪 → `自动筛废片排顺序 → 听声音看粗剪 → 拿成品与封面`。
4. **社恐不露脸 / 纯图解动画（`faceless_visual`，共 4 步，默认 `style_24` / `22` / `06` 或纯代码制片）**：不想出镜，只有产品/环境特写或只有一段文字数据 → `定台词与配音 → 配全屏特写或动态图表 → 看粗剪确认 → 拿成品与封面`。
5. **发片后复盘调优（`post_review`，共 2 步）**：视频已发出一两天，拿后台数据来找病因 → `看数据找卡点 → 存下改进配方`。

### 1.2 每一轮回复强制携带【四要素掌控感进度卡】（MUST）
在陪伴用户推进项目的**每一轮回复**中，AI 必须同步运行 `workflow_guard.py status --pipeline-dir <dir> [--user-type <类型>]`，按 [interactive-coach-protocol.md](references/interactive-coach-protocol.md) 第二节格式展示大白话四要素进度卡（`当前进度 / 我刚做了或正在做 / 现在轮到你(附 A/B/C 选项) / 离能发还差`，严禁技术缩写或黑话）：
- **选画面样式不甩全表**：按用户所属人群从 [interactive-coach-protocol.md](references/interactive-coach-protocol.md) 第三节只挑 **3~4 款最对口的大白话样式**让用户选 A/B/C/D。
- **后台长任务先预告、缺素材给二选一补救、隔天回来先读 `00_progress_card.json` 无缝续接**。

---

## 二、 唯一选题与文案方法论（内部严格溯源，对外全程大白话）

- 速查手册与大白话交付模板：[references/methodology-cheatsheet.md](references/methodology-cheatsheet.md)
- 完整编导知识总库：[references/建立可循环的内容系统.md](references/建立可循环的内容系统.md)

**三条硬性约束**：
1. **【最高优先级】对用户全程说大白话，严禁蹦出课件或专业黑话**：内部思考与脚本编排严格按方法论选型，但**在面对用户对话、交付 4 周内容日历、口播稿、分镜表、拍摄卡、剪辑表、《我替你做的决定》与周复盘时，严禁直接输出「水桶流、漏斗流、5A、A1–A5、开篇钩子、人设、爆点前置、A-roll/B-roll、J-cut/L-cut、Room Tone、LUFS、LUT、HDR、完播率」等黑话或英文缩写**，全部按 [methodology-cheatsheet.md](references/methodology-cheatsheet.md) 第零节转译成老百姓听得懂的人话。
2. **写稿前必过「事件一句话」自检**：动笔前先答「一句话能不能说清这条视频里发生了什么事？」。说不清具体事件必须退回重想；写稿落实**「用看得见的画面代替抽象感受」**与**「把专业词换成老奶奶也听得懂的话」**。
3. **开篇先让观众看懂发生了什么**：口播默认前 3 秒 2 次画面切换；纪实片允许连续展示完整动作；图解默认 1 次切换。结合画面信息可读性与片型调节镜长。

---

## 三、 三入口工作流与「最多打断 3 次」交互契约

每生产一条视频，最多只允许在 **3 个节点** 打断用户确认；其余后期参数全部按默认专业值自动推进并在交付时呈报大白话《我替你做的决定》：

### 入口路由（优先一手原材，拒绝二手模板套话）
- **一手原始材料接入与口播稿体检**（有同行评论/客服记录/门店凭证或口播初稿时优先运行；产出的 `00_raw_intel.json` 会自动透传至选镜、关键词高亮、花字提炼与封面）：
  ```bash
  python3 scripts/raw_intel_ingest.py \
    --comments-file <评论或客服导出.txt> \
    --proof-dir <实拍凭证目录> \
    --script-json <脚本.json> \
    --track <store|creator> \
    --output <项目目录>/pipeline/00_raw_intel.json
  ```
  仅在核实记录确实来自真实客户导出时才加 `--verified-customer-export`。价格、数据、对比与实拍承诺可用 `--sources-json` 关联原件，格式见 [references/pipeline-schemas.md](references/pipeline-schemas.md)。
- **入口 1（从零策划实拍）**：梳理账号主页四件套与受众定位 → 按三阶段配比生成大白话 4 周发片计划 → 逐条过「事件一句话」自检并写大白话口播稿 → 用 `generate_shot_card.py` 生成带 SVG 构图示意的手机拍摄卡。
- **入口 2（带实拍素材进来）**：运行素材深度盘点（高动态/Log 探测、锐度/防抖锁定最佳入点、景别/运镜分析、人脸与显著性感知、生成缩略接触表），输出 `00_inventory.json` 与 `00_shot_log.json` 反推选题：
  ```bash
  python3 scripts/inventory_media.py --input-dir <原素材目录> --output <项目目录>/pipeline/00_inventory.json --track <store|creator>
  ```
- **入口 3（零实拍代码制片 `--mode code-video` / 知识讲解动画 `--mode knowledge-animation`）**：
  - 编码前**必读总纲与四大工艺** [references/code-video-methodology.md](references/code-video-methodology.md) 及对应手册（[knowledge-animation-craft.md](references/knowledge-animation-craft.md) / [motion-broll-and-subtitles.md](references/motion-broll-and-subtitles.md) / [script-craft-and-platforms.md](references/script-craft-and-platforms.md)）。
  - **知识讲解动画（支持「无配音字幕即旁白」与「配音同步」双模式 + 16:9/9:16/1:1/3:4 画幅 + 商业字体注入 + 配乐/拟音混音 + 双比例 4K 代码封面 + 分平台发布文案包）**：
    ```bash
    python3 scripts/run_pipeline.py --account <账号> --workspace-root <工作区> --track creator --mode knowledge-animation --anim-title "<片名>" --anim-idea "<核心反常识命题>" --anim-ratio <16x9|9x16|1x1|3x4> --anim-font-mode <sans|serif>
    ```
  - **多卡片图解与产品演示规约闭环**：
    ```bash
    python3 scripts/code_video_spec.py --init-spec --title "<标题>" --one-idea "<核心命题>" --out-dir <pipeline目录>
    python3 scripts/code_video_spec.py --validate-spec <pipeline目录>/00_code_spec.json
    python3 scripts/run_pipeline.py --account <账号> --workspace-root <工作区> --track <store|creator> --mode code-video --code-spec <pipeline目录>/00_code_spec.json --script-json <台词JSON> --style-id style_14
    ```
  - **口播增强套件（语音岛粗剪、动态讲解窗口 + 平滑圆环人像双源画中画、词边界 DP 短句字幕、15 种动效拟音与字体子集化）**：
    - `step2_transcribe.py`（语音能量岛 + 5s 重叠短窗防吞重说）→ `step4_build_edl.py`（自动探测动态讲解窗口并绑定真双源圆环画中画）→ `step5_subtitles.py`（词边界 DP 断句 + `terms.txt` 保护词 + 双层柔和阴影 ASS/SRT + `05_subtitle_check.txt`）→ `synth_motion_sfx.py`（15 种无版权动效拟音峰值对齐）→ `step9_title_cover.py --code-cover-4k`（分平台发布文案包 `09_publish_copy_pack.md` + 360px 手机信息流小图预览 + 16:9/3:4 双比例 4K 封面）→ `subset_fonts.py`（按工程用字自动压缩子集字体）。

### 专属工作区隔离、合规门禁与诚实基线（MUST）
- **原素材严格只读**：所有加工、转码、临时帧和成片导出统一写入独立专属目录（默认 `~/.short-video-studio/workspaces/accounts/<account_slug>/projects/<project_id>/`，可用 `--workspace-root` 指定），**严禁向 `--raw-dir` 写入任何文件**。
- **广告法与平台合规前置 (`compliance_guard.py`)**：`must` 级违禁词（精准排除「最近/最后/最怕/第一口」零误杀）在文本/配音模式自动温和改写，在**实拍真人口播模式整句弃用并留痕**（严禁靠改字幕遮掩原声）；`warn` 级支持账号白名单 `compliance_whitelist.json` 凭证核销。
- **诚实基线**：未导入真实评论/客服原材时显式声明「未经真实顾客提问验证」；复盘数据未达到实验样本量前绝不盲调参数。

### 3 次打断节点（Strict Interrupt Cap = 3）
1. **🛑 打断 #1：确认选题与脚本**（或结合原材体检与 `00_contact_sheet.jpg` 拍板）。
2. **🛑 打断 #2：确认拍摄任务卡或锁定音轨盲听版 (`03_blind_audio.m4a`)**
   - 手机拍摄任务卡（支持 `--audio-events` 按配音反定每镜时长与 `--industry general|catering|auto_repair`）：
     ```bash
     python3 scripts/generate_shot_card.py --output <项目目录>/shot_card.md --title "<选题>" --track <store|creator> --industry catering
     ```
   - 缺镜头时调用 7 种修辞同构代码补镜（`--backend auto|html|pillow`）：
     ```bash
     python3 scripts/generate_code_broll.py --output <补镜.mp4> --mode <kinetic_text|data_chart|flow_diagram|proportion|day_night|chips|versus> --register warm_food --backend auto --title "<标题>" --items-json '<JSON>'
     ```
3. **🛑 打断 #3：确认锁定音轨、低清粗剪预览与方案哈希锁 (`workflow_guard.py`)**
   ```bash
   python3 scripts/run_pipeline.py --account <账号> --raw-dir <原素材目录> --track <store|creator> --mode lock-preview
   ```
   拍板后可用 `workflow_guard.py lock --pipeline-dir <dir>` 上锁，再按需走 `--mode render-locked`（锁定出片）、`--mode reedit-visuals`（只改画面音轨不动）或 `--mode relock-voice`（改词重锁音轨）。仅在真实向用户发起确认时调用 `workflow_guard.py record-stop`。

---

## 四、 先音后画流水线与独立验收交付

完整中间文件契约见 [references/pipeline-schemas.md](references/pipeline-schemas.md)，安全区与居中字幕规范见 [references/platform-safe-zones.md](references/platform-safe-zones.md)。

一键跑通端到端流水线（默认门店轨 `style_14` / 博主轨 `style_11`，自动落盘 `out/` 并清理大体积临时文件）：
```bash
python3 scripts/run_pipeline.py \
  --account <账号> \
  --raw-dir <原素材目录> \
  --track <store|creator> \
  --mode <full|code-video|knowledge-animation|lock-preview|reedit-visuals|relock-voice|render-locked> \
  [--style-id style_14] \
  [--raw-intel <00_raw_intel.json>] \
  [--sources-json <sources.json>] \
  [--visual-index <00_visual_index.json>] \
  [--licenses-json <licenses.json>] \
  [--dialect mandarin|cantonese|dialect] \
  [--store-anchor <门店名>] \
  [--multi-speaker] \
  [--hook-variants 2] \
  [--exports auto|mp4|jianying|hyperframes|both]
```

独立导出与单步重跑命令：
```bash
python3 scripts/export_jianying.py --pipeline-dir <pipeline目录>
python3 scripts/export_hyperframes.py --pipeline-dir <pipeline目录>
python3 scripts/qa_inspector.py --pipeline-dir <pipeline目录> [--sync-window <起秒> <止秒>] [--strict-asr]
```

### 核心专业能力与出厂验收门禁
- **真居中对称字幕铁律**：全套渲染、剪映、HyperFrames 与白盒/黑盒质检统一锁死 `X = 540px` 正中对称带 `[220, 860]`（宽 `640px`）与 `Y = 1310px` 基准（自动 7 点避脸），绝不发生左偏或右撞点赞栏。
- **真实物理音景与现场动作声**：实拍流水线统一采用 `assets/sound_vibe/` CC0 真实录制乐段（波形校准真实起拍）与物理音效，支持开场→正文双段配乐切换、特写镜现场动作声轻混（`-10dB`）及三轨防削波总线控制（`-14.0 ±1.5 LUFS`、真峰值 `≤ -1.0 dBTP`）；知识动画与动态图解辅以 `synth_motion_sfx.py` 15 种无版权动效拟音。
- **视觉语义与封面**：支持高动态/常见 Log 色彩还原、横转竖人脸智能居中构图、53% 特写动态配比、景别与运镜防撞墙语法、全片情绪+眼部锐度选帧封面（9:16 + 3:4 防裁切 + 180px 真实像素对比度校验 + macOS Apple Vision 可选人物前景压字）。
- **独立双层质检与盲审取证包**：`qa_inspector.py` + `independent_verifier.py` 执行白盒契约 + 单遍解码黑盒校验（含 540px OCR 居中实测、单框 WCAG、BT.709 肤色、切点像素跳变、SFX 5ms 起音校准、本地 Whisper 盲听复核与商业授权清查），同时生成一页式大白话《独立盲审取证包》（`10_blind_review_pack.md` + `10_action_strips.jpg`）。
- **人工终审签字与归档验证**：核对后执行 `workflow_guard.py approve-final --pipeline-dir <dir> [--reviewed <ID> ...] --note "<实查结果>"` 签字，并可用 `workflow_guard.py verify-out --out-dir <out目录>` 核对成品指纹。风格复刻场景用 `workflow_guard.py replication-diff` 跑洁净室防抄袭与乱序盲测。

---

## 五、 发布复盘与对照实验闭环

发片 48 小时后收集分子/分母快照数据（支持 `retention_3s`、`completion_rate`、`inquiry_rate`、`store_visit_rate`、`follow_rate` 与 `drop_off_sec` + `edl_path` 镜头归因），写入按账号与轨道隔离的 `content-log`：
```bash
# 1. 记录发布快照并生成大白话周复盘
python3 scripts/content_log_review.py --account <账号> --track <store|creator> --add-json '<快照JSON>'

# 2. 预登记对照实验 -> 回放历史 -> 达标后显式启用候选参数
python3 scripts/content_log_review.py --account <账号> --track <store|creator> --register-plan <plan.json>
python3 scripts/content_log_review.py --account <账号> --track <store|creator> --replay-plan <plan.json>
python3 scripts/content_log_review.py --account <账号> --track <store|creator> --activate-candidate <candidate_id>
```
启用后在制作命令加 `--platform <平台名>` 即可生效，旧配置自动归档到 `profile_history/`。

---

## 六、 风格谱参考包装库与环境初始化

- 已内置 **24 套 v2.1 量化风格谱**（`style_01` ~ `style_24`，涵盖 20 套主流商业短视频形态 + **4 套高空镜实拍/图解风格 `style_21`–`style_24`（空镜占比 85%–100%）**，100% 原生 `1080×1920` 竖屏安全区锁定）与 **3 大共享剪辑规则字典**（83 组 0ms 文字动画×音效配对、29 类口播语义音效分类、黄金四色排版与 3:4 封面四构图法则）：
  - **门店获客默认（`style_14`）**：门店实景出镜、双段音乐情绪反转、过半店内实拍叠层、居中暖黄重点大字；另含白边圆角人像贴纸框（`style_07`）、清冷奶油美业（`style_04`）、二手车暖金双格框（`style_17`）、户外探盘立体大字（`style_18`）、暖木厚重宋体（`style_20`）、牛皮纸工艺拆解（`style_05`）、慢调空间漫游（`style_13`）、**85% 门店工艺特写快切（`style_21`）**、**95% 品牌微纪录慢调空镜（`style_23`）**。
  - **个人账号默认（`style_11`）**：清亮通透圆角底框配圆窗例证与双段音乐；另含极速跳剪荧光高亮（`style_02`）、顶栏常驻长口播（`style_03`）、黑底竖相框治愈金句（`style_06`）、毛玻璃虚化画中画与双行巨字评论（`style_08`）、暗黑双格证据窗与圆窗主讲普法（`style_09`）、高能快切弹窗种草（`style_10`）、极简白底卡片（`style_12`）、全屏高密动效大字访谈（`style_15`）、暗黑三格巨型数字卡与线性分屏书摘（`style_16`）、冷峻数据背景白边贴纸框（`style_19`）、暗黑控制台演示（`style_01`）、**90% 例证图解拆解（`style_22`）**、**100% 全画面无出镜卡点混剪（`style_24`）**。
  - 完整大白话选用指南见 [assets/style_spectrum/STYLE_SPECTRUM_REPORT.md](assets/style_spectrum/STYLE_SPECTRUM_REPORT.md)。
  ```bash
  python3 scripts/apply_style_spectrum.py --list
  python3 scripts/apply_style_spectrum.py --style-id style_14 --apply-pipeline <项目目录>/pipeline
  python3 scripts/apply_style_spectrum.py --style-id style_14 --export-hyperframes <out_dir>
  ```
- 所有随仓内置的 4 款开源商用字体（阿里妈妈数黑体、得意黑、思源宋体 Bold & Heavy）、CC0 真实录制 BGM、物理 SFX 与 `17³` LUT 授权清单见 [references/assets-attribution.md](references/assets-attribution.md)。
- 首次部署或排查依赖/字体/无头浏览器桥时运行：
  ```bash
  python3 scripts/check_and_setup.py --init-fonts --init-assets --install-deps --init-browser
  ```
