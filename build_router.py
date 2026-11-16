import os
import re
import json
from pathlib import Path

SKILLS_DIR = Path("C:/Users/shahin.karimov/.gemini/config/skills")
OUTPUT_JSON = Path("C:/Users/shahin.karimov/.gemini/config/skills_manifest.json")
OUTPUT_MD = Path("C:/Users/shahin.karimov/.gemini/config/skills_index.md")

# Categories mapping
CATEGORIES = {
    "AI Agents & Automation": [
        "agent", "browser-use", "ufo", "composio", "superpowers", "playwright",
        "scrape", "workflow", "orchestrat", "subagent", "autonomous", "automation"
    ],
    "Web Frontend & UI/UX": [
        "react", "next", "vue", "tailwind", "css", "html", "ui-ux", "taste-skill",
        "frontend", "animation", "motion", "d3", "canvas", "shadcn", "threejs",
        "design-system", "deck", "presentation", "svg", "web-design", "icon", "dashboard"
    ],
    "Backend, APIs & Databases": [
        "api", "graphql", "rest", "backend", "fastapi", "django", "node", "express",
        "postgres", "supabase", "redis", "database", "sql", "bigquery", "docker",
        "kubernetes", "terraform", "auth", "jwt", "oauth", "stripe", "payment"
    ],
    "Mobile & Multiplatform": [
        "flutter", "dart", "react-native", "expo", "android", "swift", "ios",
        "xcode", "compose", "mobile"
    ],
    "Game Development": [
        "game", "godot", "unity", "unreal", "phaser", "pixi", "pygame", "bevy",
        "defold", "love2d", "shader", "tilemap", "ecs", "roblox", "3d", "character"
    ],
    "Code Quality, Testing & DevOps": [
        "test", "tdd", "e2e", "qa", "review", "git", "deploy", "vercel", "cloudflare",
        "ci", "lint", "debug", "benchmark", "performance", "audit", "security", "threat"
    ],
    "Data Science, ML & Analytics": [
        "ml", "data", "spark", "dbt", "dataform", "bigframes", "analytics",
        "eval", "vector", "rag", "notebook", "statistics", "science", "biology"
    ],
    "Content, SEO & Marketing": [
        "seo", "ads", "copywriting", "youtube", "article", "social", "brand",
        "content", "marketing", "changelog", "documentation", "doc", "epub", "pdf"
    ]
}

def classify(name: str, desc: str) -> str:
    combined = (name + " " + desc).lower()
    for cat, keywords in CATEGORIES.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', combined):
                return cat
    return "Specialized & Miscellaneous"

def main():
    skills = []
    
    for item in sorted(SKILLS_DIR.iterdir()):
        if not item.is_dir():
            continue
        skill_md = item / "SKILL.md"
        if not skill_md.exists():
            continue
            
        try:
            content = skill_md.read_text(encoding="utf-8", errors="ignore")
            name = item.name
            desc = ""
            
            # Simple frontmatter parser
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm = parts[1]
                    desc_match = re.search(r'description:\s*(?:[>|]-?\s*)?(.*?)(?=\n[a-zA-Z0-9_-]+:|\Z)', fm, re.DOTALL)
                    if desc_match:
                        raw_desc = desc_match.group(1).strip()
                        # Clean up multiline
                        desc = " ".join([line.strip() for line in raw_desc.splitlines() if line.strip()])
                        desc = desc.strip('"\'')
            
            if not desc:
                # Extract first paragraph after # header
                lines = content.splitlines()
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("---"):
                        desc = line
                        break
                        
            category = classify(name, desc)
            
            skills.append({
                "name": name,
                "description": desc[:300] if desc else "Specialized agent skill.",
                "category": category,
                "path": str(skill_md).replace("\\", "/")
            })
        except Exception as e:
            print(f"Error reading {item.name}: {e}")

    print(f"Total skills indexed: {len(skills)}")
    
    # Write JSON manifest
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(skills, f, indent=2, ensure_ascii=False)
    print(f"Saved manifest to {OUTPUT_JSON}")
    
    # Write Markdown index
    by_category = {}
    for s in skills:
        by_category.setdefault(s["category"], []).append(s)
        
    md_lines = [
        "# Master Skill Catalog & Router Index",
        f"\nTotal Active Skills: **{len(skills)}**\n",
        "This directory is the single source of truth for all skills available to Antigravity agents. "
        "When executing a task, reference this index to locate the exact skill, then read its `SKILL.md` before taking action.\n"
    ]
    
    for cat, items in sorted(by_category.items()):
        md_lines.append(f"## {cat} ({len(items)} skills)\n")
        md_lines.append("| Skill Name | Description | Link |")
        md_lines.append("| :--- | :--- | :--- |")
        for item in items:
            name = item["name"]
            desc = item["description"].replace("|", "\\|")
            path = item["path"]
            md_lines.append(f"| **`{name}`** | {desc} | [`SKILL.md`](file:///{path}) |")
        md_lines.append("\n")
        
    OUTPUT_MD.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"Saved Markdown index to {OUTPUT_MD}")

if __name__ == "__main__":
    main()
