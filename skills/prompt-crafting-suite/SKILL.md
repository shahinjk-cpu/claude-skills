---
name: prompt-crafting-suite
description: >
  Comprehensive prompt engineering and AI instruction suite covering Anthropic official metaprompting, DailyForge prompt workbench & A/B benchmarking, model-specific tuning (Claude Opus/Sonnet, GPT-5/6, Gemini 3, Veo), system prompt architecture from 165 production agents, anti-slop humanization, prompt caching, and structured requirement elicitation.
category: ai_ml
version: "2.0.0"
role: consolidated_suite
triggers: prompt-crafting-suite, master prompt engineering, meta-prompting & ai architecture suite, dailyforge, elicit-first, enhance-prompt, guideline-prompt-auditor, humanize-ai-writing, humanizer, meta-prompt-skill, multi-framework-prompt-opt, prompt-caching-strategy, prompt-engineering, prompt-master, prompt-optimizer, specnext-claude-kit, stop-slop, sysprompt-agent-delegation, sysprompt-citation-system, sysprompt-code-engineering, sysprompt-context-management, sysprompt-conversation-flow, sysprompt-injection-defense, sysprompt-memory-system, sysprompt-mobile-adaptation, sysprompt-output-formatting
---

# ✍️ Master Prompt Engineering, Meta-Prompting & AI Architecture Suite

