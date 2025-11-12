import sqlite3
from werkzeug.security import generate_password_hash

# подключаем базу
conn = sqlite3.connect("data.db")
cur = conn.cursor()

# новые безопасные хэши pbkdf2:sha256
users = [
    ("admin@local",   "adminpass"),
    ("teacher@local", "teachpass"),
    ("student@local", "studpass"),
    ("parent@local",  "parentpass"),
]

for email, plain in users:
    hash_val = generate_password_hash(plain, method="pbkdf2:sha256")
    cur.execute("UPDATE users SET password_hash=? WHERE email=?", (hash_val, email))

conn.commit()
conn.close()
print("✅ Пароли успешно пересозданы (pbkdf2:sha256).")
