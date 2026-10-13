"""
database.py - Database operations & User Authentication for SmartStudy.

โมดูลจัดการฐานข้อมูล SQLite และระบบยืนยันตัวตน (Authentication):
- ตาราง 'users': จัดการการสมัครสมาชิก, เข้าสู่ระบบ, แฮชรหัสผ่านด้วย SHA-256
- ตาราง 'tasks': ผูกการบ้านเข้ากับ user_id ของแต่ละคน (Multi-user Isolation)
"""

import sqlite3
import os
import hashlib
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Tuple
import pandas as pd

DB_FILE = "smartstudy.db"
SALT = "smartstudy_secure_portfolio_salt_2026"


def hash_password(password: str) -> str:
    """แฮชรหัสผ่านด้วย SHA-256 ร่วมกับ Salt เพื่อความปลอดภัย ไม่เก็บรหัสผ่านจริง"""
    return hashlib.sha256((password + SALT).encode("utf-8")).hexdigest()


def get_connection():
    """เปิดการเชื่อมต่อกับ SQLite โดยใช้ row_factory เพื่อให้อ่านข้อมูลแบบ dict ได้"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    สร้างตาราง users และ tasks หากยังไม่มี
    และอัปเกรดคอลัมน์ user_id ใน tasks ให้โดยอัตโนมัติ
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. ตาราง users
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # 2. ตาราง tasks
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                due_date TEXT NOT NULL,
                estimated_hours REAL NOT NULL,
                importance INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'รอดำเนินการ',
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)

        # ตรวจสอบว่ามีคอลัมน์ user_id ใน tasks หรือยัง (กรณีฐานข้อมูลเดิม)
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "user_id" not in columns:
            cursor.execute("ALTER TABLE tasks ADD COLUMN user_id INTEGER NOT NULL DEFAULT 1")

        conn.commit()

        # สร้างผู้ใช้ทดลอง (Demo User) หากยังไม่มีผู้ใช้ในระบบเลย
        cursor.execute("SELECT COUNT(*) FROM users")
        if cursor.fetchone()[0] == 0:
            demo_created = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO users (username, password_hash, full_name, created_at)
                VALUES (?, ?, ?, ?)
            """, ("student", hash_password("password123"), "น้องสมาร์ท สตัดดี้ (นักเรียนตัวอย่าง)", demo_created))
            conn.commit()

    finally:
        conn.close()


# ----------------- ฟังก์ชันจัดการผู้ใช้งาน (USER AUTHENTICATION) -----------------

def register_user(username: str, password: str, full_name: str) -> Tuple[bool, str]:
    """
    สมัครสมาชิกผู้ใช้ใหม่
    Returns: (ความสำเร็จ True/False, ข้อความแจ้งเตือน)
    """
    username = username.strip().lower()
    full_name = full_name.strip()

    if len(username) < 3:
        return False, "ชื่อผู้ใช้ (Username) ต้องมีความยาวอย่างน้อย 3 ตัวอักษร"
    if len(password) < 4:
        return False, "รหัสผ่านต้องมีความยาวอย่างน้อย 4 ตัวอักษร"
    if len(full_name) < 2:
        return False, "กรุณากรอกชื่อ-นามสกุลให้ถูกต้อง"

    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, f"ชื่อผู้ใช้ '{username}' มีอยู่ในระบบแล้ว กรุณาใช้ชื่ออื่น"

        pw_hash = hash_password(password)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO users (username, password_hash, full_name, created_at)
            VALUES (?, ?, ?, ?)
        """, (username, pw_hash, full_name, created_at))
        conn.commit()
        return True, "สมัครสมาชิกสำเร็จ! สามารถเข้าสู่ระบบได้เลยครับ"
    except Exception as e:
        return False, f"เกิดข้อผิดพลาดในการสมัครสมาชิก: {e}"
    finally:
        conn.close()


def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """
    ตรวจสอบชื่อผู้ใช้และรหัสผ่านเพื่อเข้าสู่ระบบ
    Returns: (ผ่านหรือไม่, ข้อมูล user dict, ข้อความ)
    """
    username = username.strip().lower()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user_row = cursor.fetchone()
        if not user_row:
            return False, None, "ไม่พบชื่อผู้ใช้นี้ในระบบ"

        if user_row["password_hash"] != hash_password(password):
            return False, None, "รหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง"

        user_dict = {
            "id": user_row["id"],
            "username": user_row["username"],
            "full_name": user_row["full_name"],
            "created_at": user_row["created_at"]
        }
        return True, user_dict, "เข้าสู่ระบบสำเร็จ!"
    finally:
        conn.close()


# ----------------- ฟังก์ชันจัดการการบ้าน (TASK OPERATIONS) -----------------

def add_task(title: str, subject: str, due_date: str, estimated_hours: float, importance: int, user_id: int = 1) -> int:
    """
    เพิ่มการบ้านใหม่ โดยผูกเข้ากับ user_id ของผู้ใช้คนนั้น
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (user_id, title, subject, due_date, estimated_hours, importance, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'รอดำเนินการ', ?)
        """, (int(user_id), title.strip(), subject.strip(), due_date, float(estimated_hours), int(importance), created_at))
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_tasks(user_id: int = 1) -> pd.DataFrame:
    """
    ดึงข้อมูลการบ้านทั้งหมดเฉพาะของ user_id ที่ระบุออกมาเป็น Pandas DataFrame
    """
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date ASC",
            conn,
            params=(int(user_id),)
        )
        return df
    finally:
        conn.close()


def update_task_status(task_id: int, new_status: str, user_id: int = 1):
    """
    อัปเดตสถานะงาน (ตรวจสอบ user_id เพื่อป้องกันการแก้ไขงานของผู้อื่น)
    """
    completed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status in ["เสร็จสิ้นแล้ว", "Completed"] else None
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE tasks
            SET status = ?, completed_at = ?
            WHERE id = ? AND user_id = ?
        """, (new_status, completed_at, int(task_id), int(user_id)))
        conn.commit()
    finally:
        conn.close()