Comprehensive prompt engineering and AI instruction suite covering Anthropic official metaprompting, DailyForge prompt workbench & A/B benchmarking, model-specific tuning (Claude Opus/Sonnet, GPT-5/6, Gemini 3, Veo), system prompt architecture from 165 production agents, anti-slop humanization, prompt caching, and structured requirement elicitation.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (37 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`dailyforge`**: DailyForge — a world-class prompt engineering system for Claude. Triggers ONLY when user message starts with /dailyforge prefix, OR when user says keywords prompt debug, prompt translate, prompt compare (with or without prefix). Transforms weak prompts into structured master prompts via category-by-category questioning. Full command system: refine, save, list, history, reset, mode, guide, score, template, debug, translate, compare, batch, challenge, tip, export. If the user seems to be doing prompt engineering WITHOUT the prefix, respond normally but add ONE line at the very end: Did you mean to use /dailyforge?
  - *Reference File:* `references/dailyforge.md`
- **`elicit-first`**: Structured requirements elicitation and ambiguity resolution before implementation. Use when a user describes a task, feature, or logic to implement before writing any code or solution.
  - *Reference File:* `references/elicit-first.md`
- **`enhance-prompt`**: Improve prompts with design specs and UI/UX vocabulary. Useful for design-to-code workflows and clarifying requests for visual output.
  - *Reference File:* `references/enhance-prompt.md`
- **`guideline-prompt-auditor`**: Writes, rewrites, reviews, and audits prompts and system prompts using Anthropic's current official guidance, and selects the right model and effort level for the task before drafting. Use when the user asks to write a prompt, improve or fix a prompt, design a system prompt, or check a prompt before running a task — including phrasings like "write me a prompt for", "make this prompt better", "design a system prompt", "check my prompt before I run this", "turn these requirements into a prompt". Applies whether the resulting prompt will be pasted into Claude Code for a coding task or run in a desktop chat or Cowork session for a non-coding task. Also use when the user pastes a prompt and asks why it is not working, when they are authoring an agent system prompt or CLAUDE.md, or when they ask which model or effort level to use. Several widely repeated prompt techniques are now obsolete or rejected by the API, so consult this skill even when prompting from memory feels sufficient.
  - *Reference File:* `references/guideline-prompt-auditor.md`
- **`humanize-ai-writing`**: Deep anti-slop rules, banned vocabulary lists, human sentence rhythm, and AI prose cleanup. Eliminates robotic transitions, cliches, and predictable AI tells.
  - *Reference File:* `references/humanize-ai-writing.md`
- **`humanizer`**: Rewrite AI-sounding text to read as human-written — removes stock phrasing, over-hedging, and robotic structure. Use when the user says text "sounds like AI," wants it "humanized," or asks to de-robotify a draft.
  - *Reference File:* `references/humanizer.md`
- **`meta-prompt-skill`**: Use when asked to generate, create, or improve a prompt for a specific task. Triggers on "write me a prompt", "generate a prompt", "create a system prompt", "make a prompt for X", or when the user describes a task and needs a well-structured Claude prompt template for it.
  - *Reference File:* `references/meta-prompt-skill.md`
- **`multi-framework-prompt-opt`**: Optimizes and rewrites prompts using proven prompt engineering techniques — draft diagnosis, canonical structure (role, context+motivation, sequential instructions, XML, few-shot, chain-of-thought, output contract, success criteria), technique selection by task type and by target model (Claude 4.x, OpenAI reasoning/GPT, Gemini). Use when the user says "/prompt-engineering", "improve this prompt", "optimize this prompt", "rewrite this prompt", "apply best practices to this prompt", "turn this into a good prompt", or pastes a prompt draft asking to make it better. Reusable across any project.
  - *Reference File:* `references/multi-framework-prompt-opt.md`
- **`prompt-caching-strategy`**: - Optimize LLM prompt caching hit rate to reduce API costs and improve latency. Analyzes prompt structure, identifies cacheable vs non-cacheable content, and recommends restructuring to maximize cache reuse. TRIGGER when: user says "prompt cache", "cache hit rate", "reduce LLM cost", "optimize token usage", "cheaper LLM calls", or asks about prompt caching strategies for OpenAI/Anthropic/other providers. DO NOT TRIGGER when: user just wants to optimize a single prompt's quality (use prompt-optimizer instead), or asks about general caching infrastructure.
  - *Reference File:* `references/prompt-caching-strategy.md`
- **`prompt-engineering`**: Chain-of-thought, few-shot, system prompt design, temperature guide, structured output
  - *Reference File:* `references/prompt-engineering.md`
- **`prompt-master`**: Generates optimized prompts for AI tools. Activates only when the user explicitly asks to write, fix, improve, or adapt a prompt for a specific AI tool (LLM, Cursor, Midjourney, image AI, video AI, coding agents, etc.). Does not activate for general conversation, coding tasks, document writing, or other non-prompt-engineering work.
  - *Reference File:* `references/prompt-master.md`
- **`prompt-optimizer`**: Analyze draft prompts, detect intent and missing context, match ECC commands, skills, and agents, and output a ready-to-paste optimized prompt with diagnosis and rationale — advisory only, never executes the task. Use when the user says 'optimize prompt', 'improve my prompt', 'rewrite this prompt', 'help me prompt', 优化prompt, 改进prompt, 怎么写prompt, or 帮我优化这个指令; not for requests to optimize code or performance.
  - *Reference File:* `references/prompt-optimizer.md`
- **`specnext-claude-kit`**: Find where the bytes of a z88dk program go before optimising your own code - rank the linker .map by symbol size in the main bank and in each banked page, spot library code the source never names (the ZX terminal driver, stdio, the heap, 32-bit math helpers), drop the console with -startup=31 and the heap pragmas, and read room figures without being fooled (room that only moved between the stack and statics, big structs as locals under zsdcc). Use this skill whenever a z88dk build is short of room, a page or the main bank overflows, or the user asks what is big, where the bytes went, why the binary is so large or how to free bytes, even if they only say "we are out of room".
  - *Reference File:* `references/specnext-claude-kit.md`
- **`stop-slop`**: Remove AI writing patterns from prose. Use when drafting, editing, or reviewing text to eliminate predictable AI tells.
  - *Reference File:* `references/stop-slop.md`
- **`sysprompt-agent-delegation`**: 当系统提示词需要设计多代理协作架构、子代理专业化分工、代理间上下文隔离与传递机制、任务生命周期管理时调用此 Skill。适用于 AI Agent 平台、多工具编排系统、代码审查流水线、跨应用协作场景等。不适用于：单代理系统（无委派需求）、简单工具调用（无子代理概念）、纯 API 编排（无 AI 决策）。当需求聚焦于"单代理内的对话路由"而非"多代理间的任务分配"时，应该用 conversation-flow 而非本 Skill。
  - *Reference File:* `references/sysprompt-agent-delegation.md`
- **`sysprompt-citation-system`**: 当系统提示需要设计引用格式、信息溯源机制、来源标注系统时调用。适用于文档问答、搜索增强生成（RAG）、代码引用、浏览器辅助等需要让用户追溯信息来源的场景。不适用于纯创作类输出（如故事、诗歌），不适用于无需溯源的常识问答，也不适用于注入防御（虽然两者都涉及内容可信度）。
  - *Reference File:* `references/sysprompt-citation-system.md`
- **`sysprompt-code-engineering`**: 当系统提示面向编程代理（Coding Agent）场景时调用。适用于构建代码编辑、文件操作、Git 工作流、自动化编程助手的系统提示。不适用于代码解释或教学场景（无文件修改），不适用于 DevOps 基础设施配置（非代码层），不适用于纯对话式代码问答（无工具调用）。
  - *Reference File:* `references/sysprompt-code-engineering.md`
- **`sysprompt-context-management`**: 当系统提示词需要设计 token 预算分配、上下文压缩策略、延迟加载机制、记忆持久化方案时调用此 Skill。适用于长对话 AI 助手、代码编辑器集成、研究型 Agent、多会话系统等需要精细管理上下文窗口的场景。不适用于：单轮交互系统（无上下文管理需求）、纯无状态 API（无对话历史）、简单的 prompt 模板设计。当需求聚焦于"如何搜索外部信息"而非"如何管理已有信息"时，应该用 search-integration 而非本 Skill。
  - *Reference File:* `references/sysprompt-context-management.md`
- **`sysprompt-conversation-flow`**: 当系统提示词需要定义 AI 如何分类用户意图、路由到不同处理流程、决定澄清策略和自主度级别时调用此 Skill。适用于多任务型 AI 助手、客服机器人、编程工具、研究助手等需要结构化对话管理的场景。不适用于：纯问答型系统（无任务执行）、单轮交互（无对话状态）、简单的 prompt 模板（无路由逻辑）。当需求仅涉及"输出什么格式"而非"如何决定输出什么"时，应该用 output-formatting 而非本 Skill。
  - *Reference File:* `references/sysprompt-conversation-flow.md`
- **`sysprompt-injection-defense`**: 当系统提示需要防御提示注入、越狱攻击、社会工程、内容信任边界突破等安全威胁时调用此 Skill。适用于构建 AI Agent、聊天机器人、文档处理助手等任何接受外部输入的系统提示。不适用于纯内部工具调用场景或已完全隔离的沙箱环境，也不适用于 UI 布局或响应格式设计。
  - *Reference File:* `references/sysprompt-injection-defense.md`
- **`sysprompt-memory-system`**: 当需要为 AI 设计记忆存储、检索、应用和更新机制时调用此 skill。典型场景包括：设计持久化记忆架构（用户偏好、历史上下文、项目知识）、定义记忆的创建/读取/更新/删除生命周期、实现静默记忆应用（不在回复中透露记忆内容）、管理敏感记忆边界。 不适用于：定义工具接口（tool-specification）、定义安全规则（safety-guardrails）、定义人格风格（personality-system）。 关键 trigger 信号：AI 需要跨会话记住用户信息、记忆内容可能敏感、需要在回复中隐式应用记忆而非显式引用、用户要求"记住这个"。
  - *Reference File:* `references/sysprompt-memory-system.md`
- **`sysprompt-mobile-adaptation`**: 当系统提示面向移动端（手机、平板）场景时调用。适用于 iOS/Android 应用内 AI 助手、移动端聊天界面、响应式输出的系统提示设计。不适用于桌面端优先的场景，不适用于移动端 UI 开发（非提示层），不适用于语音场景（语音场景使用 voice-optimization）。
  - *Reference File:* `references/sysprompt-mobile-adaptation.md`
- **`sysprompt-output-formatting`**: 当系统提示词需要为 AI 输出定义格式规范、长度约束、风格指南或反"AI味"策略时调用此 Skill。适用于聊天机器人、CLI 工具、移动端助手、设计生成器等需要自适应输出的场景。不适用于：纯内容生成（无格式要求）、内部推理链设计、安全策略制定。当需求仅涉及"用什么格式返回数据"而非"如何控制输出的风格与密度"时，这不是最佳 Skill。
  - *Reference File:* `references/sysprompt-output-formatting.md`
- **`sysprompt-persona-design`**: 当需要为 AI 产品定义核心身份、角色声明和能力边界时调用此 skill。典型场景包括：设计新 AI 产品的 system prompt 首段、为不同场景创建差异化角色（如教学助手 vs 编程代理）、重新定义 AI 与用户的关系框架。 不适用于：纯人格风格调优（应使用 personality-system）、安全规则制定（应使用 safety-guardrails）、工具集成（应使用 tool-specification）。 关键 trigger 信号：产品需要 AI 有明确自我认知、多个角色共享底层能力但身份不同、需要限制 AI 在特定领域内运作、用户会问"你是谁"。
  - *Reference File:* `references/sysprompt-persona-design.md`
- **`sysprompt-personality-system`**: 当需要在基础身份之上叠加可切换的人格风格层时调用此 skill。典型场景包括：为同一产品提供多种人格选项（如 GPT-5.1 的 friendly/professional/quirky 模式）、设计人格切换机制、防止人格泄露到用户内容中。 不适用于：定义 AI 的核心角色定位（应使用 persona-design）、设计安全规则（应使用 safety-guardrails）。 关键 trigger 信号：产品需要多种语气风格、用户可切换 AI 性格、需要防止 AI 人格污染用户文本、存在 "personality" 或 "tone" 配置项。
  - *Reference File:* `references/sysprompt-personality-system.md`
- **`sysprompt-safety-guardrails`**: 当需要为 AI 系统设计多层安全防线、内容过滤策略和伦理边界时调用此 skill。典型场景包括：设计拒绝策略与升级机制、防御 prompt 注入攻击、实现领域特定安全规则（教育、医疗、金融等）、定义 AI 的价值观锚点。 不适用于：定义工具操作权限（应使用 tool-specification）、定义 AI 身份（persona-design）、调整输出风格（personality-system）。 关键 trigger 信号：AI 涉及敏感话题、需要设计"拒绝回答"策略、存在 prompt 注入风险、特定行业合规要求、需要多层防御而非单一规则。
  - *Reference File:* `references/sysprompt-safety-guardrails.md`
- **`sysprompt-search-integration`**: 当系统提示词需要定义 AI 模型何时搜索、如何搜索、搜索哪些数据源、以及如何处理搜索结果时调用此 Skill。适用于所有涉及实时知识检索的 AI 产品设计——聊天机器人、研究助手、企业知识库问答等。不适用于：纯离线场景（无搜索能力的环境）、已完全内化的知识问答（如数学推导）、创意生成任务。当需求仅涉及"从本地文件读取内容"而非"联网检索外部信息"时，这不是最佳 Skill。
  - *Reference File:* `references/sysprompt-search-integration.md`
- **`sysprompt-tool-specification`**: 当需要为 AI 定义工具接口、设计调用规范、实现工具发现与编排机制时调用此 skill。典型场景包括：设计 AI agent 的工具集、定义 JSON Schema/XML/TypeScript 格式的工具描述、实现工具权限控制与并行调度、设计子代理委托架构。 不适用于：定义 AI 身份（persona-design）、安全规则（safety-guardrails）、记忆存储（memory-system）。 关键 trigger 信号：AI 需要调用外部 API 或服务、工具数量超过 10 个需要发现机制、需要区分工具权限层级、需要子代理并行执行、工具调用涉及敏感操作需要审批。
  - *Reference File:* `references/sysprompt-tool-specification.md`
- **`sysprompt-voice-optimization`**: 当系统提示面向语音交互场景（语音助手、语音搜索、有声回答、电话客服 AI）时调用。适用于需要将文本输出优化为口语表达的系统提示设计。不适用于纯文本聊天界面，不适用于语音合成（TTS）技术选型，不适用于图像/视频多模态场景。
  - *Reference File:* `references/sysprompt-voice-optimization.md`
- **`tr-akademik-humanizer`**: Türkçe akademik metinlerdeki yapay zekâ izlerini temizler; metni panelistin "bunu bir insan, bu projeyi bilen biri yazmış" diyeceği hale getirir. Öncelik TÜBİTAK önerileri ve raporları (1001, 1002, 1501, 1505, 2209-A/B vb.), ayrıca kalkınma ajansı başvuruları, tez, makale ve proje raporları. Türkçe AI kalıplarını ("önemli bir rol oynamaktadır", "bu bağlamda", "-mektedir" tekdüzeliği, isim tamlaması zincirleri, çeviri kokusu) bulur ve düzeltir; sayı, atıf ve terimlere dokunmaz, eksik kanıtı uydurmaz, işaretler. Tetikleyiciler: "insanlaştır", "humanize et", "AI gibi duruyor", "AI tarayıcısına takılıyor", "yapay zekâ izi", "doğal yaz", "TÜBİTAK metnimi düzelt", "panelist gözüyle oku", ".docx'teki metni insan gibi yap".
  - *Reference File:* `references/tr-akademik-humanizer.md`
- **`treylom-claude-prompt-strategies`**: Use when the user explicitly targets Claude Opus 4.7 or earlier (구세대 first-class 지원) — legacy Claude 프롬프트 전략 레퍼런스의 라우팅 인덱스. 최신 모델(Opus 5·Fable 5·4.8·Sonnet 5)은 claude-fable-5-prompt-strategies.md가 기준 파일. 본문 = references/full.md.
  - *Reference File:* `references/treylom-claude-prompt-strategies.md`
- **`treylom-expert-priming`**: Use when a prompt needs an expert role assignment — 실존 전문가 지명과 전문 용어로 AI의 잠재 공간을 활성화하는 전문가 도메인 프라이밍 방법론 레퍼런스(/prompt 전문가 프롬프팅 대원칙의 근거 자료)의 라우팅 인덱스. 본문 = references/full.md.
  - *Reference File:* `references/treylom-expert-priming.md`
- **`treylom-gemini-prompt-strategies`**: Use when composing or optimizing prompts targeting Google Gemini models (Gemini 3 Pro/Flash, 3.1) — Google 공식 문서 + 실전 팁 기반 Gemini 프롬프트 전략 레퍼런스의 라우팅 인덱스. 본문 = references/full.md.
  - *Reference File:* `references/treylom-gemini-prompt-strategies.md`
- **`treylom-gpt-prompt-strategies`**: Use when composing prompts targeting GPT-6.2 Sol (GPT 디폴트), GPT-6.2 Astra, GPT-6 Sol (직전 디폴트), GPT-6 Astra, GPT-6 Luna, GPT-5.6 Sol, legacy GPT-5.5/5.4/5.2 — lean outcome-first 7블록 규칙 + LEGACY 섹션(구 XML 스택)을 담은 GPT 프롬프트 전략 레퍼런스의 라우팅 인덱스. 본문 = references/full.md.
  - *Reference File:* `references/treylom-gpt-prompt-strategies.md`
- **`treylom-image-prompt`**: Use when generating AI image prompts — 원본 = 공냥 프롬프트 킷 v4(gpt-image-2 텍스트 프롬프트 계약 — 포맷 A/B·철칙·jsonl·검증기, skills/image-prompt-kit/ vendor 원문). 웹 UI(ChatGPT/Gemini) JSON 간이 경로는 legacy 부록. /prompt 커맨드가 이미지 타겟 감지 시 references/full.md 전체 로드.
  - *Reference File:* `references/treylom-image-prompt.md`
- **`treylom-prompt-variation`**: Use when needing AI 프롬프트 변주 가이드. 다양한 프롬프팅 테크닉과 변형 전략 레퍼런스.
  - *Reference File:* `references/treylom-prompt-variation.md`
- **`treylom-research-prompt`**: Use when composing factcheck or research prompts — IFCN 원칙 기반 검증 워크플로우와 일반 리서치 템플릿을 담은 레퍼런스의 라우팅 인덱스. 본문 = references/full.md.
  - *Reference File:* `references/treylom-research-prompt.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `dailyforge`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
