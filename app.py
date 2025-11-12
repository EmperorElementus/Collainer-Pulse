import os
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash, g, send_file, make_response, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid
import csv, io
import pandas as pd
import json
import random
import string


app = Flask(__name__)

import json

@app.template_filter('fromjson')
def fromjson_filter(s):
    try:
        return json.loads(s)
    except Exception:
        return []

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'data.db')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


app.secret_key = 'dev-secret-change-me'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 400 * 1024 * 1024

@app.route('/join_class', methods=['GET', 'POST'])
def join_class():
    user = current_user()
    if not user or user['role'] != 'student':
        flash('Только ученики могут присоединяться к классам.', 'danger')
        return redirect(url_for('dashboard'))

    db = get_db()

    if request.method == 'POST':
        class_code = request.form['class_code'].strip()
        classroom = query_db('SELECT * FROM classrooms WHERE class_code = ?', (class_code,), one=True)

        if not classroom:
            flash('Класс с таким кодом не найден.', 'danger')
            return redirect(url_for('join_class'))

        # Проверяем, не присоединён ли уже ученик
        exists = query_db('SELECT id FROM enrollments WHERE student_id = ? AND classroom_id = ?', 
                          (user['id'], classroom['id']), one=True)
        if exists:
            flash('Вы уже присоединились к этому классу.', 'info')
            return redirect(url_for('dashboard'))

        # Присоединяем ученика
        db.execute('INSERT INTO enrollments (student_id, classroom_id, joined_at) VALUES (?, ?, ?)',
                   (user['id'], classroom['id'], datetime.utcnow().isoformat()))
        db.commit()

        # Уведомление учителю
        db.execute('INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)',
                   (classroom['teacher_id'], f"{user['name']} присоединился к вашему классу {classroom['name']}", datetime.utcnow().isoformat()))
        db.commit()

        flash(f'Вы успешно присоединились к классу: {classroom["name"]}', 'success')
        return redirect(url_for('dashboard'))

    return render_template('join_class.html', user=user)

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# -------------------------------------------------
# Додати оголошення (аналог "посту" у класі)
# -------------------------------------------------
@app.route("/add_post/<int:classroom_id>", methods=["GET", "POST"])
def add_post(classroom_id):
    user = current_user()
    if not user:
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        title = request.form.get("title")
        content = request.form.get("content")
        links = request.form.getlist("links[]")

        attachments = []
        if "files" in request.files:
            for file in request.files.getlist("files"):
                if file and file.filename.strip():
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(save_path)
                    attachments.append(filename)

        db.execute(
            """
            INSERT INTO posts (classroom_id, author_id, title, content, attachments, links, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                classroom_id,
                user["id"],
                title,
                content,
                json.dumps(attachments),
                json.dumps(links),
                datetime.now().isoformat(),
            ),
        )
        db.commit()
        return redirect(f"/classroom/{classroom_id}")

    return render_template("add_post.html", classroom_id=classroom_id, user=user)

# -------------------------------------------------
# Додати завдання (аналог Assignment)
# -------------------------------------------------

@app.route("/add_assignment/<int:classroom_id>", methods=["GET", "POST"])
def add_assignment(classroom_id):
    user = current_user()
    if not user:
        return redirect("/login")

    db = get_db()

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        links = request.form.getlist("links[]")

        attachments = []
        if "files" in request.files:
            for file in request.files.getlist("files"):
                if file and file.filename.strip():
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                    file.save(save_path)
                    attachments.append(filename)

        db.execute(
            """
            INSERT INTO assignments (classroom_id, teacher_id, title, description, due_date, attachments, links, created_at, published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                classroom_id,
                user["id"],
                title,
                description,
                due_date,
                json.dumps(attachments),
                json.dumps(links),
                datetime.now().isoformat(),
                1,  # ✅ опубликовано
            ),
        )
        db.commit()
        return redirect(f"/classroom/{classroom_id}")

    return render_template("add_assignment.html", classroom_id=classroom_id, user=user)

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    try:
        with open('schema.sql', mode='r', encoding='utf-8') as f:
            db.executescript(f.read())
        db.commit()
        print("База данных создана заново.")
    except sqlite3.OperationalError as e:
        if "already exists" in str(e):
            print("База уже инициализирована — пропускаем создание таблиц.")
        else:
            raise


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur

