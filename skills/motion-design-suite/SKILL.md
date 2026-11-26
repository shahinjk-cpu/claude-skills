---
name: motion-design-suite
description: High-performance motion design and animation suite covering physics, keyframing, SVG, Canvas, 3D, and interactive web transitions.
---

# Motion Design & Animation Master Suite


## Motion Systems & Animation Patterns

### Module: motion-advanced
---
name: motion-advanced
description: Advanced motion patterns for React / Next.js — drag & drop, gestures, text animations, SVG path drawing, custom hooks, imperative sequences (useAnimate), loaders, and the full API decision tree. Requires motion-foundations. Use when building drag and drop, gestures, text or SVG animation, or imperative animation sequences in React or Next.js.
tags: [motion, animation, advanced, gestures, svg]
category: frontend
author: jeff
metadata:
  version: 1.0.0
---

#

### Module: motion-art-direction
---
name: motion-art-direction
description: This skill should be used when the user asks to "direct a motion graphics video", "do creative/art direction for a video", "define a motion language", "set the tone and pacing", "make the animation feel consistent", "decide what to animate (and what not to)", "turn a brief/brand into motion choices", or needs the senior creative judgment that sits above specific techniques (gsap/lottie/shader). Covers motion language, tone & energy, pacing/rhythm, moti

### Module: motion-background
---
name: motion-background
description: This skill should be used when the user asks to "add an animated background", "build a mesh/gradient background", "make an aurora/shader background", "add constellation/particle background", "animated hero background", or "a subtle looping background behind content". Covers CSS mesh gradients, GLSL shader gradients (Three.js), canvas particle constellations, seamless loops, and reduced-motion/performance handling — fully self-contained.
version: 0.1.0
---