def delete_task(task_id: int, user_id: int = 1):
    """ลบการบ้านออกจากฐานข้อมูลถาวรเฉพาะของผู้ใช้นั้น"""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (int(task_id), int(user_id)))
        conn.commit()
    finally:
        conn.close()


def seed_sample_data(user_id: int = 1):
    """
    โหลดข้อมูลการบ้านตัวอย่างภาษาไทย ให้กับ user_id ที่ระบุ
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE user_id = ?", (int(user_id),))
        count = cursor.fetchone()[0]
        if count == 0:
            today = date.today()
            sample_tasks = [
                ("แบบฝึกหัดแคลคูลัส ชุดที่ 4 เรื่องอนุพันธ์", "คณิตศาสตร์", (today + timedelta(days=1)).strftime("%Y-%m-%d"), 3.0, 5),
                ("เขียนเรียงความภาษาอังกฤษ หัวข้อ AI & Future", "ภาษาอังกฤษ", (today + timedelta(days=3)).strftime("%Y-%m-%d"), 4.0, 4),
                ("รายงานแล็บฟิสิกส์ เรื่องการหักเหของแสง", "ฟิสิกส์", (today - timedelta(days=1)).strftime("%Y-%m-%d"), 2.0, 4),
                ("เตรียมตัวสอบเขียนโปรแกรม Python (Loops & Functions)", "คอมพิวเตอร์", (today + timedelta(days=5)).strftime("%Y-%m-%d"), 2.5, 3),
                ("อ่านสรุปประวัติศาสตร์ไทย บทที่ 5", "สังคม / ประวัติศาสตร์", (today + timedelta(days=7)).strftime("%Y-%m-%d"), 1.5, 2),
                ("ใบงานชีววิทยา โครงสร้างเซลล์พืชและสัตว์", "ชีววิทยา", (today - timedelta(days=2)).strftime("%Y-%m-%d"), 1.0, 1),
            ]
            for title, subj, due, hours, imp in sample_tasks:
                cursor.execute("""
                    INSERT INTO tasks (user_id, title, subject, due_date, estimated_hours, importance, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, 'รอดำเนินการ', ?)
                """, (int(user_id), title, subj, due, hours, imp, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            
            # ตั้งค่าให้ใบงานชีววิทยาเป็นงานที่เสร็จแล้วเพื่อแสดงในกราฟ
            cursor.execute("""
                UPDATE tasks SET status = 'เสร็จสิ้นแล้ว', completed_at = ?
                WHERE title = 'ใบงานชีววิทยา โครงสร้างเซลล์พืชและสัตว์' AND user_id = ?
            """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), int(user_id)))
            conn.commit()
    finally:
        conn.close()
