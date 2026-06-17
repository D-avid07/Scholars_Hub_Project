# database.py
import streamlit as st
import pandas as pd
import hashlib

def get_db_connection():
    """
    Establishes a pooled SQL connection utilizing Streamlit's connection engine.
    """
    try:
        # Automatically consumes credentials from .streamlit/secrets.toml
        return st.connection("mysql", type="sql")
    except Exception as e:
        st.sidebar.error(f"⚠️ XAMPP Routing Offline: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if conn is None: return
    try:
        with conn.session as session:
            from sqlalchemy import text
            session.execute(text('''CREATE TABLE IF NOT EXISTS teachers (
                reg_number VARCHAR(50) PRIMARY KEY,
                name VARCHAR(100),
                password_hash VARCHAR(255)
            )'''))
            session.execute(text('''CREATE TABLE IF NOT EXISTS teacher_settings (
                reg_number VARCHAR(50) PRIMARY KEY,
                threshold INT DEFAULT 50
            )'''))
            session.execute(text('''CREATE TABLE IF NOT EXISTS course_materials (
                id INT AUTO_INCREMENT PRIMARY KEY,
                subject VARCHAR(100),
                filename VARCHAR(255),
                uploaded_by VARCHAR(50),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )'''))
            session.commit()
    except Exception as e:
        st.error(f"DB Init Error: {e}")


def hash_password(password):
    """Simple SHA-256 hashing for local academic prototyping account security."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(reg_number, name, password):
    conn = get_db_connection()
    if conn is None: 
        return False
    try:
        hashed = hash_password(password)
        
        # Use Streamlit's connection session manager to execute non-SELECT queries safely
        with conn.session as session:
            from sqlalchemy import text
            statement = text(
                "INSERT INTO students (reg_number, student_name, password_hash) "
                "VALUES (:reg, :name, :pass);"
            )
            session.execute(statement, {"reg": reg_number, "name": name, "pass": hashed})
            session.commit()  # Explicitly commit changes to XAMPP MySQL
        return True
    except Exception as e:
        st.error(f"Registration failed: {e}")
        return False

def verify_user(reg_number, password):
    conn = get_db_connection()
    if conn is None: 
        return None
    try:
        hashed = hash_password(password)
        
        # Explicitly query via named params keyword mapping
        df = conn.query(
            "SELECT reg_number, student_name, password_hash FROM students WHERE reg_number = :reg;",
            params={"reg": reg_number}
        )
        
        if not df.empty:
            db_password = str(df.iloc[0]['password_hash'])
            # DUAL-VERIFICATION FALLBACK: Checks secure hash OR plain text to accommodate legacy rows
            if db_password == hashed or db_password == password:
                return {"reg_number": df.iloc[0]['reg_number'], "student_name": df.iloc[0]['student_name']}
            
    except Exception as e:
        st.error(f"Login database check error: {e}")
    return None

def fetch_student_enrollments(reg_number):
    conn = get_db_connection()
    if conn is None: 
        return []
    try:
        # FIX: Converted positional argument to an explicit named keyword param format
        df = conn.query(
            "SELECT subject_name, total_reading_time FROM enrollments WHERE reg_number = :reg;", 
            params={"reg": reg_number}
        )
        return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Error gathering registration tracking logs: {e}")
        return []

# database.py - Corrected SQL Schema Alignment

def fetch_courses_by_subject(subject_name, reg_number=None):
    """Pulls courses linked to a specific subject that match the student's enrollment profile."""
    conn = get_db_connection()
    if conn is None: 
        return []
    try:
        if reg_number is not None:
            query_str = """
                SELECT c.* FROM courses c
                JOIN enrollments e ON c.subject = e.subject_name
                WHERE e.subject_name = :sub_name AND e.reg_number = :reg;
            """
            df = conn.query(query_str, params={"sub_name": subject_name, "reg": reg_number})
        else:
            query_str = """
                SELECT * FROM courses WHERE subject = :sub_name;
            """
            df = conn.query(query_str, params={"sub_name": subject_name})
            
        records = df.to_dict(orient="records")
        if not records:
            # Fallback mock data if the DB is empty so the homepage doesn't crash
            records = [
                {"title": f"Introductory {subject_name}", "rating": "4.5", "img_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=400"},
                {"title": f"Advanced {subject_name}", "rating": "4.8", "img_url": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=400"}
            ]
        return records
    except Exception as e:
        st.error(f"Error filtering courses for token alignment: {e}")
        return [
            {"title": f"Introductory {subject_name}", "rating": "4.5"},
            {"title": f"Advanced {subject_name}", "rating": "4.8"}
        ]

def enroll_in_subject(reg_number, subject_name):
    """Creates a new student record association row inside the enrollment matrix."""
    conn = get_db_connection()
    if conn is None: 
        return False
    try:
        with conn.session as session:
            from sqlalchemy import text
            statement = text(
                "INSERT IGNORE INTO enrollments (reg_number, subject_name, total_reading_time) "
                "VALUES (:reg, :sub, 0);"
            )
            session.execute(statement, {"reg": reg_number, "sub": subject_name})
            session.commit()
        return True
    except Exception as e:
        st.error(f"Enrollment tracking link broken: {e}")
        return False

def update_reading_time(reg_number, subject_name, additional_minutes=1):
    """Increments tracked reading velocity logs directly into the server database."""
    conn = get_db_connection()
    if conn is None: 
        return False
    try:
        with conn.session as session:
            from sqlalchemy import text
            statement = text(
                "UPDATE enrollments SET total_reading_time = total_reading_time + :mins "
                "WHERE reg_number = :reg AND subject_name = :sub;"
            )
            session.execute(statement, {"mins": additional_minutes, "reg": reg_number, "sub": subject_name})
            session.commit()
        return True
    except Exception:
        return False

def fetch_student_performance_summary(reg_number):
    """Pulls aggregated diagnostic metrics for the Agentic analyzer engine."""
    conn = get_db_connection()
    if conn is None: 
        return {"avg_score": 0, "total_time": 0, "weakness": "None Detected"}
    try:
        df_time = conn.query("SELECT SUM(total_reading_time) as total_time FROM enrollments WHERE reg_number = :reg;", params={"reg": reg_number})
        df_quiz = conn.query("SELECT AVG(score) as avg_score FROM quiz_results WHERE reg_number = :reg;", params={"reg": reg_number})
        
        total_time = int(df_time.iloc[0]['total_time']) if not df_time.empty and df_time.iloc[0]['total_time'] is not None else 0
        avg_score = int(df_quiz.iloc[0]['avg_score']) if not df_quiz.empty and df_quiz.iloc[0]['avg_score'] is not None else 0
        
        return {"avg_score": avg_score, "total_time": total_time}
    except Exception:
        return {"avg_score": 0, "total_time": 0}

def register_teacher(reg_number, name, password):
    conn = get_db_connection()
    if conn is None: return False
    try:
        hashed = hash_password(password)
        with conn.session as session:
            from sqlalchemy import text
            statement = text(
                "INSERT INTO teachers (reg_number, name, password_hash) "
                "VALUES (:reg, :name, :pass);"
            )
            session.execute(statement, {"reg": reg_number, "name": name, "pass": hashed})
            session.execute(text("INSERT INTO teacher_settings (reg_number, threshold) VALUES (:reg, 50);"), {"reg": reg_number})
            session.commit()
        return True
    except Exception as e:
        st.error(f"Teacher registration failed: {e}")
        return False

def verify_teacher(reg_number, password):
    conn = get_db_connection()
    if conn is None: return None
    try:
        hashed = hash_password(password)
        df = conn.query(
            "SELECT reg_number, name, password_hash FROM teachers WHERE reg_number = :reg;",
            params={"reg": reg_number}
        )
        if not df.empty:
            db_password = str(df.iloc[0]['password_hash'])
            if db_password == hashed or db_password == password:
                return {"reg_number": df.iloc[0]['reg_number'], "name": df.iloc[0]['name']}
    except Exception as e:
        st.error(f"Teacher login error: {e}")
    return None

def set_performance_threshold(reg_number, threshold):
    conn = get_db_connection()
    if conn is None: return False
    try:
        with conn.session as session:
            from sqlalchemy import text
            statement = text(
                "INSERT INTO teacher_settings (reg_number, threshold) VALUES (:reg, :thresh) "
                "ON DUPLICATE KEY UPDATE threshold = :thresh;"
            )
            session.execute(statement, {"reg": reg_number, "thresh": threshold})
            session.commit()
        return True
    except Exception:
        return False

def get_performance_threshold(reg_number):
    conn = get_db_connection()
    if conn is None: return 50
    try:
        df = conn.query("SELECT threshold FROM teacher_settings WHERE reg_number = :reg;", params={"reg": reg_number})
        if not df.empty:
            return int(df.iloc[0]['threshold'])
    except Exception:
        pass
    return 50

def save_course_material_record(subject, filename, uploaded_by):
    conn = get_db_connection()
    if conn is None: return False
    try:
        with conn.session as session:
            from sqlalchemy import text
            statement = text(
                "INSERT INTO course_materials (subject, filename, uploaded_by) "
                "VALUES (:sub, :fname, :up_by);"
            )
            session.execute(statement, {"sub": subject, "fname": filename, "up_by": uploaded_by})
            session.commit()
        return True
    except Exception:
        return False

def get_all_students_performance():
    conn = get_db_connection()
    if conn is None: return pd.DataFrame()
    try:
        query = """
        SELECT s.reg_number, s.student_name, 
               COALESCE(SUM(e.total_reading_time), 0) as total_time,
               (SELECT AVG(score) FROM quiz_results q WHERE q.reg_number = s.reg_number) as avg_score
        FROM students s
        LEFT JOIN enrollments e ON s.reg_number = e.reg_number
        GROUP BY s.reg_number, s.student_name
        """
        df = conn.query(query)
        df['avg_score'] = df['avg_score'].fillna(0).astype(int)
        df['total_time'] = df['total_time'].fillna(0).astype(int)
        return df
    except Exception as e:
        st.error(f"Error fetching students performance: {e}")
        return pd.DataFrame()


def get_course_materials(active_subject):
    """
    Fetches uploaded materials from the database for a specific subject
    using Streamlit's connection engine framework.
    """
    conn = get_db_connection()
    if conn is None: 
        return []
    try:
        # Use SQL LOWER logic to match cross-case inputs safely
        query_str = "SELECT id, subject, filename, uploaded_by, uploaded_at FROM course_materials WHERE LOWER(subject) = LOWER(:sub);"
        df = conn.query(query_str, params={"sub": active_subject})
        
        if df is not None and not df.empty:
            return df.to_dict(orient="records")
    except Exception as e:
        st.error(f"Error reading course materials tracking: {e}")
    return []