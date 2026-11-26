#!/usr/bin/env python3
"""
[素材获取：拍摄任务卡]
为需要实拍的短视频生成傻瓜式手机拍摄任务卡：
逐个镜头写明：拍什么、机位与景别、目标时长（头尾各留 1.0s，共 +2.0s 余量）、备份条数、手机拍摄要点，
并生成对齐 common.SUBTITLE_SAFE_ZONE 的 SVG 简笔构图示意卡片。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import CANVAS_HEIGHT, CANVAS_WIDTH, SUBTITLE_SAFE_ZONE, SUBTITLE_SYMMETRIC_ZONE, read_json, write_json

DEFAULT_SHOTS = [
    {
        "shot_no": 1,
        "role": "真人出镜 · 开头 3 秒抓人第一句",
        "what": "老板/主理人微侧身自然面对镜头，手里拿核心产品、账单或原料，情绪到位说出开头最抓人的第一句",
        "angle_framing": "手机立在眼睛齐高位置、别正死板对着脸（微侧 15–30° 更自然），离人一个手臂远，头顶留一拃空隙避开顶部遮挡",
        "duration_sec": 4.5,
        "backup_takes": 3,
        "diagram_type": "portrait_hook",
        "phone_tips": "竖屏 1080p/30fps（关美颜和手机高动态模式防假脸发灰）；手持允许自然轻微呼吸感、别僵硬；嘴离麦不超两巴掌，脸朝窗户自然光，说错别停直接重念那一句",
        "spoken_line": "开头前 3 秒留住人的第一句话（先给最带劲的画面和具体事件）",
    },
    {
        "shot_no": 2,
        "role": "细节特写补拍（必须录进现场动作声）",
        "what": "近距离拍产品细节、手里干活动作或单据/原料物证，把锅响、切菜、工具动作声一起录进去",
        "angle_framing": "手机抬高约一拃 45° 俯拍，镜头离主体两掌宽（点屏幕锁死对焦与亮度）",
        "duration_sec": 5.0,
        "backup_takes": 2,
        "diagram_type": "closeup_detail",
        "phone_tips": "【特写/物证务必拍稳】手肘贴桌稳住别抖糊小字和细节，慢推 2 秒即可；头尾各停稳 1.0 秒再收机（共留 +2.0 秒剪辑余量）",
        "spoken_line": "盖在关键信息说话处，只换画面展示实打实的细节，声音不断",
    },
    {
        "shot_no": 3,
        "role": "门店/干活场景实拍（证明真实靠谱）",
        "what": "门头、操作台、顾客实景或正在干活的真实状态，让观众一眼看见你是真干活、真开店",
        "angle_framing": "往后退三步拍全貌，用主摄 1x 不要开广角防变形，人物/招牌放中间偏上",
        "duration_sec": 6.0,
        "backup_takes": 2,
        "diagram_type": "wide_scene",
        "phone_tips": "第一视角边走边拍允许自然轻微手持感；横扫展示环境时匀速走 4 秒，开头和收尾各停稳 1 秒",
        "spoken_line": "配合讲清老板的脾气、原则底线和为什么这么做的那一段",
    },
    {
        "shot_no": 4,
        "role": "真人出镜 · 结尾表态与引导留言",
        "what": "回到真人面对镜头，重申自己的做事底线，并抛一个具体问题让评论区聊起来（或说明怎么找到店）",
        "angle_framing": "身体略微侧转一点，离手机一个手臂远平视，眼神看镜头小圆孔别老盯屏幕",
        "duration_sec": 5.0,
        "backup_takes": 2,
        "diagram_type": "portrait_hook",
        "phone_tips": "说话有情绪大于一切；说完最后一个字微笑停满 1.0–2.0 秒再抬手关录制，防止句尾被手挡脸",
        "spoken_line": "结尾亮底线金句 + 一句具体互动问题或到店指引",
    },
]

PRESENTATION_PICKER = [
    ("边干活边拍", "手上干着活顺嘴聊，最真实、最适合晒手艺和门店日常"),
    ("副驾侧拍 / 车里聊", "手机架在旁边微侧拍，自在不尴尬，适合讲行业看法和日常科普"),
    ("边走路边拍", "带着轻微手持呼吸感边走边说，最自然、上手最快"),
    ("近距离悄悄话 / 俯视拍", "像给熟人透底一样，最适合讲内幕和避坑提醒"),
    ("店里沙发/饭桌边吃边聊", "像朋友聊天一样接地气，适合讲自己的真实经历和故事"),
    ("内心配音（不用背词）", "镜头只拍干活和店里画面，声音后期照着念就行，完全不卡壳"),
]

INDUSTRY_CHECKLISTS = {
    "general": [
        "准备 1–2 个能直接证明专业度的真实实物/单据道具，开拍放手边（别空手干讲）。",
    ],
    "catering": [
        "【餐饮必拍】早上开档鲜货上秤/拆箱过程 + 热锅下料滋啦同期声 + 明厨洁净操作台。",
        "【餐饮避坑】拍生肉血水、垃圾桶、杂乱后厨角落时严禁作为夸赞“鲜美/卫生”的垫画面。",
    ],
    "auto_repair": [
        "【汽修必拍】新旧配件放一块对比特写 + 配件防伪标/原厂码对光拍清 + 拧扭矩扳手清脆咔哒同期声。",
        "【汽修避坑】实拍车牌与客户微信界面注意错位遮挡隐私，切忌黑脏废油糊满镜头的无效抖拍。",
    ],
}


def build_sketch_svg(diagram_type: str, shot_no: int) -> str:
    """生成清晰直观的 9:16 竖屏简笔构图示意 SVG（精准映射对称居中字幕带与平台安全框）。"""
    sx = round(SUBTITLE_SYMMETRIC_ZONE["x_min"] / CANVAS_WIDTH * 180)
    sw = round((SUBTITLE_SYMMETRIC_ZONE["x_max"] - SUBTITLE_SYMMETRIC_ZONE["x_min"]) / CANVAS_WIDTH * 180)
    sy = round(SUBTITLE_SAFE_ZONE["y_min"] / CANVAS_HEIGHT * 320)
    sh = max(24, round((SUBTITLE_SAFE_ZONE["y_max"] - SUBTITLE_SAFE_ZONE["y_min"]) / CANVAS_HEIGHT * 320))
    scy = sy + sh // 2 + 4

    base_header = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="320" viewBox="0 0 180 320">'
        '<defs><marker id="a" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M 0 1 L 10 5 L 0 9 z" fill="#0284C7"/></marker></defs>'
        '<rect x="2" y="2" width="176" height="316" rx="14" fill="#F8FAFC" stroke="#334155" stroke-width="3"/>'
        '<rect x="10" y="27" width="136" height="220" fill="none" stroke="#10B981" stroke-width="1.5" stroke-dasharray="4,3"/>'
        '<text x="14" y="20" font-size="9" fill="#64748B" font-family="sans-serif">顶部留白防遮挡</text>'
        '<text x="14" y="262" font-size="9" fill="#EF4444" font-family="sans-serif">底部文案遮挡区</text>'
        '<rect x="148" y="115" width="24" height="125" rx="4" fill="#E2E8F0"/>'
        '<text x="160" y="180" font-size="8" fill="#64748B" text-anchor="middle" transform="rotate(90 160 180)">点赞栏</text>'
    )
    if diagram_type == "portrait_hook":
        body = (
            '<circle cx="78" cy="88" r="24" fill="#FDE68A" stroke="#0F172A" stroke-width="2.5"/>'
            '<path d="M40 180 C40 132, 116 132, 116 180 Z" fill="#93C5FD" stroke="#0F172A" stroke-width="2.5"/>'
            '<circle cx="70" cy="84" r="2.5" fill="#0F172A"/><circle cx="86" cy="84" r="2.5" fill="#0F172A"/>'
            '<path d="M71 96 Q78 102 85 96" fill="none" stroke="#0F172A" stroke-width="2"/>'
            f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="6" fill="#FEF08A" stroke="#CA8A04" stroke-width="1.5"/>'
            f'<text x="{sx + sw // 2}" y="{scy}" font-size="10" font-weight="bold" text-anchor="middle" fill="#0F172A">字幕安全区</text>'
        )
    elif diagram_type == "closeup_detail":
        body = (
            '<ellipse cx="78" cy="142" rx="48" ry="34" fill="#FED7AA" stroke="#9A3412" stroke-width="2.5"/>'
            '<rect x="44" y="125" width="68" height="34" rx="8" fill="#FB923C" stroke="#7C2D12" stroke-width="2"/>'
            '<line x1="25" y1="80" x2="55" y2="115" stroke="#0284C7" stroke-width="2.5" marker-end="url(#a)"/>'
            '<text x="78" y="70" font-size="11" font-weight="bold" text-anchor="middle" fill="#0369A1">45° 俯拍特写</text>'
            '<text x="78" y="147" font-size="11" font-weight="bold" text-anchor="middle" fill="#FFFFFF">产品主体</text>'
        )
    else:
        body = (
            '<rect x="24" y="88" width="108" height="90" fill="#E0E7FF" stroke="#3730A3" stroke-width="2.5"/>'
            '<rect x="52" y="126" width="52" height="52" fill="#A5B4FC" stroke="#3730A3" stroke-width="2"/>'
            '<path d="M26 205 L128 205" stroke="#059669" stroke-width="3"/>'
            '<polygon points="128,200 138,205 128,210" fill="#059669"/>'
            '<text x="78" y="75" font-size="11" font-weight="bold" text-anchor="middle" fill="#312E81">环境全景横移</text>'
            '<text x="78" y="222" font-size="9" text-anchor="middle" fill="#059669">匀速横扫 4s</text>'
        )
    footer = (
        f'<text x="78" y="295" font-size="11" font-weight="bold" text-anchor="middle" fill="#0F172A">镜头 #{shot_no} 构图框</text>'
        '</svg>'
    )
    return base_header + body + footer


def build_ascii_sketch(diagram_type: str) -> str:
    if diagram_type == "portrait_hook":
        return "\n".join([
            "┌──────────────────────┐",
            "│  (避开顶部状态栏遮挡)│",
            "│       ╭───╮          │",
            "│       │^_^│  ←人物   │",
            "│      ╭┴───┴╮  居中   │",
            "│      │     │         │",
            "│ [字幕黄金安全区]     │",
            "│░░░░░░░░░░░░░░░░░░░░░░│",
            "└──────────────────────┘",
        ])
    if diagram_type == "closeup_detail":
        return "\n".join([
            "┌──────────────────────┐",
            "│  ↘ 手机45°俯拍       │",
            "│                      │",
            "│     ╔══════════╗     │",
            "│     ║ 产品特写 ║     │",
            "│     ╚══════════╝     │",
            "│  (锁定对焦·稳住手腕) │",
            "│░░░░░░░░░░░░░░░░░░░░░░│",
            "└──────────────────────┘",
        ])
    return "\n".join([
        "┌──────────────────────┐",
        "│  门店/工作场景全景   │",
        "│   ┌──────┬──────┐    │",
        "│   │ 招牌 │ 门面 │    │",
        "│   └──────┴──────┘    │",
        "│  ───匀速横移 4s───▶  │",
        "│░░░░░░░░░░░░░░░░░░░░░░│",
        "└──────────────────────┘",
    ])


_EMO_PLAIN = {
    "hook": "开头抓人",
    "info": "讲清干货",
    "detail": "展示细节",
    "persona": "亮出底线态度",
    "cta": "引导留言到店",
    "twist": "反转揭秘",
}


def shots_from_audio_events(audio_events: Dict[str, Any]) -> List[Dict[str, Any]]:
    """按锁音节奏反推实拍时长（统一头尾各留 1.0s，共 +2.0s 余量），并按情绪角色区分口播与特写。"""
    out: List[Dict[str, Any]] = []
    sents = audio_events.get("sentences", [])
    n_s = len(sents)
    broll_idx = 0
    for idx, sent in enumerate(sents, start=1):
        s_dur = max(1.0, float(sent["end_sec"]) - float(sent["start_sec"]))
        rec_dur = round(s_dur + 2.0, 1)
        emo = str(sent.get("emotion_or_info", "info"))
        emo_label = _EMO_PLAIN.get(emo, "正常讲述")
        is_human_anchor = idx == 1 or idx == n_s or emo in ("hook", "persona", "cta")
        if is_human_anchor:
            diag = "portrait_hook"
            role = f"真人出镜说话 #{idx}（{emo_label}）"
            what = f"主理人微侧身自然出镜说话：「{sent['text'][:18]}」，手里拿实物、说话带真实情绪"
            framing = "手机与眼齐平、微侧身别死板正怼脸，离人一臂远，头顶留空避开顶部遮挡"
            tips = f"这段台词约 {s_dur:.1f} 秒，手持允许轻微自然呼吸感，重点是情绪到位"
        else:
            broll_idx += 1
            diag = "closeup_detail" if broll_idx % 2 == 1 else "wide_scene"
            role = f"{'产品/动作特写补拍' if diag == 'closeup_detail' else '门店环境实景补拍'} #{idx}"
            what = f"拍与这句话直接对应的真实画面：「{sent['text'][:16]}」对应的动作、实物或场景"
            framing = "主体放画面中上；特写距两掌宽，全景退后三步"
            if diag == "closeup_detail":
                tips = f"这段台词约 {s_dur:.1f} 秒；特写/物证镜头务必手肘贴稳锁焦，别把字和细节拍糊"
            else:
                tips = f"这段台词约 {s_dur:.1f} 秒；第一视角带景走动可保留自然生活感"
        out.append({
            "shot_no": idx,
            "role": role,
            "what": what,
            "angle_framing": framing,
            "duration_sec": rec_dur,
            "backup_takes": 2,
            "diagram_type": diag,
            "phone_tips": tips,
            "spoken_line": sent["text"],
        })
    return out


def generate_shot_card(
    output_md: Path,
    title: str,
    track: str,
    shots: List[Dict[str, Any]],
    industry: str = "general",
    voice_locked: bool = False,
) -> None:
    output_md.parent.mkdir(parents=True, exist_ok=True)
    svg_dir = output_md.parent / "shot_sketches"
    svg_dir.mkdir(parents=True, exist_ok=True)

    ind_labels = {"general": "通用门店/账号", "catering": "餐饮美食", "auto_repair": "汽车维修保养"}
    ind_tips = INDUSTRY_CHECKLISTS.get(industry, INDUSTRY_CHECKLISTS["general"])
    lines = [
        f"# 手机拍摄任务卡：{title}",
        "",
        f"- **拍片目标**：{'实体店同城获客（靠真实细节和老板靠谱感让人来问、进店）' if track=='store' else '个人账号涨粉引流（靠高密度干货和真情绪留住人）'} | **行业参考**：{ind_labels.get(industry, industry)}",
        "- **手机与设备设置**：`竖屏 1080p / 30帧` · 建议新款手机主摄或便携云台相机 · **别开美颜相机**（也关掉手机高动态模式防画面发灰）· **开拍前拿袖口擦干净主镜头**",
        "- **核心原则**：**用「一个手臂 / 一拃 / 退三步」做机位尺子；头尾各多停 1.0 秒（共 +2.0 秒余量）方便后期无缝衔接！**",
        "",
        "## 拍出真实感与好画面的现场铁律（照着做一次过）",
        "1. **说话的情绪大于一切，别炫技**：背词磕巴没关系，真情实感比字正腔圆更管用，不用搞花哨运镜。",
        "2. **不要死板正对着人硬拍**：身体微侧、边干活边聊或略带角度，看起来像熟人聊天，不像审讯。",
        "3. **分镜头掌握稳度（活人自然，特写拍稳）**：真人出镜说话或第一视角走动时，**允许自然轻微手持呼吸感、别架得太死板**；但拍**产品细节特写、单据、价格标签等物证**时，手肘一定要贴桌稳住、点屏幕锁死对焦，避免小字拍糊。",
        "4. **必录 2 个现场动作声**：热锅滋啦、刀切声、工具清脆声等顺手录进去，别全拍哑巴画面。",
        "5. **单独录 10 秒店里安静环境音**：开拍前大家闭嘴停 10 秒，录一段干净底音，方便后期把话头话尾垫顺滑。",
        "6. **外接麦先拍一下手 & 说错千万别按停**：用无线麦时每条开拍前对着镜头拍一下手对齐声音；说错直接停半秒把那句重念一遍，后期会自动挑最好的一遍留下。",
        "7. **拍完当场花 20 秒回看 3 条**：① 声音清不清、没破音 ② 关键实物和人脸清不清 ③ 头顶留出一拃、底部躲开手机黑字遮挡区。",
        "",
        "## 6 种最顺手的懒人拍法（挑 1 种不尴尬的直接开拍）",
    ]
    for pname, pdesc in PRESENTATION_PICKER:
        lines.append(f"- **{pname}**：{pdesc}")
    lines.append("")
    if voice_locked:
        lines.extend([
            "## 配音已锁定（按配音时长自动算好每段要拍几秒）",
            "- 下表每个镜头的建议时长已按**对应那句话的时长 + 2.0 秒头尾余量**自动算出，照着拍就能严丝合缝！",
            "",
        ])

    lines.append("## 行业专属备料与避坑提醒")
    for t in ind_tips:
        lines.append(f"- {t}")
    lines.append("")

    for s in shots:
        svg_file = svg_dir / f"shot_{int(s['shot_no']):02d}.svg"
        svg_file.write_text(build_sketch_svg(s.get("diagram_type", "portrait_hook"), int(s["shot_no"])), encoding="utf-8")
        lines += [
            f"## 镜头 #{s['shot_no']}：{s['role']}",
            "",
            f"- **拍什么**：{s['what']}",
            f"- **对应台词/用途**：{s.get('spoken_line', '')}",
            f"- **身体尺子机位**：{s['angle_framing']}",
            f"- **建议录制时长**：{s['duration_sec']} 秒（含头尾各 1.0 秒余量）",
            f"- **建议多拍几遍**：拍 **{s['backup_takes']} 遍**（说错别停直接重念，挑最顺的一遍）",
            f"- **手机拍摄要点**：{s['phone_tips']}",
            f"- **构图示意图**：已附高清构图示意图（打开 `shot_sketches/{svg_file.name}` 查看）",
            "",
            "```text",
            build_ascii_sketch(s.get("diagram_type", "portrait_hook")),
            "```",
            "",
        ]

    output_md.write_text("\n".join(lines), encoding="utf-8")
    write_json(output_md.with_suffix(".json"), {"title": title, "track": track, "industry": industry, "shots": shots})


def main() -> None:
    parser = argparse.ArgumentParser(description="生成小白身体尺子拍摄任务卡（支持配音反定时长与行业提示）")
    parser.add_argument("--output", required=True, help="输出 Markdown 任务卡路径")
    parser.add_argument("--title", default="八年老店老板说句大实话", help="视频选题标题")
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--industry", choices=["general", "catering", "auto_repair"], default="general")
    parser.add_argument("--audio-events", help="可选：已锁定的 03_audio_events.json，按每句配音+2.0s反写实拍时长")
    parser.add_argument("--shots-json", help="可选：自定义镜头列表 JSON 文件（兼容 list 与 {'shots': [...]}）")
    args = parser.parse_args()

    voice_locked = False
    if args.shots_json:
        raw_shots = read_json(Path(args.shots_json))
        shots = raw_shots.get("shots", []) if isinstance(raw_shots, dict) else raw_shots
        if not isinstance(shots, list) or not shots:
            raise ValueError(f"shots-json 格式为空或非法: {args.shots_json}")
    elif args.audio_events:
        ae_path = Path(args.audio_events)
        if not ae_path.is_file():
            raise FileNotFoundError(f"指定的锁音事件文件不存在: {ae_path}")
        ae = read_json(ae_path)
        shots = shots_from_audio_events(ae) or DEFAULT_SHOTS
        voice_locked = True
    else:
        shots = DEFAULT_SHOTS
    generate_shot_card(Path(args.output), args.title, args.track, shots, industry=args.industry, voice_locked=voice_locked)
    print(f"[shot_card] 已生成拍摄任务卡与 SVG 简笔示意 -> {args.output}")


if __name__ == "__main__":
    main()
