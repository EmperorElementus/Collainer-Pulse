# Simple scheduler to publish scheduled posts and notify users.
import sqlite3, os
from datetime import datetime
DB = os.path.join(os.path.dirname(__file__), 'data.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()
now = datetime.utcnow().isoformat()
cur.execute("SELECT id FROM posts WHERE published=0 AND publish_at IS NOT NULL AND publish_at <= ?", (now,))
rows = cur.fetchall()
for (pid,) in rows:
    cur.execute("UPDATE posts SET published=1 WHERE id=?", (pid,))
# create notifications for class members
cur.execute("SELECT p.id, p.classroom_id, p.title FROM posts p WHERE p.publish_at <= ? AND p.publish_at IS NOT NULL", (now,))
posts = cur.fetchall()
for pid, cid, title in posts:
    # notify enrolled students
    cur.execute("SELECT student_id FROM enrollments WHERE classroom_id=?", (cid,))
    students = cur.fetchall()
    for (sid,) in students:
        cur.execute("INSERT INTO notifications (user_id, message, created_at, read) VALUES (?,?,?,0)", (sid, f'New post published: {title}', now))
conn.commit()
conn.close()
print(f'Published {len(rows)} posts and notified students.')
