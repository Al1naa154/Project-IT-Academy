from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)
DB_NAME = "habits.db"

def get_db():
    return sqlite3.connect(DB_NAME)


def init_db():
    with get_db() as db:
        db.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tag TEXT
        )""")

        db.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            log_date TEXT,
            FOREIGN KEY (habit_id) REFERENCES habits(id)
        )""")

class Habit:
    def __init__(self, name, tag):
        self.name = name
        self.tag = tag

    def save(self):
        with get_db() as db:
            db.execute("INSERT INTO habits (name, tag) VALUES (?, ?)", (self.name, self.tag))


class HabitService:
    @staticmethod
    def get_all():
        with get_db() as db:
            return db.execute("SELECT * FROM habits").fetchall()

    @staticmethod
    def log_today(habit_id):
        today = date.today().isoformat()
        with get_db() as db:
            db.execute("INSERT INTO habit_logs (habit_id, log_date) VALUES (?, ?)", (habit_id, today))

    @staticmethod
    def get_logs(habit_id):
        with get_db() as db:
            rows = db.execute(
                "SELECT log_date FROM habit_logs WHERE habit_id = ? ORDER BY log_date",
                (habit_id,)
            ).fetchall()
        return [r[0] for r in rows]

    @staticmethod
    def calculate_streak(habit_id):
        logs = HabitService.get_logs(habit_id)
        streak = 0
        current_day = date.today()

        for log in reversed(logs):
            if date.fromisoformat(log) == current_day:
                streak += 1
                current_day -= timedelta(days=1)
            else:
                break
        return streak

HTML = """
<!doctype html>
<title>Трекер привычек</title>
<h1>Трекер привычек</h1>

<h2>Добавить привычку</h2>
<form method="post" action="/add">
  Название: <input name="name" required>
  Тег: <input name="tag">
  <button>Добавить</button>
</form>

<h2>Мои привычки</h2>
<ul>
{% for h in habits %}
  <li>
    <b>{{ h[1] }}</b> ({{ h[2] }}) | Streak: {{ streaks[h[0]] }} дней
    <a href="/log/{{ h[0] }}">✔ Отметить сегодня</a>
  </li>
{% endfor %}
</ul>
"""

@app.route("/")
def index():
    habits = HabitService.get_all()
    streaks = {h[0]: HabitService.calculate_streak(h[0]) for h in habits}
    return render_template_string(HTML, habits=habits, streaks=streaks)


@app.route("/add", methods=["POST"])
def add():
    habit = Habit(request.form["name"], request.form["tag"])
    habit.save()
    return redirect(url_for("index"))


@app.route("/log/<int:habit_id>")
def log(habit_id):
    HabitService.log_today(habit_id)
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
