"""
chatbot.py - ผู้ช่วยเรียน AI ของ SmartStudy

โหมดการทำงาน:
1. ถ้ามี API key (Gemini / Groq / OpenAI) จะเรียกโมเดลจริง
2. ถ้าไม่มีคีย์ จะใช้ผู้ช่วยในเครื่องที่รู้การบ้านของผู้ใช้ + ตอบคำถามเรียนพื้นฐาน
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

SYSTEM_PROMPT = """คุณคือ 'สมาร์ทตี้' ผู้ช่วยเรียนของแอป SmartStudy
พูดภาษาไทยสุภาพ เป็นกันเอง กระชับ ชัดเจน เหมาะกับนักเรียนมัธยม-มหาวิทยาลัย
หน้าที่หลัก:
- ช่วยวางแผนทำการบ้านตามข้อมูลงานจริงที่ให้มา
- อธิบายเนื้อหาวิชาให้เข้าใจง่าย พร้อมตัวอย่างสั้นๆ
- ให้กำลังใจและเทคนิคโฟกัส / Pomodoro
- อย่าแต่งข้อมูลการบ้านที่ไม่มีในรายการ
- ถ้าไม่แน่ใจ ให้บอกตรงๆ และแนะนำวิธีหาคำตอบ
ตอบสั้นพออ่านบนแชทได้ (ประมาณ 80-180 คำ) ใช้หัวข้อหรือ bullet เมื่อช่วยอ่าน"""


def build_homework_context(df: pd.DataFrame) -> str:
    """สรุปการบ้านของผู้ใช้เป็นข้อความให้โมเดลอ่าน"""
    if df is None or df.empty:
        return "ผู้ใช้ยังไม่มีการบ้านในระบบ"

    pending = df[~df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])]
    done = df[df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])]
    lines = [
        f"งานทั้งหมด {len(df)} ชิ้น, ค้าง {len(pending)} ชิ้น, เสร็จแล้ว {len(done)} ชิ้น"
    ]
    if pending.empty:
        lines.append("ไม่มีงานค้าง")
        return "\n".join(lines)

    ranked = pending.sort_values("urgency_score", ascending=False) if "urgency_score" in pending.columns else pending
    for _, row in ranked.head(8).iterrows():
        lines.append(
            f"- {row.get('title')} | วิชา {row.get('subject')} | ส่ง {row.get('due_date')} "
            f"({row.get('deadline_status', '')}) | สำคัญ {row.get('importance')}/5 | "
            f"ประมาณ {row.get('estimated_hours')} ชม. | {row.get('urgency_badge', '')}"
        )
    return "\n".join(lines)


def detect_provider(api_key: str) -> Optional[str]:
    """เดาผู้ให้บริการจากรูปแบบคีย์ หรือค่าที่ผู้ใช้เลือก"""
    key = (api_key or "").strip()
    if not key:
        return None
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith("sk-"):
        return "openai"
    if key.startswith("AIza"):
        return "gemini"
    return "gemini"


def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 45) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _messages_to_gemini(system: str, history: List[Dict[str, str]], user_text: str) -> List[Dict[str, Any]]:
    contents: List[Dict[str, Any]] = []
    contents.append({"role": "user", "parts": [{"text": system}]})
    contents.append({"role": "model", "parts": [{"text": "รับทราบค่ะ/ครับ จะช่วยวางแผนเรียนตามข้อมูลจริง"}]})
    for msg in history[-10:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": user_text}]})
    return contents


def call_llm(
    provider: str,
    api_key: str,
    user_text: str,
    homework_context: str,
    history: List[Dict[str, str]],
) -> str:
    """เรียก Gemini / Groq / OpenAI แล้วคืนข้อความตอบ"""
    prompt_user = f"ข้อมูลการบ้านปัจจุบัน:\n{homework_context}\n\nคำถามของนักเรียน:\n{user_text}"

    if provider == "gemini":
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={api_key}"
        )
        payload = {
            "contents": _messages_to_gemini(SYSTEM_PROMPT, history, prompt_user),
            "generationConfig": {"temperature": 0.6, "maxOutputTokens": 700},
        }
        result = _post_json(url, payload, {"Content-Type": "application/json"})
        candidates = result.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini ไม่ส่งคำตอบกลับมา")
        parts = candidates[0].get("content", {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            raise RuntimeError("Gemini ส่งข้อความว่าง")
        return text

    openai_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    openai_messages.append({"role": "system", "content": f"ข้อมูลการบ้าน:\n{homework_context}"})
    for msg in history[-10:]:
        openai_messages.append({"role": msg["role"], "content": msg["content"]})
    openai_messages.append({"role": "user", "content": user_text})

    if provider == "groq":
        url = "https://api.groq.com/openai/v1/chat/completions"
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": openai_messages,
            "temperature": 0.6,
            "max_tokens": 700,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    else:
        url = "https://api.openai.com/v1/chat/completions"
        payload = {
            "model": "gpt-4o-mini",
            "messages": openai_messages,
            "temperature": 0.6,
            "max_tokens": 700,
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    result = _post_json(url, payload, headers)
    return result["choices"][0]["message"]["content"].strip()


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def generate_local_reply(user_text: str, df: pd.DataFrame) -> str:
    """ผู้ช่วยในเครื่อง: วางแผนจากงานจริง + ตอบคำถามเรียนพื้นฐาน"""
    q = _normalize(user_text)
    pending = pd.DataFrame()
    if df is not None and not df.empty:
        pending = df[~df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])].copy()

    if any(k in q for k in ["สวัสดี", "hello", "hi", "หวัดดี", "ทัก"]):
        return (
            "สวัสดีครับ! ผมคือสมาร์ทตี้ ผู้ช่วยเรียนของ SmartStudy 🎓\n\n"
            "ถามได้เลย เช่น:\n"
            "• ควรทำการบ้านชิ้นไหนก่อน\n"
            "• สรุปงานที่ค้างอยู่\n"
            "• อธิบายอนุพันธ์ / เซลล์ / Python loop\n"
            "• เทคนิคโฟกัส Pomodoro"
        )

    if any(k in q for k in ["ทำชิ้นไหน", "ทำอะไรก่อน", "ควรเริ่ม", "แนะนำงาน", "ด่วนสุด", "อันดับ 1", "next"]):
        if pending.empty:
            return "ตอนนี้ไม่มีงานค้างเลยครับ 🎉 ใช้เวลาไปทบทวนวิชาที่อ่อน หรือพักผ่อนให้พร้อมรอบหน้าได้เลย"
        top = pending.sort_values("urgency_score", ascending=False).iloc[0]
        return (
            f"แนะนำให้เริ่ม **{top['title']}** วิช{top['subject']} ก่อนครับ {top.get('urgency_badge', '')}\n\n"
            f"เหตุผล: {top.get('recommendation_reason', 'งานนี้เร่งด่วนที่สุดในรายการ')}\n\n"
            f"📅 ส่ง {top['due_date']} ({top.get('deadline_status', '')}) · "
            f"⏱️ ประมาณ {top['estimated_hours']} ชม. · ⭐ สำคัญ {top['importance']}/5\n\n"
            "วิธีเริ่ม: เปิดนาฬิกา Pomodoro 25 นาที แล้วทำแค่ชิ้นนี้ชิ้นเดียวจนจบเซสชัน"
        )

    if any(k in q for k in ["งานค้าง", "สรุปงาน", "มีงานอะไร", "รายการการบ้าน", "เหลือกี่ชิ้น", "สถานะงาน", "การบ้านทั้งหมด", "การบ้านของฉัน"]):
        if pending.empty:
            return "สรุปแล้ว: **เคลียร์งานหมดแล้ว** ไม่มีชิ้นค้างส่งครับ เก่งมาก!"
        overdue = pending[pending.get("days_left", 0) < 0] if "days_left" in pending.columns else pending.iloc[0:0]
        lines = [f"งานที่ยังค้าง **{len(pending)}** ชิ้น" + (f" (เลยกำหนด {len(overdue)} ชิ้น)" if len(overdue) else "")]
        show = pending.sort_values("urgency_score", ascending=False) if "urgency_score" in pending.columns else pending
        for i, (_, row) in enumerate(show.head(6).iterrows(), start=1):
            lines.append(f"{i}. {row['title']} — {row['subject']} (ส่ง {row['due_date']})")
        lines.append("\nอยากให้จัดแผนทีละชิ้นไหมครับ? พิมพ์ว่า **ควรทำชิ้นไหนก่อน** ได้เลย")
        return "\n".join(lines)

    if any(k in q for k in ["pomodoro", "โพโมโดโร", "โฟกัส", "สมาธิ", "จับเวลา", "ขี้เกียจ", "ไม่มีสมาธิ"]):
        return (
            "เทคนิคโฟกัสที่ใช้ได้จริง:\n"
            "1. ตั้งเวลา **25 นาที** ทำชิ้นเดียว ปิดแจ้งเตือนมือถือ\n"
            "2. เมื่อหมดเวลา พัก 5 นาที ลุกยืดเส้น ดื่มน้ำ\n"
            "3. ครบ 4 รอบแล้วพักยาว 15 นาที\n\n"
            "ถ้าเริ่มยาก ให้สัญญาแค่ 10 นาทีแรก สมองมักไหลต่อเอง "
            "ไปที่เมนู ⏱️ โหมดจับเวลาโฟกัส ในแอปนี้ได้เลยครับ"
        )

    knowledge = _subject_knowledge(q)
    if knowledge:
        return knowledge

    if pending is not None and not pending.empty:
        top = pending.sort_values("urgency_score", ascending=False).iloc[0] if "urgency_score" in pending.columns else pending.iloc[0]
        hint = f"\n\nงานด่วนสุดตอนนี้คือ **{top['title']}** ({top['subject']}) ส่ง {top['due_date']}"
    else:
        hint = ""

    return (
        "ผมช่วยได้ 3 แบบหลักครับ:\n"
        "• วางแผนการบ้านจากงานในระบบ\n"
        "• อธิบายเนื้อหา เช่น อนุพันธ์, นิวตัน, เซลล์, loop ใน Python, essay\n"
        "• เทคนิคเรียน / Pomodoro\n\n"
        "ลองพิมพ์คำถามให้เจาะจงขึ้นอีกนิด เช่น *อธิบายอนุพันธ์แบบง่าย* "
        "หรือ *สรุปงานที่ค้าง*"
        f"{hint}\n\n"
        "💡 ถ้าใส่ API key (Gemini/Groq/OpenAI) ที่กล่องด้านบน สมาร์ทตี้จะตอบแบบโมเดลจริงได้กว้างขึ้น"
    )


def _subject_knowledge(q: str) -> Optional[str]:
    """คลังคำอธิบายสั้นสำหรับวิชาหลัก"""
    if any(k in q for k in ["อนุพันธ์", "derivative", "ดิฟ", "แคลคูลัส"]):
        return (
            "**อนุพันธ์** คืออัตราการเปลี่ยนแปลงของฟังก์ชัน ณ จุดหนึ่ง\n\n"
            "ถ้า f(x) = x² แล้ว f'(x) = 2x\n"
            "แปลว่าที่ x = 3 ความชันเท่ากับ 6\n\n"
            "สูตรที่ใช้บ่อย:\n"
            "• (xⁿ)' = n xⁿ⁻¹\n"
            "• ค่าคงที่อนุพันธ์เป็น 0\n"
            "• (fg)' = f'g + fg'\n\n"
            "ทริค: ถามตัวเองว่า *ค่านี้เพิ่มขึ้นเร็วแค่ไหน* — นั่นคืออนุพันธ์"
        )
    if any(k in q for k in ["อินทิกรัล", "integral", "ปริพันธ์"]):
        return (
            "**อินทิกรัล** คือการหาพื้นที่ใต้กราฟ หรือการย้อนอนุพันธ์\n\n"
            "ถ้า F'(x) = f(x) แล้ว ∫ f(x) dx = F(x) + C\n"
            "ตัวอย่าง: ∫ 2x dx = x² + C\n\n"
            "อินทิกรัลจำกัดเขต ∫ จาก a ถึง b ของ f(x) = F(b) − F(a) คือพื้นที่ใต้กราฟ"
        )
    if any(k in q for k in ["นิวตัน", "newton", "f=ma", "แรง", "กฏข้อ 2", "กฎข้อ 2"]):
        return (
            "**กฎของนิวตันข้อ 2:** F = ma\n"
            "แรงลัพธ์ = มวล × ความเร่ง\n\n"
            "หน่วย: F เป็นนิวตัน (N), m เป็นกิโลกรัม, a เป็น m/s²\n"
            "ตัวอย่าง: มวล 2 kg ความเร่ง 3 m/s² → แรง 6 N\n\n"
            "อย่าลืมรวมแรงทุกทิศทางเป็นแรงลัพธ์ก่อนค่อยแทนสูตร"
        )
    if any(k in q for k in ["เซลล์", "cell", "ไมโทคอนเดรีย", "คลอโรพลาสต์"]):
        return (
            "**เซลล์** คือหน่วยเล็กสุดของสิ่งมีชีวิต\n\n"
            "• พืช: มีผนังเซลล์ + คลอโรพลาสต์ (สังเคราะห์แสง)\n"
            "• สัตว์: ไม่มีผนังเซลล์/คลอโรพลาสต์ แต่มีไมโทคอนเดรียเหมือนกัน\n"
            "• ไมโทคอนเดรีย = โรงงานพลังงาน (ATP)\n"
            "• นิวเคลียส = ศูนย์ควบคุม มี DNA"
        )
    if any(k in q for k in ["loop", "ลูป", "for ", "while", "python"]):
        return (
            "**Loop ใน Python** ใช้ทำซ้ำโดยไม่ต้องเขียนโค้ดซ้ำ\n\n"
            "```python\n"
            "for i in range(5):\n"
            "    print(i)   # 0 1 2 3 4\n"
            "```\n"
            "```python\n"
            "n = 3\n"
            "while n > 0:\n"
            "    print(n)\n"
            "    n -= 1\n"
            "```\n"
            "`for` รู้จำนวนรอบชัด, `while` วนจนกว่าเงื่อนไขจะเท็จ"
        )
    if any(k in q for k in ["essay", "เรียงความ", "paragraph", "อังกฤษ"]):
        return (
            "โครงเรียงความภาษาอังกฤษแบบง่าย:\n\n"
            "1. **Intro** — บอกหัวข้อ + thesis 1 ประโยค\n"
            "2. **Body 2-3 ย่อหน้า** — 1 ย่อหน้า = 1 เหตุผล + ตัวอย่าง\n"
            "3. **Conclusion** — สรุปประเด็น ไม่ยกเรื่องใหม่\n\n"
            "ประโยคเปิดที่ใช้ได้: *This essay discusses ... because ...*\n"
            "ถ้าส่งงาน AI & Future: เลือก 2 มุม เช่น ประโยชน์ต่อการศึกษา vs ความเสี่ยงงานหาย"
        )
    if any(k in q for k in ["กำลังใจ", "ท้อ", "เหนื่อย", "สอบ", "เครียด"]):
        return (
            "เครียดแล้วแปลว่าคุณใส่ใจงานอยู่ครับ ซึ่งดีมาก\n\n"
            "ลองซอยงานเป็นชิ้นเล็ก: ไม่ต้องทำให้จบวันนี้ทั้งก้อน "
            "แค่ปิด 1 รอบ Pomodoro ก็ถือว่าชนะแล้ว\n"
            "หายใจเข้า 4 วินาที กลั้น 4 วินาที หายใจออก 4 วินาที แล้วเริ่มชิ้นที่เล็กที่สุด"
        )
    return None


def resolve_api_key(session_key: str = "") -> str:
    """ลำดับความสำคัญ: คีย์ที่กรอกในแอป > environment"""
    if session_key and session_key.strip():
        return session_key.strip()
    for name in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENAI_API_KEY"):
        val = os.environ.get(name, "").strip()
        if val:
            return val
    return ""


def reply(
    user_text: str,
    df: pd.DataFrame,
    history: List[Dict[str, str]],
    api_key: str = "",
    provider_choice: str = "auto",
) -> Tuple[str, str]:
    """
    คืนค่า (ข้อความตอบ, โหมดที่ใช้)
    โหมด: gemini | groq | openai | local
    """
    text = (user_text or "").strip()
    if not text:
        return "พิมพ์คำถามมาได้เลยครับ เช่น 'ควรทำการบ้านชิ้นไหนก่อน'", "local"

    key = resolve_api_key(api_key)
    homework = build_homework_context(df)

    if key:
        provider = provider_choice if provider_choice in {"gemini", "groq", "openai"} else detect_provider(key)
        try:
            answer = call_llm(provider, key, text, homework, history)
            return answer, provider
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")[:180]
            fallback = generate_local_reply(text, df)
            return (
                f"เรียกโมเดล {provider} ไม่สำเร็จ (รหัส {exc.code}) จึงตอบด้วยโหมดในเครื่องก่อนครับ\n\n{fallback}\n\n"
                f"รายละเอียดสั้นๆ: {detail}",
                "local",
            )
        except Exception:
            fallback = generate_local_reply(text, df)
            return (
                "ตอนนี้ต่อโมเดลออนไลน์ไม่ได้ จึงใช้ผู้ช่วยในเครื่องตอบให้ก่อนครับ\n\n" + fallback,
                "local",
            )

    return generate_local_reply(text, df), "local"
