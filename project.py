from flask import Flask, render_template_string, request, redirect, url_for
import mysql.connector
from datetime import date, timedelta

app = Flask(__name__)


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1210",
    "database": "habit_tracker"
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)



def init_db():
    with get_db() as db:
        cursor = db.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS habits (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            tag VARCHAR(100),
            target_days INT NOT NULL,
            completed BOOLEAN DEFAULT FALSE
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS habit_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            habit_id INT,
            log_date DATE,
            FOREIGN KEY (habit_id) REFERENCES habits(id) ON DELETE CASCADE
        )
        """)

        db.commit()



class Habit:
    def __init__(self, name, tag, target_days):
        self.name = name
        self.tag = tag
        self.target_days = target_days

    def save(self):
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO habits (name, tag, target_days) VALUES (%s, %s, %s)",
                (self.name, self.tag, self.target_days)
            )
            db.commit()


class HabitService:

    @staticmethod
    def get_active():
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM habits WHERE completed = FALSE")
            return cursor.fetchall()

    @staticmethod
    def get_completed():
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("SELECT * FROM habits WHERE completed = TRUE")
            return cursor.fetchall()

    @staticmethod
    def delete(habit_id):
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute("DELETE FROM habits WHERE id = %s", (habit_id,))
            db.commit()

    @staticmethod
    def log_today(habit_id):
        today = date.today()
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO habit_logs (habit_id, log_date) VALUES (%s, %s)",
                (habit_id, today)
            )
            db.commit()

        if HabitService.calculate_progress(habit_id)[0] >= HabitService.get_target(habit_id):
            HabitService.mark_completed(habit_id)

    @staticmethod
    def get_logs(habit_id):
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT log_date FROM habit_logs WHERE habit_id = %s ORDER BY log_date",
                (habit_id,)
            )
            return [row[0] for row in cursor.fetchall()]

    @staticmethod
    def calculate_streak(habit_id):
        logs = HabitService.get_logs(habit_id)
        streak = 0
        current = date.today()

        for log in reversed(logs):
            if log == current:
                streak += 1
                current -= timedelta(days=1)
            else:
                break
        return streak

    @staticmethod
    def calculate_progress(habit_id):
        logs = HabitService.get_logs(habit_id)
        done = len(set(logs))
        target = HabitService.get_target(habit_id)
        return done, target

    @staticmethod
    def get_target(habit_id):
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT target_days FROM habits WHERE id = %s",
                (habit_id,)
            )
            return cursor.fetchone()[0]

    @staticmethod
    def mark_completed(habit_id):
        with get_db() as db:
            cursor = db.cursor()
            cursor.execute(
                "UPDATE habits SET completed = TRUE WHERE id = %s",
                (habit_id,)
            )
            db.commit()



HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Трекер привычек</title>
<style>
body {
    font-family: Arial;
    background: #f4f6f8;
    padding: 30px;
}
h1, h2 {
    color: #333;
}
.card {
    background: white;
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
}
button {
    padding: 5px 10px;
    border: none;
    border-radius: 5px;
    background: #4CAF50;
    color: white;
}
.delete {
    background: #e74c3c;
}
progress {
    width: 100%;
}
.tag {
    background: #ddd;
    padding: 3px 8px;
    border-radius: 8px;
    font-size: 12px;
}
</style>
</head>

<body>

<h1>🔥 Трекер привычек</h1>

<div class="card">
<h2>➕ Новая привычка</h2>
<form method="post" action="/add">
    Название: <input name="name" required>
    Тег: <input name="tag">
    Цель (дней): <input type="number" name="target" required>
    <button>Добавить</button>
</form>
</div>

<h2>📌 Активные привычки</h2>
{% for h in active %}
<div class="card">
<b>{{ h[1] }}</b> <span class="tag">{{ h[2] }}</span><br>
Streak: {{ streaks[h[0]] }} дней<br>

<progress value="{{ progress[h[0]][0] }}" max="{{ progress[h[0]][1] }}"></progress>
{{ progress[h[0]][0] }} / {{ progress[h[0]][1] }} дней

<br><br>
<a href="/log/{{ h[0] }}"><button>✔ Отметить сегодня</button></a>
<a href="/delete/{{ h[0] }}"><button class="delete">🗑 Удалить</button></a>
</div>
{% endfor %}

<h2>🏆 Завершённые привычки</h2>
{% for h in completed %}
<div class="card">
<b>{{ h[1] }}</b> — выполнено ✅
</div>
{% endfor %}

</body>
</html>
"""



@app.route("/")
def index():
    active = HabitService.get_active()
    completed = HabitService.get_completed()

    streaks = {h[0]: HabitService.calculate_streak(h[0]) for h in active}
    progress = {h[0]: HabitService.calculate_progress(h[0]) for h in active}

    return render_template_string(
        HTML,
        active=active,
        completed=completed,
        streaks=streaks,
        progress=progress
    )


@app.route("/add", methods=["POST"])
def add():
    habit = Habit(
        request.form["name"],
        request.form["tag"],
        int(request.form["target"])
    )
    habit.save()
    return redirect(url_for("index"))


@app.route("/log/<int:habit_id>")
def log(habit_id):
    HabitService.log_today(habit_id)
    return redirect(url_for("index"))


@app.route("/delete/<int:habit_id>")
def delete(habit_id):
    HabitService.delete(habit_id)
    return redirect(url_for("index"))



if __name__ == "__main__":
    init_db()
    app.run(debug=True)