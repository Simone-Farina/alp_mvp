def suggest_parent_via_ai(title: str, content: str) -> str | None:
    import os
    from alp.core.ai_helper import openai
    if not (os.getenv("OPENAI_API_KEY") and openai):
        return None
    prompt = (
        "You are a knowledge graph assistant. "
        f"Note title: {title}\n"
        "Suggest ONE broader parent topic; reply ROOT if none.\n\n"
        f"CONTENT:\n{content[:4000]}"
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    ans = resp.choices[0].message.content.strip()
    return None if ans.upper() == "ROOT" else ans