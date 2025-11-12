-- Родители и ученики (для связи и контроля)
CREATE TABLE IF NOT EXISTS parent_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    parent_code TEXT UNIQUE NOT NULL,
    created_at TEXT,
    FOREIGN KEY (parent_id) REFERENCES users(id),
    FOREIGN KEY (student_id) REFERENCES users(id)
);


-- Таблица объявлений
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER NOT NULL,
    author_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    attachments TEXT,        -- JSON список файлов
    links TEXT,               -- JSON список ссылок
    created_at TEXT,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
);

-- Таблица заданий
CREATE TABLE IF NOT EXISTS assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER NOT NULL,
    teacher_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    due_date TEXT,
    attachments TEXT,         -- JSON список файлов
    links TEXT,                -- JSON список ссылок
    created_at TEXT,
    FOREIGN KEY (classroom_id) REFERENCES classrooms(id) ON DELETE CASCADE
);

-- users
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,
    parent_id INTEGER,
    parent_token TEXT,
    created_at TEXT
);

CREATE TABLE classrooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    teacher_id INTEGER,
    section TEXT,
    class_code TEXT,
    created_at TEXT,
    archived INTEGER DEFAULT 0
);

CREATE TABLE co_teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    user_id INTEGER
);

CREATE TABLE topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    title TEXT,
    position INTEGER,
    created_at TEXT
);

CREATE TABLE materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    title TEXT,
    file TEXT,
    created_at TEXT,
    author_id INTEGER
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    classroom_id INTEGER,
    joined_at TEXT
);

CREATE TABLE assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    title TEXT,
    description TEXT,
    attachment TEXT,
    due_date TEXT,
    created_at TEXT,
    topic_id INTEGER
);

CREATE TABLE submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER,
    student_id INTEGER,
    file TEXT,
    submitted_at TEXT,
    grade REAL,
    comment TEXT,
    graded_at TEXT,
    grade_category TEXT
);

CREATE TABLE rubrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER,
    title TEXT,
    criteria TEXT
);

CREATE TABLE grade_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    name TEXT
);

CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    message TEXT,
    created_at TEXT,
    read INTEGER DEFAULT 0
);

CREATE TABLE calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    title TEXT,
    event_at TEXT,
    created_at TEXT
);

-- Drive
CREATE TABLE drive_folders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    title TEXT,
    parent_id INTEGER,
    created_at TEXT
);
CREATE TABLE drive_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    title TEXT,
    file TEXT,
    folder_id INTEGER,
    uploaded_by INTEGER,
    created_at TEXT
);

-- Quizzes and auto-grader
CREATE TABLE quizzes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classroom_id INTEGER,
    title TEXT,
    created_at TEXT
);
CREATE TABLE questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER,
    text TEXT,
    choice1 TEXT,
    choice2 TEXT,
    choice3 TEXT,
    choice4 TEXT,
    correct_choice INTEGER
);
CREATE TABLE quiz_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER,
    question_id INTEGER,
    student_id INTEGER,
    answer TEXT,
    created_at TEXT
);
CREATE TABLE quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quiz_id INTEGER,
    student_id INTEGER,
    score REAL,
    created_at TEXT
);
