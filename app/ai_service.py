import os, httpx

SYSTEM_NOTE="You are SumTalsa, an education support assistant. Outputs must be teacher-reviewable, curriculum-aware, age-appropriate, and must not claim unverified curriculum facts."

def mock_generate(module:str,prompt:str)->str:
    if module=="lesson":
        return f"""LESSON PLAN\nFocus: {prompt}\n\n1. Engage / Introduction\nActivate prior knowledge with a short learner-centered prompt.\n\n2. Explore / Development\nUse guided activity, pair/group work or practical investigation.\n\n3. Explain / Deepening\nLearners present evidence; teacher clarifies key concepts.\n\n4. Elaborate / Practice\nApply learning in a new context.\n\n5. Evaluate / Reflection\nUse a short competency check and learner reflection.\n\nTeacher review: verify curriculum source, timing, inclusivity and assessment evidence."""
    if module=="exam":
        return f"""ASSESSMENT BLUEPRINT\nFocus: {prompt}\n\nSection A: Foundational understanding\nSection B: Application\nSection C: Analysis/reasoning\nExtended task: Evaluate/create where appropriate\n\nMarking guide: allocate marks at observable scoring points and accept equivalent valid responses.\n\nTeacher review required before use."""
    return f"""SUMTALSA SUPPORT\nRequest: {prompt}\n\nSuggested approach:\n1. Clarify the intended competency or learning goal.\n2. Use learner-centered examples and practical context.\n3. Include a short check for understanding.\n4. Review for curriculum alignment and factual accuracy before use."""

async def generate(module:str,prompt:str)->str:
    provider=os.getenv("AI_PROVIDER","mock").lower()
    if provider!="openai" or not os.getenv("OPENAI_API_KEY"):
        return mock_generate(module,prompt)
    # Generic OpenAI Responses API hook; falls back safely if unavailable.
    headers={"Authorization":f"Bearer {os.environ['OPENAI_API_KEY']}","Content-Type":"application/json"}
    payload={"model":os.getenv("OPENAI_MODEL","gpt-5-mini"),"input":[{"role":"system","content":[{"type":"input_text","text":SYSTEM_NOTE}]},{"role":"user","content":[{"type":"input_text","text":prompt}]}]}
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            r=await client.post("https://api.openai.com/v1/responses",headers=headers,json=payload)
            r.raise_for_status()
            data=r.json()
        text=[]
        for item in data.get("output",[]):
            for c in item.get("content",[]):
                if c.get("type")=="output_text":
                    text.append(c.get("text",""))
        return "\n".join(text).strip() or mock_generate(module,prompt)
    except Exception:
        return mock_generate(module,prompt)
