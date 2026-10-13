"""
planner.py - Task Urgency Calculation and Recommendation Engine for SmartStudy.

โมดูลคำนวณระดับความเร่งด่วนของงานและการบ้าน (Prioritization & Recommendation Engine):
1. คำนวณจำนวนวันที่เหลือก่อนถึงกำหนดส่ง
2. คำนวณคะแนนความเร่งด่วน (Urgency Score) อิงจากกำหนดส่ง, ความสำคัญ, และเวลาที่ต้องใช้
3. จัดกลุ่มระดับความเร่งด่วน (Critical, High, Medium, Low)
4. สร้างคำแนะนำเป็นภาษาไทยที่อธิบายเหตุผลว่าทำไมควรทำงานนี้ก่อน
"""

from datetime import datetime, date
from typing import Dict, Any, List
import pandas as pd


def calculate_days_remaining(due_date_str: str) -> int:
    """
    คำนวณจำนวนวันระหว่างวันนี้กับวันกำหนดส่ง
    - ค่าติดลบ (< 0): เลยกำหนดส่งแล้ว
    - 0: ต้องส่งวันนี้
    - ค่าบวก (> 0): เหลือเวลาอีก N วัน
    """
    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    today = date.today()
    delta = (due_date - today).days
    return delta


def calculate_task_urgency(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    คำนวณคะแนนความเร่งด่วน (Urgency Score) สำหรับการบ้านแต่ละชิ้น

    องค์ประกอบของอัลกอริทึม:
    1. ความใกล้ของวันส่ง (Base Urgency):
       - งานที่เลยกำหนด: ได้คะแนนสูงสุด (100 - 125 แต้ม)
       - ส่งวันนี้: 90 แต้ม
       - ส่งพรุ่งนี้: 75 แต้ม
       - ส่งภายใน 3 วัน: 60 แต้ม
       - ส่งภายใน 7 วัน: 40 แต้ม
       - ส่งหลังจากนั้น: 10 - 30 แต้ม
    2. ค่าน้ำหนักความสำคัญ (Importance Score):
       - ระดับ 1-5 คูณด้วย 8 (ได้ 8 ถึง 40 แต้ม)
    3. เวลาที่ต้องใช้ทำ (Workload Score):
       - งานที่ใช้เวลาทำนานต้องเริ่มวางแผนก่อน (ได้สูงสุด 15 แต้ม)
    """
    due_date_str = str(task["due_date"])
    importance = int(task.get("importance", 3))
    estimated_hours = float(task.get("estimated_hours", 1.0))
    days_left = calculate_days_remaining(due_date_str)

    # 1. คำนวณคะแนนความใกล้ของวันส่ง
    if days_left < 0:
        base_urgency = 100.0 + min(abs(days_left) * 5.0, 25.0)
        deadline_status = f"เลยกำหนด ({abs(days_left)} วัน)"
    elif days_left == 0:
        base_urgency = 90.0
        deadline_status = "ส่งวันนี้!"
    elif days_left == 1:
        base_urgency = 75.0
        deadline_status = "ส่งพรุ่งนี้!"
    elif days_left <= 3:
        base_urgency = 60.0
        deadline_status = f"เหลืออีก {days_left} วัน"
    elif days_left <= 7:
        base_urgency = 40.0
        deadline_status = f"เหลืออีก {days_left} วัน"
    else:
        base_urgency = max(10.0, 30.0 - (days_left - 7) * 1.5)
        deadline_status = f"เหลืออีก {days_left} วัน"

    # 2. คะแนนระดับความสำคัญ (1-5 -> 8 ถึง 40 แต้ม)
    importance_score = importance * 8.0

    # 3. คะแนนเวลาที่ต้องใช้ทำ (0 ถึง 15 แต้ม)
    workload_score = min(estimated_hours * 2.5, 15.0)

    # คะแนนรวม
    total_score = base_urgency + importance_score + workload_score

    # จำแนกระดับความเร่งด่วน (Urgency Tier)
    if days_left < 0 or days_left == 0 or total_score >= 115:
        urgency_tier = "Critical"
        urgency_tier_th = "วิกฤต / ด่วนที่สุด"
        urgency_badge = "🔴 ด่วนที่สุด"
    elif total_score >= 90:
        urgency_tier = "High"
        urgency_tier_th = "เร่งด่วนสูง"
        urgency_badge = "🟠 ด่วนมาก"
    elif total_score >= 60:
        urgency_tier = "Medium"
        urgency_tier_th = "ปานกลาง"
        urgency_badge = "🟡 ปานกลาง"
    else:
        urgency_tier = "Low"
        urgency_tier_th = "ทยอยทำได้"
        urgency_badge = "🟢 ไม่เร่งด่วน"

    # สร้างคำอธิบายเหตุผลเป็นภาษาไทย
    if days_left < 0:
        reason = f"เลยกำหนดส่งมาแล้ว {abs(days_left)} วัน! ต้องใช้เวลาทำประมาณ {estimated_hours} ชม. ควรรีบเคลียร์ทันทีเพื่อไม่ให้ถูกตัดคะแนน"
    elif days_left == 0:
        reason = f"กำหนดส่งคือวันนี้! ต้องใช้เวลาประมาณ {estimated_hours} ชม. เริ่มทำทันทีก่อนหมดวัน"
    elif days_left == 1:
        reason = f"ต้องส่งพรุ่งนี้แล้ว ความสำคัญระดับ {importance}/5 ต้องใช้เวลา {estimated_hours} ชม. เริ่มเลยเพื่อไม่ต้องอดนอน"
    elif importance >= 4 and days_left <= 3:
        reason = f"งานสำคัญมาก ({importance}/5) และเหลือเวลาอีก {days_left} วัน (ประมาณ {estimated_hours} ชม.) ควรเริ่มวางโครงร่างตอนนี้"
    elif estimated_hours >= 4.0:
        reason = f"เป็นงานใหญ่ที่ต้องใช้เวลาถึง {estimated_hours} ชั่วโมง ควรทยอยแบ่งทำตั้งแต่วันนี้"
    else:
        reason = f"ยังมีเวลาเตรียมตัวอีก {days_left} วัน วางแผนอ่านหรือทยอยทำแบบสบายๆ ได้"

    return {
        "days_left": days_left,
        "deadline_status": deadline_status,
        "urgency_score": round(total_score, 1),
        "urgency_tier": urgency_tier,
        "urgency_tier_th": urgency_tier_th,
        "urgency_badge": urgency_badge,
        "recommendation_reason": reason,
    }


def analyze_and_rank_tasks(df: pd.DataFrame) -> pd.DataFrame:
    """
    รับ DataFrame การบ้านทั้งหมด คำนวณความเร่งด่วน และเรียงลำดับจากด่วนสุดไปน้อยสุด
    """
    if df.empty:
        return pd.DataFrame()

    enriched_records = []
    for _, row in df.iterrows():
        task_dict = row.to_dict()
        urgency_metrics = calculate_task_urgency(task_dict)
        combined = {**task_dict, **urgency_metrics}
        enriched_records.append(combined)

    enriched_df = pd.DataFrame(enriched_records)

    # เรียงลำดับ: งานที่ยังไม่เสร็จขึ้นก่อน แล้วตามด้วยคะแนนความเร่งด่วนมากไปน้อย
    enriched_df["is_completed"] = enriched_df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])
    enriched_df = enriched_df.sort_values(
        by=["is_completed", "urgency_score"],
        ascending=[True, False]
    ).reset_index(drop=True)

    return enriched_df


def get_top_recommendation(ranked_df: pd.DataFrame):
    """
    ดึงงานที่ต้องทำด่วนที่สุด 1 ชิ้นแรกที่ยังไม่เสร็จ (Pending)
    """
    if ranked_df.empty:
        return None

    pending_tasks = ranked_df[~ranked_df["status"].isin(["Completed", "เสร็จสิ้นแล้ว"])]
    if pending_tasks.empty:
        return None

    return pending_tasks.iloc[0].to_dict()