def current_user():
    uid = session.get('user_id')
    if not uid:
        return None
    return query_db('SELECT * FROM users WHERE id = ?', (uid,), one=True)

def login_user(user):
    session['user_id'] = user['id']
    session['role'] = user['role']

def generate_class_code():
    return str(uuid.uuid4())[:6].upper()

@app.route('/')
def index():
    user = current_user()
    recent_classes = query_db('SELECT * FROM classrooms WHERE archived=0 ORDER BY created_at DESC LIMIT 6')
    return render_template('index.html', user=user, recent_classes=recent_classes)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role = request.form['role']
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        pwd = request.form['password']

        db = get_db()

        # Проверяем, не зарегистрирован ли уже email
        if query_db('SELECT id FROM users WHERE email = ?', (email,), one=True):
            flash('Email уже зарегистрирован', 'danger')
            return redirect(url_for('register'))

        pwd_hash = generate_password_hash(pwd, method='pbkdf2:sha256')

        # Создаём нового пользователя
        cur = db.execute(
            'INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, email, pwd_hash, role, datetime.utcnow().isoformat())
        )
        db.commit()

        user_id = cur.lastrowid

        # 🔹 Вот сюда вставляем код генерации токена для родителя
        if role == 'parent':
            token = str(uuid.uuid4())[:8]
            db.execute('UPDATE users SET parent_token = ? WHERE id = ?', (token, user_id))
            db.commit()
            flash(f'Ваш родительский код: {token}', 'info')

        flash('Регистрация прошла успешно. Теперь можно войти.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pwd = request.form['password']
        user = query_db('SELECT * FROM users WHERE email = ?', (email,), one=True)
        if user and check_password_hash(user['password_hash'], pwd):
            login_user(user)
            flash('Welcome, ' + user['name'], 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('index'))

@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/dashboard')
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    role = user['role']
    if role == 'teacher':
        classes = query_db('SELECT * FROM classrooms WHERE (teacher_id = ? OR id IN (SELECT classroom_id FROM co_teachers WHERE user_id=?)) AND archived=0', (user['id'], user['id']))
        notes = query_db('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 6', (user['id'],))
        return render_template('dashboard_teacher.html', user=user, classes=classes, notes=notes)
    elif role == 'student':
        classes = query_db('''
            SELECT c.* FROM classrooms c
            JOIN enrollments e ON e.classroom_id = c.id
            WHERE e.student_id = ? AND c.archived=0
        ''', (user['id'],))
        grades = query_db('SELECT grade FROM submissions WHERE student_id = ?', (user['id'],))
        avg = None
        if grades:
            vals = [g['grade'] for g in grades if g['grade'] is not None]
            if vals:
                avg = sum(vals)/len(vals)
        notes = query_db('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 6', (user['id'],))
        return render_template('dashboard_student.html', user=user, classes=classes, avg=avg, notes=notes)
    elif role == 'parent':
        children = query_db('SELECT u.* FROM users u WHERE u.parent_id = ?', (user['id'],))
        return render_template('dashboard_parent.html', user=user, children=children)
    elif role == 'admin':
        users = query_db('SELECT * FROM users ORDER BY role, name')
        return render_template('dashboard_admin.html', user=user, users=users)
    else:
        return "Unknown role", 400

# many routes reused from v2...
# For brevity, include routes for create_classroom, classroom view, enroll_code, create_topic, create_post, publish_scheduled,
# add_material, add_co_teacher, create_assignment, assignment, grade, admin functions, stats, archive/copy class, notifications, export grades, calendar, guardian_summary

@app.route("/create_classroom", methods=["GET", "POST"])
def create_classroom():
    user = current_user()
    if user["role"] != "teacher":
        return "Access denied", 403

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        code = generate_code()

        db = get_db()
        db.execute("""
            INSERT INTO classrooms (name, description, teacher_id, class_code, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (name, description, user["id"], code, datetime.now().isoformat()))
        db.commit()
        return redirect("/dashboard")

    return render_template("create_classroom.html", user=user)

@app.route("/join_classroom", methods=["GET", "POST"])
def join_classroom():
    user = get_current_user()
    if user["role"] != "student":
        return "Только ученики могут присоединяться", 403

    if request.method == "POST":
        code = request.form["code"].strip().upper()
        db = get_db()
        classroom = db.execute("SELECT id, teacher_id FROM classrooms WHERE class_code=?", (code,)).fetchone()
        if not classroom:
            return render_template("join_classroom.html", user=user, error="Неверный код класса")

        # Проверяем, не в классе ли уже ученик
        exists = db.execute("SELECT * FROM enrollments WHERE classroom_id=? AND student_id=?", 
                            (classroom["id"], user["id"])).fetchone()
        if exists:
            return render_template("join_classroom.html", user=user, error="Вы уже в этом классе")

        db.execute("INSERT INTO enrollments (student_id, classroom_id, joined_at) VALUES (?, ?, ?)",
                   (user["id"], classroom["id"], datetime.now().isoformat()))
        db.commit()

        # Уведомляем учителя
        db.execute("INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
                   (classroom["teacher_id"], f"{user['name']} приєднався до класу", datetime.now().isoformat()))
        db.commit()

        return redirect(f"/classroom/{classroom['id']}")

    return render_template("join_classroom.html", user=user)

@app.route('/link_parent', methods=['GET', 'POST'])
def link_parent():
    user = get_current_user()
    if user['role'] != 'student':
        flash('Только ученики могут привязывать родителя.', 'warning')
        return redirect(url_for('index'))

    db = get_db()
    if request.method == 'POST':
        parent_code = request.form['parent_code'].strip()
        parent = query_db('SELECT id FROM users WHERE parent_token = ? AND role = "parent"', (parent_code,), one=True)
        if not parent:
            flash('Родитель с таким кодом не найден.', 'danger')
            return redirect(url_for('link_parent'))

        db.execute('UPDATE users SET parent_id = ? WHERE id = ?', (parent['id'], user['id']))
        db.commit()
        flash('Родитель успешно привязан!', 'success')
        return redirect(url_for('index'))

    return render_template('link_parent.html')


@app.route('/classroom/<int:cid>')
def classroom(cid):
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    db = get_db()
    c_row = query_db('SELECT * FROM classrooms WHERE id = ?', (cid,), one=True)
    c = dict(c_row) if c_row else None

    if not c:
        return "Classroom not found", 404

    # Общие данные
    topics = query_db('SELECT * FROM topics WHERE classroom_id = ? ORDER BY position ASC', (cid,))
    posts = query_db('SELECT * FROM posts WHERE classroom_id = ? AND published=1 ORDER BY created_at DESC', (cid,))
    assignments = query_db('SELECT * FROM assignments WHERE classroom_id = ? ORDER BY created_at DESC', (cid,))
    materials = query_db('SELECT * FROM materials WHERE classroom_id = ? ORDER BY created_at DESC', (cid,))

    if user['role'] == 'teacher':
        students = query_db('SELECT u.* FROM users u JOIN enrollments e ON u.id = e.student_id WHERE e.classroom_id = ?', (cid,))
        co_teachers = query_db('SELECT u.* FROM users u JOIN co_teachers ct ON ct.user_id = u.id WHERE ct.classroom_id = ?', (cid,))
        folders = query_db('SELECT * FROM drive_folders WHERE classroom_id=? ORDER BY parent_id NULLS FIRST, id', (cid,))
        return render_template('classroom_teacher.html', user=user, classroom=c, topics=topics,
                               posts=posts, assignments=assignments, students=students,
                               co_teachers=co_teachers, materials=materials, folders=folders)

    elif user['role'] == 'student':
        return render_template('classroom_student.html', user=user, classroom=c, topics=topics,
                               posts=posts, assignments=assignments, materials=materials)

    elif user['role'] == 'parent':
        # Находим ученика, которого привязал родитель
        student = query_db('SELECT * FROM users WHERE parent_token = ?', (user['parent_token'],), one=True)
        if student:
            student_assignments = query_db('SELECT * FROM assignments WHERE classroom_id IN (SELECT classroom_id FROM enrollments WHERE student_id = ?)', (student['id'],))
        else:
            student_assignments = []
        return render_template('classroom_parent.html', user=user, student=student, assignments=student_assignments, posts=posts, materials=materials)

    else:
        flash('Нет доступа к этому классу', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/enroll_code', methods=['GET','POST'])
def enroll_code():
    user = current_user()
    if not user or user['role'] != 'student':
        return redirect(url_for('login'))
    if request.method == 'POST':
        code = request.form['code'].strip().upper()
        c = query_db('SELECT * FROM classrooms WHERE class_code = ? AND archived=0', (code,), one=True)
        if not c:
            flash('Invalid class code', 'danger')
            return redirect(url_for('enroll_code'))
        if query_db('SELECT * FROM enrollments WHERE student_id=? AND classroom_id=?', (user['id'], c['id']), one=True):
            flash('Already enrolled', 'info')
            return redirect(url_for('classroom', cid=c['id']))
        execute_db('INSERT INTO enrollments (student_id, classroom_id, joined_at) VALUES (?,?,?)',(user['id'], c['id'], datetime.utcnow().isoformat()))
        flash('Enrolled to ' + c['name'], 'success')
        return redirect(url_for('classroom', cid=c['id']))
    return render_template('enroll_code.html', user=user)

@app.route('/create_topic/<int:cid>', methods=['POST'])
def create_topic(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    title = request.form['title']
    pos = query_db('SELECT COALESCE(MAX(position),0)+1 as p FROM topics WHERE classroom_id=?', (cid,), one=True)['p']
    execute_db('INSERT INTO topics (classroom_id, title, position, created_at) VALUES (?,?,?,?)', (cid, title, pos, datetime.utcnow().isoformat()))
    flash('Topic created', 'success')
    return redirect(url_for('classroom', cid=cid))

@app.route('/create_post/<int:cid>', methods=['GET','POST'])
def create_post(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        publish = request.form.get('publish') == 'on'
        publish_at = request.form.get('publish_at') or None
        published = 1 if publish else 0
        execute_db('INSERT INTO posts (classroom_id, title, body, published, publish_at, created_at, author_id) VALUES (?,?,?,?,?,?,?)',
                   (cid, title, body, published, publish_at, datetime.utcnow().isoformat(), user['id']))
        flash('Post saved', 'success')
        return redirect(url_for('classroom', cid=cid))
    return render_template('create_post.html', user=user, cid=cid)

@app.route('/publish_scheduled')
def publish_scheduled():
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    now = datetime.utcnow().isoformat()
    rows = query_db('SELECT * FROM posts WHERE published=0 AND publish_at IS NOT NULL AND publish_at <= ?', (now,))
    for r in rows:
        execute_db('UPDATE posts SET published=1 WHERE id=?', (r['id'],))
        # notify enrolled students
        cid = r['classroom_id']
        students = query_db('SELECT student_id FROM enrollments WHERE classroom_id=?', (cid,))
        for s in students:
            execute_db('INSERT INTO notifications (user_id, message, created_at, read) VALUES (?,?,?,0)', (s['student_id'], f'New post: {r["title"]}', now))
    flash(f'Published {len(rows)} scheduled posts', 'success')
    return redirect(url_for('dashboard'))

@app.route('/add_material/<int:cid>', methods=['POST'])
def add_material(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    file = request.files.get('file')
    filename = None
    if file and file.filename:
        filename = secure_filename(str(uuid.uuid4()) + '_' + file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    title = request.form.get('title') or (file.filename if file else 'Material')
    execute_db('INSERT INTO materials (classroom_id, title, file, created_at, author_id) VALUES (?,?,?,?,?)',(cid, title, filename, datetime.utcnow().isoformat(), user['id']))
    flash('Material added', 'success')
    return redirect(url_for('classroom', cid=cid))

@app.route('/add_co_teacher/<int:cid>', methods=['POST'])
def add_co_teacher(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    email = request.form['email'].strip().lower()
    u = query_db('SELECT * FROM users WHERE email = ?', (email,), one=True)
    if not u:
        flash('User not found', 'danger')
        return redirect(url_for('classroom', cid=cid))
    if query_db('SELECT * FROM co_teachers WHERE classroom_id=? AND user_id=?',(cid,u['id']), one=True):
        flash('Already co-teacher', 'info')
        return redirect(url_for('classroom', cid=cid))
    execute_db('INSERT INTO co_teachers (classroom_id, user_id) VALUES (?,?)',(cid,u['id']))
    flash('Co-teacher added', 'success')
    return redirect(url_for('classroom', cid=cid))

@app.route('/create_assignment/<int:cid>', methods=['GET','POST'])
def create_assignment(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        desc = request.form['description']
        due = request.form.get('due')
        topic_id = request.form.get('topic_id')
        attach = request.files.get('attachment')
        filename = None
        if attach and attach.filename:
            filename = secure_filename(str(uuid.uuid4()) + '_' + attach.filename)
            attach.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        execute_db('INSERT INTO assignments (classroom_id, title, description, attachment, due_date, created_at, topic_id) VALUES (?,?,?,?,?,?,?)',
                   (cid, title, desc, filename, due, datetime.utcnow().isoformat(), topic_id))
        flash('Assignment created', 'success')
        return redirect(url_for('classroom', cid=cid))
    topics = query_db('SELECT * FROM topics WHERE classroom_id = ? ORDER BY position ASC', (cid,))
    return render_template('create_assignment.html', user=user, cid=cid, topics=topics)

@app.route('/assignment/<int:aid>', methods=['GET', 'POST'])
def assignment(aid):
    user = current_user()
    if not user:
        return redirect(url_for('login'))

    # Получаем задание
    a = query_db('''
        SELECT a.*, c.name as classroom_name
        FROM assignments a
        JOIN classrooms c ON a.classroom_id = c.id
        WHERE a.id = ?
    ''', (aid,), one=True)

    if not a:
        return "Assignment not found", 404

    # Если студент отправляет ответ
    if request.method == 'POST' and user['role'] == 'student':
        text_answer = request.form.get('text_answer', '').strip()
        uploaded_files = request.files.getlist('submission')

        filenames = []
        for file in uploaded_files:
            if file and file.filename.strip():
                filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                filenames.append(filename)

        execute_db('''
            INSERT INTO submissions (assignment_id, student_id, submitted_at, text_answer, attachments)
            VALUES (?, ?, ?, ?, ?)
        ''', (aid, user['id'], datetime.utcnow().isoformat(), text_answer, json.dumps(filenames)))

        flash('✅ Завдання надіслано успішно!', 'success')
        return redirect(url_for('assignment', aid=aid))

    # Если преподаватель сохраняет оценку / комментарий
    elif request.method == 'POST' and user['role'] == 'teacher':
        sub_id = request.form.get('submission_id')
        grade = request.form.get('grade', '').strip()
        comment = request.form.get('teacher_comment', '').strip()

        if sub_id:
            execute_db('''
                UPDATE submissions
                SET grade = ?, teacher_comment = ?
                WHERE id = ?
            ''', (grade, comment, sub_id))
            flash('💾 Оцінка збережена!', 'success')

        return redirect(url_for('assignment', aid=aid))

    # Получаем все отправленные работы
    submissions = query_db('''
        SELECT s.*, u.name as student_name
        FROM submissions s
        JOIN users u ON u.id = s.student_id
        WHERE s.assignment_id = ?
        ORDER BY s.submitted_at DESC
    ''', (aid,))

    # Проверяем, отправил ли студент свою работу
    my_submission = None
    if user['role'] == 'student':
        my_submission = query_db('''
            SELECT * FROM submissions
            WHERE assignment_id = ? AND student_id = ?
        ''', (aid, user['id']), one=True)

    return render_template(
        'assignment.html',
        user=user,
        assignment=a,
        submissions=submissions,
        my_submission=my_submission
    )


@app.route('/grade/<int:submission_id>', methods=['POST'])
def grade(submission_id):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    grade = request.form.get('grade')
    comment = request.form.get('comment')
    category = request.form.get('category')
    db = get_db()
    db.execute('UPDATE submissions SET grade=?, comment=?, graded_at=?, grade_category=? WHERE id=?', (grade, comment, datetime.utcnow().isoformat(), category, submission_id))
    db.commit()
    flash('Graded', 'success')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/admin/users')
def admin_users():
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    users = query_db('SELECT * FROM users ORDER BY created_at DESC')
    return render_template('admin_users.html', user=user, users=users)

@app.route('/admin/link_parent', methods=['GET','POST'])
def admin_link_parent():
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        parent_id = request.form['parent_id']
        student_email = request.form['student_email'].strip().lower()
        student = query_db('SELECT * FROM users WHERE email = ?', (student_email,), one=True)
        if not student:
            flash('Student not found', 'danger')
            return redirect(url_for('admin_link_parent'))
        execute_db('UPDATE users SET parent_id = ? WHERE id = ?', (parent_id, student['id']))
        flash('Linked parent to student', 'success')
    parents = query_db('SELECT * FROM users WHERE role = "parent"')
    return render_template('admin_link_parent.html', user=user, parents=parents)

@app.route('/parent/link', methods=['GET','POST'])
def parent_link():
    user = current_user()
    if not user or user['role'] != 'parent':
        return redirect(url_for('login'))
    if request.method == 'POST':
        token = request.form['token'].strip()
        student = query_db('SELECT * FROM users WHERE parent_token = ?', (token,), one=True)
        if not student:
            flash('Invalid token', 'danger')
            return redirect(url_for('parent_link'))
        execute_db('UPDATE users SET parent_id = ? WHERE id = ?', (user['id'], student['id']))
        flash('Linked to student ' + student['name'], 'success')
        return redirect(url_for('dashboard'))
    return render_template('parent_link.html', user=user)

@app.route('/stats')
def stats():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    totals = {
        'users': query_db('SELECT COUNT(*) as c FROM users', (), one=True)['c'],
        'classes': query_db('SELECT COUNT(*) as c FROM classrooms', (), one=True)['c'],
        'assignments': query_db('SELECT COUNT(*) as c FROM assignments', (), one=True)['c'],
        'submissions': query_db('SELECT COUNT(*) as c FROM submissions', (), one=True)['c']
    }
    class_stats = query_db('''
        SELECT c.id, c.name,
            (SELECT COUNT(*) FROM enrollments e WHERE e.classroom_id = c.id) as students,
            (SELECT COUNT(*) FROM assignments a WHERE a.classroom_id = c.id) as assignments
        FROM classrooms c
        ORDER BY c.name
    ''')
    return render_template('stats.html', user=user, totals=totals, class_stats=class_stats)

@app.route('/stats_data/<int:cid>')
def stats_data(cid):
    # returns JSON metrics for charting
    # naive: per-assignment average grade
    rows = query_db('''
        SELECT a.title, AVG(s.grade) as avg_grade
        FROM assignments a
        LEFT JOIN submissions s ON s.assignment_id = a.id
        WHERE a.classroom_id = ?
        GROUP BY a.id
    ''', (cid,))
    data = {'labels':[r['title'] for r in rows], 'data':[r['avg_grade'] if r['avg_grade'] is not None else 0 for r in rows]}
    return jsonify(data)

@app.route('/archive_class/<int:cid>', methods=['POST'])
def archive_class(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    execute_db('UPDATE classrooms SET archived=1 WHERE id=?', (cid,))
    flash('Class archived', 'success')
    return redirect(url_for('dashboard'))

@app.route('/copy_class/<int:cid>', methods=['POST'])
def copy_class(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    c = query_db('SELECT * FROM classrooms WHERE id=?', (cid,), one=True)
    if not c:
        flash('Class not found', 'danger')
        return redirect(url_for('dashboard'))
    new_code = generate_class_code()
    cur = execute_db('INSERT INTO classrooms (name, description, teacher_id, section, class_code, created_at, archived) VALUES (?,?,?,?,?,?,0)',
                     (c['name'] + ' (copy)', c['description'], user['id'], c['section'], new_code, datetime.utcnow().isoformat()))
    new_id = cur.lastrowid
    topics = query_db('SELECT * FROM topics WHERE classroom_id=?', (cid,))
    for t in topics:
        execute_db('INSERT INTO topics (classroom_id, title, position, created_at) VALUES (?,?,?,?)',(new_id, t['title'], t['position'], datetime.utcnow().isoformat()))
    flash('Class copied. New code: ' + new_code, 'success')
    return redirect(url_for('classroom', cid=new_id))

@app.route('/notifications')
def notifications():
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    notes = query_db('SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC', (user['id'],))
    return render_template('notifications.html', user=user, notes=notes)

@app.route('/notify_all', methods=['POST'])
def notify_all():
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    message = request.form.get('message') or 'Important update'
    users = query_db('SELECT id FROM users')
    for u in users:
        execute_db('INSERT INTO notifications (user_id, message, created_at, read) VALUES (?,?,?,0)', (u['id'], message, datetime.utcnow().isoformat()))
    flash('Notified all users', 'success')
    return redirect(url_for('admin_users'))

@app.route('/export_grades/<int:cid>')
def export_grades(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    rows = query_db('''
        SELECT u.name as student, u.email as email, s.grade, s.comment, a.title as assignment
        FROM submissions s
        JOIN users u ON u.id = s.student_id
        JOIN assignments a ON a.id = s.assignment_id
        WHERE a.classroom_id = ?
        ORDER BY u.name
    ''', (cid,))
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['Student','Email','Assignment','Grade','Comment'])
    for r in rows:
        cw.writerow([r['student'], r['email'], r['assignment'], r['grade'] if r['grade'] is not None else '', r['comment'] or ''])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename=grades_class_{cid}.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/calendar/<int:cid>', methods=['GET','POST'])
def calendar(cid):
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        when = request.form['when']
        execute_db('INSERT INTO calendar_events (classroom_id, title, event_at, created_at) VALUES (?,?,?,?)', (cid, title, when, datetime.utcnow().isoformat()))
        flash('Event added', 'success')
        return redirect(url_for('calendar', cid=cid))
    events = query_db('SELECT * FROM calendar_events WHERE classroom_id = ? ORDER BY event_at', (cid,))
    return render_template('calendar.html', user=user, events=events, cid=cid)

@app.route('/guardian_summary/<int:student_id>')
def guardian_summary(student_id):
    user = current_user()
    if not user or user['role'] not in ('parent','admin'):
        return redirect(url_for('login'))
    student = query_db('SELECT * FROM users WHERE id = ?', (student_id,), one=True)
    if not student:
        return "Student not found", 404
    grades = query_db('SELECT a.title as assignment, s.grade, s.graded_at FROM submissions s JOIN assignments a ON a.id = s.assignment_id WHERE s.student_id = ?', (student_id,))
    recent = query_db('SELECT p.title, p.body, p.created_at FROM posts p JOIN classrooms c ON p.classroom_id = c.id WHERE p.published=1 ORDER BY p.created_at DESC LIMIT 10')
    return render_template('guardian_summary.html', user=user, student=student, grades=grades, recent=recent)

# Drive: folders & files in DB
@app.route('/drive/<int:cid>', methods=['GET','POST'])
def drive(cid):
    user = current_user()
    if not user:
        return redirect(url_for('login'))
    if request.method == 'POST' and user['role'] in ('teacher','admin'):
        title = request.form.get('title') or 'New Folder'
        parent = request.form.get('parent') or None
        execute_db('INSERT INTO drive_folders (classroom_id, title, parent_id, created_at) VALUES (?,?,?,?)', (cid, title, parent, datetime.utcnow().isoformat()))
        flash('Folder created', 'success')
        return redirect(url_for('drive', cid=cid))
    folders = query_db('SELECT * FROM drive_folders WHERE classroom_id=? ORDER BY id', (cid,))
    files = query_db('SELECT * FROM drive_files WHERE classroom_id=? ORDER BY created_at DESC', (cid,))
    return render_template('drive.html', user=user, cid=cid, folders=folders, files=files)

@app.route('/drive_upload/<int:cid>', methods=['POST'])
def drive_upload(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin','student'):
        return redirect(url_for('login'))
    f = request.files.get('file')
    if not f or not f.filename:
        flash('No file', 'danger')
        return redirect(url_for('drive', cid=cid))
    filename = secure_filename(str(uuid.uuid4()) + '_' + f.filename)
    f.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    folder = request.form.get('folder') or None
    execute_db('INSERT INTO drive_files (classroom_id, title, file, folder_id, uploaded_by, created_at) VALUES (?,?,?,?,?,?)', (cid, f.filename, filename, folder, user['id'], datetime.utcnow().isoformat()))
    flash('Uploaded', 'success')
    return redirect(url_for('drive', cid=cid))

# Import/Export CSV for users and classes
@app.route('/admin/export_users')
def export_users():
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    rows = query_db('SELECT id,name,email,role,created_at FROM users')
    si = io.StringIO()
    cw = csv.writer(si)
    cw.writerow(['id','name','email','role','created_at'])
    for r in rows:
        cw.writerow([r['id'], r['name'], r['email'], r['role'], r['created_at']])
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=users.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/admin/import_users', methods=['GET','POST'])
def import_users():
    user = current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        f = request.files.get('file')
        if not f:
            flash('No file', 'danger')
            return redirect(url_for('admin_users'))
        df = pd.read_csv(f)
        for _, row in df.iterrows():
            email = str(row.get('email','')).strip().lower()
            name = row.get('name','Imported')
            role = row.get('role','student')
            pwd = row.get('password') if 'password' in row else 'changeme'
            if email:
                if query_db('SELECT * FROM users WHERE email=?', (email,), one=True):
                    continue
                execute_db('INSERT INTO users (name,email,password_hash,role,created_at) VALUES (?,?,?,?,?)', (name,email,generate_password_hash(str(pwd)),role,datetime.utcnow().isoformat()))
        flash('Import complete', 'success')
        return redirect(url_for('admin_users'))
    return render_template('import_users.html', user=user)

# Quizzes: MCQ auto-grader
@app.route('/create_quiz/<int:cid>', methods=['GET','POST'])
def create_quiz(cid):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title']
        cur = execute_db('INSERT INTO quizzes (classroom_id, title, created_at) VALUES (?,?,?)', (cid, title, datetime.utcnow().isoformat()))
        qid = cur.lastrowid
        flash('Quiz created. Now add questions.', 'success')
        return redirect(url_for('edit_quiz', quiz_id=qid))
    return render_template('create_quiz.html', user=user, cid=cid)

@app.route('/edit_quiz/<int:quiz_id>', methods=['GET','POST'])
def edit_quiz(quiz_id):
    user = current_user()
    if not user or user['role'] not in ('teacher','admin'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        text = request.form['text']
        choices = [request.form.get(f'choice{i}') for i in range(1,5)]
        correct = request.form.get('correct')
        execute_db('INSERT INTO questions (quiz_id, text, choice1, choice2, choice3, choice4, correct_choice) VALUES (?,?,?,?,?,?,?)', (quiz_id, text, choices[0], choices[1], choices[2], choices[3], correct))
        flash('Question added', 'success')
        return redirect(url_for('edit_quiz', quiz_id=quiz_id))
    quiz = query_db('SELECT * FROM quizzes WHERE id=?', (quiz_id,), one=True)
    questions = query_db('SELECT * FROM questions WHERE quiz_id=?', (quiz_id,))
    return render_template('edit_quiz.html', user=user, quiz=quiz, questions=questions)

@app.route('/take_quiz/<int:quiz_id>', methods=['GET','POST'])
def take_quiz(quiz_id):
    user = current_user()
    if not user or user['role'] != 'student':
        return redirect(url_for('login'))
    if request.method == 'POST':
        answers = {}
        questions = query_db('SELECT * FROM questions WHERE quiz_id=?', (quiz_id,))
        correct_count = 0
        total = 0
        for q in questions:
            total += 1
            ans = request.form.get(f'q{q["id"]}')
            execute_db('INSERT INTO quiz_submissions (quiz_id, question_id, student_id, answer, created_at) VALUES (?,?,?,?,?)', (quiz_id, q['id'], user['id'], ans, datetime.utcnow().isoformat()))
            if ans == str(q['correct_choice']):
                correct_count += 1
        score = (correct_count/total)*100 if total>0 else 0
        execute_db('INSERT INTO quiz_results (quiz_id, student_id, score, created_at) VALUES (?,?,?,?)', (quiz_id, user['id'], score, datetime.utcnow().isoformat()))
        flash(f'Quiz submitted. Score: {score:.1f}%', 'success')
        return redirect(url_for('dashboard'))
    quiz = query_db('SELECT * FROM quizzes WHERE id=?', (quiz_id,), one=True)
    questions = query_db('SELECT * FROM questions WHERE quiz_id=?', (quiz_id,))
    return render_template('take_quiz.html', user=user, quiz=quiz, questions=questions)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)