import sqlite3

db_path = "data.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Получаем список всех таблиц, кроме системных
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
tables = [row[0] for row in cur.fetchall()]

print("🧹 Очистка таблиц:")

for table in tables:
    cur.execute(f"DELETE FROM {table};")
    cur.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}';")  # сбрасываем автонумерацию
    print(f"  - {table}")

conn.commit()
conn.close()

print("\n✅ Все таблицы очищены, структура сохранена!")
