import sys
import json
import re
from pathlib import Path

MANIFEST_PATH = Path("C:/Users/shahin.karimov/.gemini/config/skills_manifest.json")

def search_skills(query: str, top_k: int = 5):
    if not MANIFEST_PATH.exists():
        print(f"Error: Manifest not found at {MANIFEST_PATH}")
        return []
        
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        skills = json.load(f)
        
    query_tokens = [t.lower() for t in re.split(r'[\s\-_,.:;]+', query) if len(t) > 1]
    
    scored = []
    for item in skills:
        name = item["name"].lower()
        desc = item["description"].lower()
        cat = item["category"].lower()
        
        score = 0
        
        # Exact skill name match
        for token in query_tokens:
            if token == name:
                score += 15
            elif token in name:
                score += 6
            if token in desc:
                score += 2
            if token in cat:
                score += 1
                
        # Phrase match
        q_lower = query.lower()
        if q_lower in name:
            score += 20
        elif q_lower in desc:
            score += 10
            
        if score > 0:
            scored.append((score, item))
            
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in scored[:top_k]]

def main():
    if len(sys.argv) < 2:
        print("Usage: python skill_router.py <query> [top_k]")
        sys.exit(1)
        
    query = " ".join(sys.argv[1:])
    top_k = 5
    if len(sys.argv) >= 3 and sys.argv[-1].isdigit():
        top_k = int(sys.argv[-1])
        query = " ".join(sys.argv[1:-1])
        
    results = search_skills(query, top_k)
    
    if not results:
        print(f"No specific skills found for query: '{query}'")
        return
        
    print(f"\n--- Top {len(results)} Skill Recommendations for: '{query}' ---")
    for idx, item in enumerate(results, 1):
        print(f"\n{idx}. [{item['name']}] ({item['category']})")
        print(f"   Description: {item['description']}")
        print(f"   Path: {item['path']}")

if __name__ == "__main__":
    main()
