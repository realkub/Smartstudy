"""
test_planner.py - Unit tests for SmartStudy's urgency algorithm, database, and authentication.

ทดสอบอัลกอริทึมการคำนวณความเร่งด่วน, ฐานข้อมูล, และระบบ Authentication:
    python -m unittest test_planner.py
"""

import unittest
from datetime import date, timedelta
import os
import database
import planner


class TestSmartStudyPlanner(unittest.TestCase):

    def test_days_remaining_today(self):
        today_str = date.today().strftime("%Y-%m-%d")
        days = planner.calculate_days_remaining(today_str)
        self.assertEqual(days, 0)

    def test_days_remaining_future(self):
        future_str = (date.today() + timedelta(days=5)).strftime("%Y-%m-%d")
        days = planner.calculate_days_remaining(future_str)
        self.assertEqual(days, 5)

    def test_days_remaining_overdue(self):
        past_str = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
        days = planner.calculate_days_remaining(past_str)
        self.assertEqual(days, -2)

    def test_overdue_task_urgency_tier(self):
        task = {
            "title": "การบ้านคณิตศาสตร์ส่งช้า",
            "subject": "คณิตศาสตร์",
            "due_date": (date.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "estimated_hours": 2.0,
            "importance": 4
        }
        res = planner.calculate_task_urgency(task)
        self.assertEqual(res["urgency_tier"], "Critical")
        self.assertIn("เลยกำหนด", res["deadline_status"])
        self.assertGreaterEqual(res["urgency_score"], 100.0)

    def test_future_low_priority_task(self):
        task = {
            "title": "อ่านหนังสือนอกเวลา",
            "subject": "ภาษาไทย",
            "due_date": (date.today() + timedelta(days=14)).strftime("%Y-%m-%d"),
            "estimated_hours": 1.0,
            "importance": 1
        }
        res = planner.calculate_task_urgency(task)
        self.assertEqual(res["urgency_tier"], "Low")
        self.assertLess(res["urgency_score"], 60.0)


class TestDatabaseAndAuth(unittest.TestCase):

    def setUp(self):
        database.DB_FILE = "test_smartstudy.db"
        database.init_db()
        conn = database.get_connection()
        try:
            conn.execute("DELETE FROM tasks")
            conn.execute("DELETE FROM users")
            conn.commit()
        finally:
            conn.close()

    def tearDown(self):
        if os.path.exists("test_smartstudy.db"):
            try:
                os.remove("test_smartstudy.db")
            except Exception:
                pass

    def test_register_and_authenticate_user(self):
        success, msg = database.register_user("testuser", "securepass123", "นายทดสอบ โปรแกรมเมอร์")
        self.assertTrue(success)

        # Login with correct password
        auth_ok, user_info, _ = database.authenticate_user("testuser", "securepass123")
        self.assertTrue(auth_ok)
        self.assertEqual(user_info["username"], "testuser")
        self.assertEqual(user_info["full_name"], "นายทดสอบ โปรแกรมเมอร์")

        # Login with wrong password
        fail_ok, _, _ = database.authenticate_user("testuser", "wrongpassword")
        self.assertFalse(fail_ok)

    def test_duplicate_username_rejected(self):
        database.register_user("alex", "pass1234", "Alex Smith")
        success, _ = database.register_user("alex", "pass5678", "Alex Another")
        self.assertFalse(success)

    def test_add_and_retrieve_task_with_user_id(self):
        success, _ = database.register_user("somchai", "pass1234", "สมชาย เรียนดี")
        self.assertTrue(success)
        _, user, _ = database.authenticate_user("somchai", "pass1234")
        user_id = user["id"]

        task_id = database.add_task(
            title="เรียงความประวัติศาสตร์",
            subject="สังคม",
            due_date="2026-10-20",
            estimated_hours=3.5,
            importance=4,
            user_id=user_id
        )
        self.assertIsInstance(task_id, int)
        df = database.get_all_tasks(user_id=user_id)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["title"], "เรียงความประวัติศาสตร์")
        self.assertEqual(df.iloc[0]["status"], "รอดำเนินการ")

    def test_update_and_delete_task(self):
        task_id = database.add_task(
            title="เตรียมสอบชีววิทยา",
            subject="ชีววิทยา",
            due_date="2026-10-21",
            estimated_hours=1.5,
            importance=3,
            user_id=1
        )
        database.update_task_status(task_id, "เสร็จสิ้นแล้ว", user_id=1)
        df = database.get_all_tasks(user_id=1)
        self.assertEqual(df.iloc[0]["status"], "เสร็จสิ้นแล้ว")

        database.delete_task(task_id, user_id=1)
        df_after = database.get_all_tasks(user_id=1)
        self.assertEqual(len(df_after), 0)


class TestChatbot(unittest.TestCase):

    def test_detect_provider(self):
        import chatbot
        self.assertEqual(chatbot.detect_provider("gsk_abc"), "groq")
        self.assertEqual(chatbot.detect_provider("sk-abc"), "openai")
        self.assertEqual(chatbot.detect_provider("AIzaSyDummy"), "gemini")
        self.assertIsNone(chatbot.detect_provider(""))

    def test_local_reply_greeting_and_derivative(self):
        import chatbot
        import pandas as pd
        empty = pd.DataFrame()
        hi = chatbot.generate_local_reply("สวัสดีครับ", empty)
        self.assertIn("สมาร์ทตี้", hi)
        calc = chatbot.generate_local_reply("อธิบายอนุพันธ์แบบง่าย", empty)
        self.assertIn("อนุพันธ์", calc)

    def test_local_reply_uses_homework(self):
        import chatbot
        import pandas as pd
        tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
        df = pd.DataFrame([{
            "id": 1,
            "title": "แบบฝึกหัดแคลคูลัส",
            "subject": "คณิตศาสตร์",
            "due_date": tomorrow,
            "estimated_hours": 3.0,
            "importance": 5,
            "status": "รอดำเนินการ",
            "urgency_score": 120,
            "urgency_badge": "🔴 ด่วนที่สุด",
            "deadline_status": "ส่งพรุ่งนี้!",
            "recommendation_reason": "ต้องส่งพรุ่งนี้แล้ว",
            "days_left": 1,
        }])
        answer = chatbot.generate_local_reply("ควรทำการบ้านชิ้นไหนก่อน", df)
        self.assertIn("แบบฝึกหัดแคลคูลัส", answer)


if __name__ == "__main__":
    unittest.main()