### Module: motion-canvas
---
name: motion-canvas
description: Complete production-ready guide for Motion Canvas with ESM/CommonJS workarounds, full setup templates, and troubleshooting for programmatic video creation using TypeScript
license: MIT
metadata:
  version: 2.0.0
  author: motion-canvas
  repo: https://github.com/motion-canvas/motion-canvas
  tags: [Video, TypeScript, Animation, Motion Canvas, Signals, Generators, Canvas API, Vector, Audio Sync, Vite, ESM]
  dependencies: ["@motion-canvas/core>=3.0.0", "@motio

### Module: motion-claude-agent-lab
---
name: claude-agent-lab
description: Claude 代理实验室的连续数据界面动效模板。
---

从 `example.html` 开始制作影片；它是可直接渲染的完整参考成片。

**Arc:** 参考 → 数据 → 叙事 → 动效 → 指导 → 交付

| Scene (`CFG.scenes` id) | Dur | Summary | Build | Reuse |
|---|---|---|---|---|
| `reference` | 4 s | 参考阶段：REFERENCE，文件送往代理队列 | 单 canvas，`reference-focus` 淡入，`reference-out` 尾部淡出；持续轨道运动 | 替换 `referenceTitle`、`referenceCopy`、`referenceFile`、`referenceDetail`，保持弧形关联结构 |
| `data` | 4 s | 数据阶段：DATA，文件送往代理队列 | 单 canvas，`data-focus` 淡入，`data-out` 尾部淡出；持

### Module: motion-claude-design-team
---
name: motion-claude-design-team
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Claude 动效设计团队

从 `example.html` 开始修改，这是可确定性逐帧寻址的画布影片。

**Arc:** 引子 → 打字标题 → 请求 → 并行任务 → 设计团队 → 实时预览 → 配色变化 → 完成 → 收尾

关键 cue：title-typed（打字完成）、prompt-typed（请求完成）、prompt-submit（提交推近）、preview-launch（预览标题）、preview-feedback（换色请求）、palette-finished（完成状态）。

## 文件
保留 `example.html`、`assets/gsap.min.js`、`assets/Inter-Variable.ttf`、`assets/Inter-OFL.txt`、`assets/animator-label.png`、`

### Module: motion-design
---
name: motion-design
description: "Apply motion craft to an active task: refine a brief, beat map, visual continuity, typography, pacing, and timeline implementation. Use when planning or improving motion graphics; the host task owns artifact creation, output format, and export."
triggers:
  - motion design
  - motion graphics
  - 视频动效
  - 动态设计
  - MG动画
  - kinetic typography
  - animated explainer
od:
  mode: utility
  category: animation-motion
  featured: -100
  example_prompt: Create a 15

### Module: motion-dev
---
name: motion-dev
description: >-
  A high-performance JavaScript and React animation library for modern web interfaces.
---

# motion.dev

## Overview
A high-performance JavaScript and React animation library for modern web interfaces.

- **Category**: Frontend
- **Type**: Library
- **Reference**: https://motion.dev

## Key Capabilities & Architecture
1. **Core Integration**: Provides structured conventions and patterns for integrating motion.dev into agentic workflows.
2. **Best Practices**

### Module: motion-distilbook-explainer
---
name: distilbook-explainer
description: DistilBook 手绘讲解产品演示模板。
od:
  mode: video
  scenario: video
---

从 `example.html` 开始制作；它是本模板的完整影片。参考品牌、产品、文案和数字保持原样，用户明确改编时再通过 CFG 替换。

**Arc:** 教师手写引子 → 品牌 → 添加资料 → 审核脚本 → 同步绘图 → 速度 → 风格 → 画幅 → 语言 → 品牌定制 → 收尾。

## 结构

| 场景（CFG.scenes id） | 时长 | 画面摘要 | 构建方式 | 复用内容 |
|---|---:|---|---|---|
| `hook` | 2.0 s | 教师不照读，而是画出来 | 单画布，hook-line、hook-answer 逐字裁切，expo.out；hook-underline 划线 | 手写形式保留，文字按用户主张重写 |
| `intro` | 1.9 s | 三色书本与 DistilBook | books-land 三书错峰下

### Module: motion-doctrine
---
name: motion-doctrine
description: "GATEWAY — load FIRST before composing any HyperFrames animation or video. The high-level motion law that makes a multi-scene video feel like ONE continuous camera move instead of a stack of independently-animated slides. Covers the vector law (how you exit determines how you enter, incl. the Z scale-sign rule), the film's current, carrier elements, causal motion, the Seam Gate (build-gate enforcement), the ban on idle wobble (motion must PERFORM, not breat

### Module: motion-flowdrive-motion-reel
---
name: motion-flowdrive-motion-reel
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Flowdrive 动效展示

从 `example.html` 开始制作。此文件是影片源；拷贝 `assets/` 中所有图像、字体、许可证和 `gsap.min.js`，并读取 `references/sound.json`。参考原片保留 Flowdrive、Anthropic、Claude Code 和原文案。

**Arc:** 点阵文件 → 上传 → 分层流播 → 全球交付 → 域名安全 → 无限带宽 → Webflow → 品牌收尾

| Scene (`CFG.scenes` id) | Dur | Summary | Build | Reuse |
|-|-|-|-|-|
| `hook` | 1.300 s | 点阵文件 | 单 canvas；`hook-enter` 入场，`hook-out` 从末尾计时退出；cub

### Module: motion-foundations
---
name: motion-foundations
description: Motion tokens, spring presets, performance rules, device adaptation, accessibility enforcement, and SSR safety for React / Next.js using motion/react. Foundation layer — all other motion skills depend on this. Use when setting up motion tokens, spring presets, reduced-motion handling, or SSR-safe animation in React or Next.js.
tags: [motion, animation, performance, accessibility]
category: frontend
author: jeff
metadata:
  version: 1.0.0
---

# Motion Fo

### Module: motion-frames
---
name: motion-frames
description: |
  A single-frame motion-design composition with looping CSS animations —
  rotating type ring, animated globe, ticking timer, parallax labels.
  Renders as a hero video poster you can hand straight to HyperFrames or
  any keyframe-based exporter. Use when the brief asks for "motion design",
  "animated hero", "loop", "video poster", "title card", or pairs Open
  Claude Design with HyperFrames for a kinetic export.
triggers:
  - "motion design"
  - "motion g

### Module: motion-future
---
name: motion-future
description: "The Future Is Already Here — motion design template. A 20-second electric-blue tech reel, rebuilt from the viral original: 3D cubes, a word tunnel, liquid chrome type, a FUTURE.EXE desktop, a countdown, glass objects and a chrome FUTURE hero, cut to 120 BPM."
od:
  mode: video
  scenario: video
  preview:
    type: html
    entry: example.html
---

# The Future Is Already Here

A 20-second electric-blue tech reel, rebuilt from the viral original: 3D cubes, a

### Module: motion-kinetic-motion-designer
---
name: motion-kinetic-motion-designer
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# 动效设计师名片

从 `example.html` 开始改编。保留目录中的 `assets/Anton-400.ttf`、`assets/Anton-OFL.txt`、`assets/Caveat-400.ttf`、`assets/Caveat-OFL.txt`、`assets/gsap.min.js`、`assets/cover.jpg` 和 `references/sound.json`。原音轨 `assets/soundtrack.mp3` 由 runner 添加。

**Arc:** 弹跳 → 文字 → 动作词 → 缓动 → 跟随 → 预备动作 → 名片

| 场景（CFG.scenes id） | 时长 | 画面含义 | 构建方式 | 复用 |
|---|---|---|---|---|
| `spacing` | 1.9

### Module: motion-lab
---
name: motion-lab
description: "为当前网页或组件查找、选型和改造动效。包含 160 个案例的 HTML/CSS/JS、参数与中英文索引，覆盖基础、文字、交互和高级动效。"
en_name: motion-lab
zh_name: "Motion.Lab · 160 个动效案例"
zh_description: "为当前网页或组件查找、选型和改造动效。包含 160 个案例的 HTML/CSS/JS、参数与中英文索引，覆盖基础、文字、交互和高级动效。"
triggers:
  - "motion-lab"
  - "动效"
  - "动画"
  - "motion"
  - "Motion.Lab"
  - "动效案例"
  - "案例库"
  - "特效"
  - "文字动画"
  - "hover"
  - "scroll"
license: MIT
od:
  mode: utility
  category: animation-motion
  upstream: https://github.com/yangxu128/Motion.Lab

### Module: motion-mind-clarity-journey
---
name: mind-clarity-journey
description: 清晰心智主题的黑红剪影动效模板。
---

以 `example.html` 为影片起点；保留单 canvas 与 GSAP 主时钟，按 `CFG` 调整内容。

**Arc:** 清晰 → 成长 → 专注 → 想法 → 出发

| 场景（CFG.scenes id） | 时长 | 画面与含义 | 实现 | 复用 |
|---|---|---|---|---|
| `clarity` | 2.25 s | 头脑敞开，太阳升起再缩为水滴 | canvas 路径与射线，`sun-rise`、`mind-reveal`、`sun-sink` | 三个开场文字变量；保留升起与内收 |
| `growth` | 2.083333 s | 手臂举壶，头顶生出红色枝叶 | `water-pour`、`plant-grow`、`water-stop`；宽高联动生长、顶叶倾斜与循环水滴 | 无产品列表；保留浇灌因果 |
| `focus` | 2.166667 s | 手中火柴点燃，出现专注燃料文案 | `match

### Module: motion-opus-design-lab
---
name: motion-opus-design-lab
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Opus Motion Design Lab

从 `example.html` 开始制作影片。它是一段 15.125 秒的浏览器工作台式动效实验室：上方是演示舞台，中间的像素向导指向当前控制项，下方是始终可见的六格代码面板。

**Arc:** spacing → typography → motion blur → easing → follow-through → anticipation → final delivery

| Scene (`CFG.scenes` id) | Dur | Summary | Build | Reuse |
|-|-|-|-|-|
| `spacing` | 1.967 s | 蓝球沿弧线弹跳，残影解释动作间距 | canvas 弹道与轮廓残影；`ball-release` 触发起跳 | 可替换 `acce

### Module: motion-patterns
---
name: motion-patterns
description: Production-ready animation patterns for React / Next.js — button, modal, toast, stagger, page transitions, exit animations, scroll, and layout — built on motion-foundations tokens and springs. Use when animating a specific UI element in React or Next.js — button, modal, toast, stagger, page transition, or scroll.
tags: [motion, animation, ui-patterns]
category: frontend
author: jeff
metadata:
  version: 1.0.0
---

# Motion Patterns

Copy-paste patterns for 

### Module: motion-product-promo
---
name: motion-product-promo
description: "Product Promo — motion design template. A 15-second product promo rebuilt from the viral original with a fictional brand: a halftone mascot asks 'Got something to sell?', product cards pop onto blue, a phone store fills in, a checkout board is stamped 'Handled.' and the wordmark closes it."
od:
  mode: video
  scenario: video
  preview:
    type: html
    entry: example.html
---

# Product Promo

A 15-second product promo rebuilt from the viral origin

### Module: motion-prompt-motion-gallery
---
name: prompt-motion-gallery
description: Prompt Motion 网页作品浏览与形态变换演示。
---

从 `example.html` 开始制作；这是可寻址、单 Canvas、GSAP 主时钟驱动的完整影片。

**Arc:** 作品浏览 → 播放器形变 → 返回 → 图片打印演示 → 返回首页。

| 场景（CFG.scenes id） | 时长 | 画面与信息 | 构建方式 | 复用方式 |
|---|---|---|---|---|
| gallery | 4.70 | 页面标题、订阅卡与四列作品墙上下浏览 | Canvas 重建网页；gallery-open 弹窗进入 | brand、headline、独立图片变量 |
| player | 4.50 | 按钮→加载→勾选→音乐播放器→音量条 | player-loader、player-check、player-island、player-expand、player-play、player-scrub、player-volume；实测过冲回落，文字分层去模糊显现 | al

### Module: motion-semantic-color-stripes
---
name: motion-semantic-color-stripes
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

从 `example.html` 开始修改。这是一段将原片词语输入与色带占比变化重建在单个 canvas 上的演示。

**Arc:** 番茄 → 霓虹 → 年代与游戏词语 → 城市 → 蓝色语义 → 自然意象

## 文件
复制 `example.html`、`assets/gsap.min.js`、`assets/motion-data.js`、`assets/NotoSansMono-variable.woff2` 与 `assets/NotoSansMono-OFL.txt`，保持相对路径。声音结构见 `references/sound.json`。封面为 `assets/cover.jpg`。

## 场景结构
文字、色带、插入点与鼠标指针均由纯函数 `render(t)` 重建；不加载参考视频，不使用整帧背景。`assets/

### Module: motion-showreel
---
name: motion-showreel
description: "Motion Designer Showreel — motion design template. A 15-second motion designer showreel at 128 BPM, rebuilt from the viral original: an Open Design mark opener, a stretching wordmark, six easing curves, a morphing shape, a truchet field, a 3D point cloud, kinetic type and an end card."
od:
  mode: video
  scenario: video
  preview:
    type: html
    entry: example.html
---

# Motion Designer Showreel

A 15-second motion designer showreel at 128 BPM, rebui

### Module: motion-skills
---
name: motion-skills
description: Master orchestrator and suite guide for motion graphics, video animation, kinetic typography, WebGL, UI micro-interactions, and AI video pipelines. Guides selection across 30+ motion skills (iart.ai suite, Remotion, After Effects, GSAP, CSS, Manim, and MotionClone).
metadata:
  version: 1.0.0
---

# Motion Skills: Master Motion & Animation Suite

The **Motion Skills** ecosystem is a collection of 30+ agent-native skills covering motion design craft, video pro

### Module: motion-sky-water-tessellation
---
name: sky-water-tessellation
description: 鸟群与鱼群交错的黑白版画循环模板。
---

从 `example.html` 开始制作影片，保留本地资源的相对路径。

**Arc:** 版画鸟群拍翼 → 鸟鱼正负形交错 → 鱼群游动；三个空间层同时存在，没有剪切。

| Scene (`CFG.scenes` id) | Dur | Summary | Build | Reuse |
|-|-|-|-|-|
| `tessellation` | 4.266667 s | 上部鸟群飞行，下部鱼群游动，中间形成黑白负形 | 单 canvas；`flight-start` 启动连续位移，`cycle-end` 标记终点；翼面使用余弦拍动，位移线性、起伏正弦 | 读取 `fishLine`、`fishScale`、`fishFine`；保持鸟鱼尺寸和错位排列 |

## 资源
必须携带 `assets/gsap.min.js`、`assets/engraving.js`、`assets/fish-line.png`、`assets/fish-sca

### Module: motion-superx-audience-growth
---
name: superx-audience-growth
description: "SuperX 受众增长产品宣传模板：火焰点燃品牌，产品操作连续转为增长数据。"
od:
  mode: video
  scenario: video
---

从 `example.html` 开始改编，它是本模板的完整影片。保留单画布、GSAP 主时间轴与纯时间函数 `render(t)`；默认内容完整保留 SuperX 原片身份。

**Arc:** 发布循环 → 品牌点燃 → 发现热门 → 内容写作 → 智能排期 → 互动增长 → 规模数据 → 行动收尾

## 参考文件

复制 `example.html`、`references/sound.json`，以及下列本地资源，保持路径：
- `assets/InstrumentSerif-400-Italic.ttf`
- `assets/InstrumentSerif-OFL.txt`
- `assets/Inter-400.ttf`
- `assets/Inter-500.ttf`
- `assets/Inter-600.ttf`


### Module: motion-tixfox-ticket-promo
---
name: motion-tixfox-ticket-promo
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# TixFox 票务宣传片

从 `example.html` 开始制作；此文件是完整画面与唯一时间逻辑入口。

**Arc:** 提问 → 费用问题 → 品牌 → 定价 → 建活动与销售 → 购票 → 收款 → 检票 → 品牌收尾

## 文件
保留 `assets/gsap.min.js`、`assets/Roboto-regular.ttf`、`assets/Roboto-OFL.txt`、`assets/fox-logo.png`、`assets/fox-coin.png`、`assets/microphone.png`、`assets/ticket-qr.png`、`assets/fox-tickets.png`、`assets/RobotoMono-regular.ttf`、`assets/RobotoMono-OFL.txt` 

### Module: motion-ui-morph
---
name: motion-ui-morph
description: "One-Shape UI Motion — motion design template. A 14-second code-only UI motion piece, rebuilt from the viral original: one shape morphs from a button into a loader, player, slider, toggle, tabs, chart, command palette and toast, driven by a cursor at 120 BPM."
od:
  mode: video
  scenario: video
  preview:
    type: html
    entry: example.html
---

# One-Shape UI Motion

A 14-second code-only UI motion piece, rebuilt from the viral original: one shape morp

### Module: motion-visual-lesson
---
name: motion-visual-lesson
description: "Bring Ideas to Life (让灵感成真) — a 20-second OpenDesign paper story, with interactive prototypes, websites, PPT, posters and motion films collected into a book of possibilities."
od:
  mode: video
  scenario: video
  preview:
    type: html
    entry: example.html
---

# 让灵感成真 / Bring Ideas to Life

A 20-second paper-cutout story for OpenDesign: a girl sends “OpenDesign, what can you design?” on a paper plane. The buddy demonstrates interactive prototype

### Module: motion-windows-studio-launch
---
name: motion-windows-studio-launch
description: >-
  Specialized AI agent skill extracted from nexu-io/open-design.
---

# Windows Studio Launch

从 `example.html` 开始，保留本地 assets 路径。该文件是可直接播放和定位时间的完整影片。

**Arc:** 启动 → 发布 → 期待 → 演示 → 安装 → 反馈 → 品牌收尾

| Scene (`CFG.scenes` id) | Dur | Summary | Build | Reuse |
|---|---|---|---|---|
| `boot` | 5.85 s | 云朵天空中的 Windows 旗帜变为 HyperFrames 标志 | 单 canvas，`boot-in` 入场，`boot-out` 末端，power3.out | 修改 CFG 对应文案与图像，保留窗口层级 |
| `desktop` | 3.95 s | 复古图标和发布标题进入桌面

