# Functions for database creation and usage for habit tracking
# Still a work in progress
# Author: Stavros
# Date: Apr 12 2024

import sqlite3
from datetime import datetime

DATABASE_NAME = 'wheatley.db'

def create_habits_table():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            habit_name TEXT NOT NULL,
            streak INTEGER DEFAULT 0,
            last_completed DATETIME,
            reminder_time TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            completed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def create_habit(user_id, habit_name, reminder_time):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO habits (user_id, habit_name, reminder_time) VALUES (?, ?, ?)',
                   (user_id, habit_name, reminder_time))
    conn.commit()
    conn.close()

def get_habits(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT habit_name, streak, last_completed, reminder_time FROM habits WHERE user_id = ?', (user_id,))
    habits = cursor.fetchall()
    conn.close()
    return habits

def mark_habit_completed(user_id, habit_name):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE habits SET streak = streak + 1, last_completed = DATETIME('now'), completed = 1 WHERE user_id = ? AND habit_name = ?",
                   (user_id, habit_name))
    conn.commit()
    conn.close()

def reset_habit_streak(user_id, habit_name):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE habits SET streak = 0, last_completed = NULL WHERE user_id = ? AND habit_name = ?',
                   (user_id, habit_name))
    conn.commit()
    conn.close()

def delete_habit(user_id, habit_name):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM habits WHERE user_id = ? AND habit_name = ?', (user_id, habit_name))
    conn.commit()
    conn.close()

def get_all_habits():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * from habits')
    allhabits = cursor.fetchall()
    conn.close()
    return allhabits

def update_habit(user_id, habit_name, new_reminder_time):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('UPDATE habits SET reminder_time = ?, updated_at = DATETIME(\'now\') WHERE user_id = ? AND habit_name = ?', (new_reminder_time, user_id, habit_name))
    conn.commit()
    conn.close()

def get_all_habits_with_times():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, habit_name, reminder_time, streak FROM habits')
    habits = cursor.fetchall()
    conn.close()
    return habits


# Initialize the database table if it doesn't exist
create_habits_table()
