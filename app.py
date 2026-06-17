# app.py
import streamlit as st
import streamlit.components.v1 as components
from database import fetch_courses_by_subject, verify_user, register_user, fetch_student_enrollments, init_db, register_teacher, verify_teacher, set_performance_threshold, get_performance_threshold, save_course_material_record, get_all_students_performance

init_db()

st.set_page_config(page_title="Scholar's Hub", layout="wide", page_icon="🎓")

# --- INITIALIZE CORE APP STATE CONFIGS ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "user_role" not in st.session_state:
    st.session_state.user_role = "student"
if "current_subject" not in st.session_state:
    st.session_state.current_subject = "Literature"
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Browse" # Modes: Browse, Auth, Dashboard, TeacherDashboard

# --- BRANDING STYLES ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

/* Main CSS overrides */
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Inter', sans-serif !important;
}

h1, h2, h3, h4, h5, h6 {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 700 !important;
}

/* Card wrappers matching the screenshots */
.card-wrapper {
    background: #FFFFFF !important;
    border: 1px solid #E2E8F0 !important;
    border-radius: 16px !important;
    padding: 24px !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.02) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    margin-bottom: 15px !important;
    color: #C0D2F0 !important;
}

.card-wrapper:hover {
    transform: translateY(-4px) !important;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.08), 0 10px 10px -5px rgba(0, 0, 0, 0.03) !important;
}

/* Premium royal purple button styles */
div.stButton > button {
    background-color: #4F46E5 !important;
    color: white !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    border: none !important;
    box-shadow: 0 4px 10px rgba(79, 70, 229, 0.15) !important;
    transition: all 0.2s ease-in-out !important;
}

div.stButton > button:hover {
    background-color: #4338CA !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 15px rgba(79, 70, 229, 0.25) !important;
}

/* Tab indicator style */
.stTabs [data-baseweb="tab"] {
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    color: #4B5563 !important;
}

.stTabs [aria-selected="true"] {
    color: #4F46E5 !important;
}
</style>
""", unsafe_allow_html=True)

# --- HELPER COMPONENT FOR READING FILES ---
# --- HELPER COMPONENT FOR READING FILES ---
def display_course_materials_section(subject_name):
    """Queries and displays course material resources uploaded by teachers for a specific subject."""
    import os
    from database import get_course_materials
    from langchain_community.document_loaders import PyPDFLoader
    
    st.markdown("### 📂 Course Reference Materials")

    # Fetch dynamic data records matching this tab profile
    materials = get_course_materials(subject_name)

    if materials:
        for mat in materials:
            # Layout divided into file info, Download button, and Inline Reading portal trigger
            col_file, col_dl, col_read = st.columns([2, 1, 1])
            with col_file:
                st.markdown(f"📄 **{mat['filename']}**")
                st.caption(f"Uploaded status synchronized down on: {mat['uploaded_at']}")
            
            local_file_path = os.path.join("data", mat['filename'])
            file_exists = os.path.exists(local_file_path)

            with col_dl:
                # Verify if the physical file exists on the local computer storage disk
                if file_exists:
                    with open(local_file_path, "rb") as file_bytes:
                        st.download_button(
                            label="📥 Download",
                            data=file_bytes,
                            file_name=mat['filename'],
                            mime="application/pdf",
                            key=f"dl_{subject_name}_{mat['filename']}",
                            use_container_width=True
                        )
                else:
                    # Fallback if database metadata points to a file missing from local project folder
                    st.error("❌ Physical file missing.")
            
            with col_read:
                if file_exists:
                    # Interactive button to open the content in the workspace itself
                    read_key = f"active_read_{subject_name}_{mat['filename']}"
                    if st.session_state.get(read_key, False):
                        if st.button("❌ Close Viewer", key=f"btn_close_{subject_name}_{mat['filename']}", use_container_width=True):
                            st.session_state[read_key] = False
                            st.rerun()
                    else:
                        if st.button("📖 Read Inline", key=f"btn_read_{subject_name}_{mat['filename']}", use_container_width=True):
                            st.session_state[read_key] = True
                            st.rerun()
                else:
                    st.write("")

            # Inline PDF Paginated Document Viewer
            if file_exists and st.session_state.get(f"active_read_{subject_name}_{mat['filename']}", False):
                with st.container():
                    st.markdown(f"""
                    <div style="background-color: #0F172A; border: 1px solid #1E293B; padding: 15px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px;">
                        <h5 style="margin-top: 0; color: #38BDF8;">📖 Document Reading Desk: {mat['filename']}</h5>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.spinner("Extracting content segments for browser view..."):
                        try:
                            # Load PDF via the standard LangChain community document loaders
                            loader = PyPDFLoader(local_file_path)
                            pages = loader.load()
                            total_pages = len(pages)
                            
                            if total_pages == 0:
                                st.warning("This document has no readable text layout pages.")
                            else:
                                page_index_key = f"page_idx_{subject_name}_{mat['filename']}"
                                if page_index_key not in st.session_state:
                                    st.session_state[page_index_key] = 1
                                    
                                current_page = st.session_state[page_index_key]
                                
                                # Paginated controls layout
                                nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
                                with nav_col1:
                                    if st.button("⬅️ Previous", key=f"prev_pg_{subject_name}_{mat['filename']}") and current_page > 1:
                                        st.session_state[page_index_key] -= 1
                                        st.rerun()
                                with nav_col2:
                                    st.markdown(f"<div style='text-align: center; font-size: 0.9rem;'>Page <b>{current_page}</b> of <b>{total_pages}</b></div>", unsafe_allow_html=True)
                                with nav_col3:
                                    if st.button("Next ➡️", key=f"next_pg_{subject_name}_{mat['filename']}") and current_page < total_pages:
                                        st.session_state[page_index_key] += 1
                                        st.rerun()
                                        
                                # Render page text content beautifully in a scrollable frame
                                st.markdown("---")
                                st.markdown(f"""
                                <div style="background-color: #1E293B; color: #F1F5F9; border: 1px solid #334155; padding: 25px; border-radius: 8px; font-family: 'Inter', sans-serif; line-height: 1.7; font-size: 0.95rem; max-height: 450px; overflow-y: auto; white-space: pre-wrap;">
{pages[current_page - 1].page_content}
                                </div>
                                """, unsafe_allow_html=True)
                                st.markdown("---")
                        except Exception as e:
                            st.error(f"Failed to initialize browser preview structure: {e}")
    else:
        st.info("No official uploaded reading text documents are listed for this subject profile track yet.")


# --- GLOBAL NAVIGATION BAR ---
nav_col1, nav_col2 = st.columns([4, 1])
with nav_col1:
    st.markdown("""
    <div style="padding-top: 5px;">
        <h2 style="margin: 0; font-family: 'Outfit', sans-serif; font-weight: 800; color: #4F46E5; display: flex; align-items: center;">
            <span style="margin-right: 8px;">🎓</span> Scholar's Hub
        </h2>
    </div>
    """, unsafe_allow_html=True)
with nav_col2:
    if not st.session_state.logged_in:
        if st.button("Sign In", use_container_width=True):
            st.session_state.view_mode = "Auth"
            st.rerun()
    else:
        st.write(f"👋 {st.session_state.user_info.get('student_name', st.session_state.user_info.get('name', 'User'))}")
        if st.button("Log Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_info = None
            st.session_state.user_role = "student"
            st.session_state.view_mode = "Browse"
            st.rerun()

st.divider()

# ====================================================================
# VIEW 1: ANONYMOUS HOMEPAGE BROWSE MODE
# ====================================================================
if st.session_state.view_mode == "Browse":
    # Two-column premium hero section
    col_hero_left, col_hero_right = st.columns([1.2, 1])
    with col_hero_left:
        st.markdown("""
        <div style="padding-top: 35px; margin-bottom: 20px;">
            <h1 style="font-size: 3.2rem; font-weight: 800; line-height: 1.15; margin-bottom: 20px; color: #0F172A;">
                Make yourself one <br><span style="color: #4F46E5;">Comfort & Professional</span>
            </h1>
            <p style="font-size: 1.15rem; color: #4B5563; line-height: 1.6; margin-bottom: 30px;">
                Comprehensive educational experiences that develop and enhance skill sets that can be applied to diverse job profiles.
            </p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Find your desired Course", key="hero_find_btn"):
            st.session_state.view_mode = "Auth"
            st.rerun()
    with col_hero_right:
        st.markdown("""
        <div style="border-radius: 24px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.08);">
            <img src="https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=600" style="width: 100%; object-fit: cover;" />
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.divider()
    
    st.write("### Featured Category")
    sub_cols = st.columns(4)
    subjects = ["Literature", "Physics", "Chemistry", "Math"]
    emojis = ["📖", "🔬", "🧪", "🧮"]
    
    for sub, col, emoji in zip(subjects, sub_cols, emojis):
        with col:
            st.markdown(f"""
            <div class="card-wrapper" style="text-align: center; padding: 25px 15px;">
                <span style="font-size: 2.2rem; display: block; margin-bottom: 12px;">{emoji}</span>
                <h4 style="margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 700; color: #1E293B;">{sub}</h4>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"Browse {sub}", key=f"browse_{sub}", use_container_width=True):
                st.session_state.current_subject = sub
                st.rerun()

    st.divider()
    
    st.write(f"### Current Listings under **{st.session_state.current_subject}**")
    active_courses = fetch_courses_by_subject(st.session_state.current_subject, "ANONYMOUS_PREVIEW")
    
    # Simple formatting validation fallback if course matrix empty
    if not active_courses:
        active_courses = [
            {"title": f"Introductory {st.session_state.current_subject} Track", "rating": "4.5", "img_url": "https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=400"},
            {"title": f"Advanced {st.session_state.current_subject} Track", "rating": "4.8", "img_url": "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=400"}
        ]

    c_col1, c_col2 = st.columns(2)
    for idx, col in enumerate([c_col1, c_col2]):
        if idx < len(active_courses):
            with col:
                st.markdown(f"""
                <div class="card-wrapper" style="padding: 0; overflow: hidden; border-radius: 16px;">
                    <img src="{active_courses[idx].get('img_url', 'https://images.unsplash.com/photo-1516321318423-f06f85e504b3?w=400')}" style="width: 100%; height: 200px; object-fit: cover;" />
                    <div style="padding: 20px;">
                        <span style="background-color: #EEF2F6; color: #4F46E5; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: 600;">Recorded</span>
                        <h4 style="margin: 15px 0 10px 0; font-size: 1.15rem; color: #0F172A;">{active_courses[idx]['title']}</h4>
                        <span style="color: #F59E0B; font-weight: 600; font-size: 0.95rem;">⭐ {active_courses[idx]['rating']} <span style="color: #6B7280; font-weight: 400; font-size: 0.85rem;">(0 reviews)</span></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Enroll Now ({active_courses[idx]['title']})", key=f"enr_{idx}", use_container_width=True):
                    st.session_state.view_mode = "Auth"
                    st.rerun()

# ====================================================================
# VIEW 2: AUTHENTICATION ENVELOPE GATEWAY
# ====================================================================
elif st.session_state.view_mode == "Auth":
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h2 style="margin: 0; color: #4F46E5; font-size: 2rem;">🔓 System Authentication Gateway</h2>
        <p style="color: #6B7280; margin-top: 5px;">Access your profile dashboard or create a new account</p>
    </div>
    """, unsafe_allow_html=True)
    
    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔒 Secure Sign In", "🎓 Student Registration", "👩‍🏫 Teacher Registration"])
    
    with auth_tab1:
        st.markdown("""
        <div style="background: white; border: 1px solid #E2E8F0; padding: 25px; border-radius: 16px; margin-bottom: 20px;">
            <h4 style="margin-top: 0; margin-bottom: 10px; color: #1E293B;">Login to Scholar's Workspace</h4>
            <p style="color: #6B7280; font-size: 0.85rem; margin-bottom: 20px;">Enter your student ID or teacher registration number below.</p>
        </div>
        """, unsafe_allow_html=True)
        
        login_reg = st.text_input("Registration / ID Number:", placeholder="e.g., 20261004 or T-2026")
        login_pass = st.text_input("Password:", type="password")
        
        if st.button("Secure Sign In", key="login_btn", use_container_width=True):
            if login_reg and login_pass:
                # 1. Attempt Student verification
                user = verify_user(login_reg, login_pass)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_info = user
                    st.session_state.user_role = "student"
                    st.session_state.view_mode = "Dashboard"
                    st.success("Access Verified! Redirecting to Student panel...")
                    st.rerun()
                else:
                    # 2. Attempt Teacher verification
                    t_user = verify_teacher(login_reg, login_pass)
                    if t_user:
                        st.session_state.logged_in = True
                        st.session_state.user_info = t_user
                        st.session_state.user_role = "teacher"
                        st.session_state.view_mode = "TeacherDashboard"
                        st.success("Access Verified! Redirecting to Teacher portal...")
                        st.rerun()
                    else:
                        st.error("Invalid ID or Password combination. Please try again.")
            else:
                st.warning("Please fill out all fields.")
                
    with auth_tab2:
        st.markdown("<div style='margin-bottom: 15px;'><h4>Create Student Profile</h4></div>", unsafe_allow_html=True)
        reg_num = st.text_input("Assign Reg Number (Numeric Sequence):", placeholder="e.g., 20261005")
        fullname = st.text_input("Student Legal Fullname:")
        reg_pass = st.text_input("Create Secure Password:", type="password")
        if st.button("Create Student Account Profile", key="reg_btn", use_container_width=True):
            if reg_num.isdigit() and fullname and reg_pass:
                if register_user(reg_num, fullname, reg_pass):
                    st.success("Profile written to XAMPP! You can now log in using the Sign In tab.")
            else:
                st.warning("Please ensure Registration Number is numeric and fields are populated.")
 
    with auth_tab3:
        st.markdown("<div style='margin-bottom: 15px;'><h4>Register Teacher credentials</h4></div>", unsafe_allow_html=True)
        t_reg_num = st.text_input("Teacher Reg Number:", placeholder="e.g., T-2026")
        t_fullname = st.text_input("Teacher Fullname:")
        t_reg_pass = st.text_input("Teacher Secure Password:", type="password")
        if st.button("Create Teacher Account Profile", key="t_reg_btn", use_container_width=True):
            if t_reg_num and t_fullname and t_reg_pass:
                if register_teacher(t_reg_num, t_fullname, t_reg_pass):
                    st.success("Teacher Profile created! You can now log in using the Sign In tab.")
            else:
                st.warning("Please fill out all fields.")

# ====================================================================
# VIEW 4: TEACHER DASHBOARD
# ====================================================================
elif st.session_state.view_mode == "TeacherDashboard":
    import os
    from engine import generate_student_report
    from vector_store import create_knowledge_base
    
    st.write(f"### 👩‍🏫 Welcome, Teacher {st.session_state.user_info.get('name')}")
    st.caption(f"Teacher ID: {st.session_state.user_info.get('reg_number')}")
    
    t_tab1, t_tab2, t_tab3 = st.tabs(["📊 Student Reports", "📚 Course Materials", "⚙️ Settings"])
    
    with t_tab1:
        st.write("#### Enrolled Students Progress")
        students_df = get_all_students_performance()
        if not students_df.empty:
            st.dataframe(students_df)
            
            selected_student = st.selectbox("Select Student for AI Report:", students_df['reg_number'].tolist())
            if st.button("Generate AI Diagnostic Report"):
                with st.spinner("AI is analyzing student performance..."):
                    threshold = get_performance_threshold(st.session_state.user_info['reg_number'])
                    report = generate_student_report(selected_student, threshold)
                    st.markdown("### 🤖 Agentic AI Report")
                    st.info(report)
        else:
            st.write("No students enrolled yet.")
            
    with t_tab2:
        st.write("#### Upload Course Materials")
        subject = st.selectbox("Target Subject:", ["Literature", "Physics", "Chemistry", "Math"])
        uploaded_file = st.file_uploader("Upload PDF", type=["pdf"])
        if st.button("Upload and Process"):
            if uploaded_file is not None:
                os.makedirs("data", exist_ok=True)
                file_path = os.path.join("data", uploaded_file.name)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                with st.spinner("Processing document into AI Knowledge Base..."):
                    create_knowledge_base(file_path)
                    save_course_material_record(subject, uploaded_file.name, st.session_state.user_info['reg_number'])
                    st.success(f"{uploaded_file.name} processed and added to Knowledge Base for {subject}!")
            else:
                st.warning("Please select a file.")
                
    with t_tab3:
        st.write("#### AI Assessment Threshold")
        current_threshold = get_performance_threshold(st.session_state.user_info['reg_number'])
        new_threshold = st.slider("Minimum Performance Threshold (%)", 0, 100, current_threshold)
        if st.button("Save Settings"):
            set_performance_threshold(st.session_state.user_info['reg_number'], new_threshold)
            st.success("Threshold updated successfully.")

# ====================================================================
# VIEW 3: STUDENT DASHBOARD PORTAL
# ====================================================================
elif st.session_state.view_mode == "Dashboard":
    from database import fetch_student_enrollments, enroll_in_subject, update_reading_time, fetch_student_performance_summary
    
    # Inject study timer alert (5 minutes = 300,000 ms)
    components.html("""
    <script>
    setInterval(function() {
        window.parent.alert("You've been studying for 5 minutes! Don't forget to click the 'Log 5 Minutes of Study Time' button.");
    }, 300000);
    </script>
    """, height=0, width=0)
    
    # Initialize localized structural quiz states
    if "quiz_active" not in st.session_state:
        st.session_state.quiz_active = False
    if "current_quiz_sub" not in st.session_state:
        st.session_state.current_quiz_sub = None
    if "student_subpage" not in st.session_state:
        st.session_state.student_subpage = "Home"

    # Fetch fresh aggregate metrics from XAMPP database
    perf = fetch_student_performance_summary(st.session_state.user_info['reg_number'])
    enrollments = fetch_student_enrollments(st.session_state.user_info['reg_number'])
    
    # Extract subject names exactly as they are saved in your DB columns
    enrolled_subjects = [e['subject_name'] for e in enrollments]
    
    # Render top navigation controls if quiz is not active
    if not st.session_state.quiz_active:
        st.markdown(f"""
        <div style="background: white; border: 1px solid #E2E8F0; padding: 15px 30px; border-radius: 16px; box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05); margin-bottom: 25px; display: flex; justify-content: space-between; align-items: center;">
            <span style="font-family: 'Outfit', sans-serif; font-weight: 800; font-size: 1.5rem; color: #4F46E5;">🎓 Scholar's Dashboard</span>
        </div>
        """, unsafe_allow_html=True)
        
        nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 1])
        with nav_col1:
            if st.button("🏠 Workspace Home", key="nav_home", use_container_width=True):
                st.session_state.student_subpage = "Home"
                st.rerun()
        with nav_col2:
            if st.button("📚 Enrolled tracks", key="nav_courses", use_container_width=True):
                st.session_state.student_subpage = "Courses"
                st.rerun()
        with nav_col3:
            if st.button("👤 Profile", key="nav_profile", use_container_width=True):
                st.session_state.student_subpage = "Profile"
                st.rerun()
        st.divider()

    # ====================================================================
    # SUB-VIEW A: ACTIVE INTERACTIVE EXAM TESTING INTERFACE
    # ====================================================================
    if st.session_state.quiz_active:
        st.write(f"### 🎯 Agentic Assessment Profile: {st.session_state.current_quiz_sub}")
        
        from engine import generate_dynamic_quiz
        import json
        
        if "quiz_data" not in st.session_state or st.session_state.get("quiz_subject") != st.session_state.current_quiz_sub:
            with st.spinner("AI is generating your customized assessment..."):
                quiz_data = generate_dynamic_quiz(st.session_state.current_quiz_sub)
                if not quiz_data:
                    st.error("Could not generate quiz. Teacher might not have uploaded materials yet.")
                    if st.button("Cancel Assessment"):
                        st.session_state.quiz_active = False
                        st.rerun()
                else:
                    st.session_state.quiz_data = quiz_data
                    st.session_state.quiz_subject = st.session_state.current_quiz_sub
                    st.rerun()
        
        if "quiz_data" in st.session_state and st.session_state.quiz_data:
            st.info("Answer the questions below. Your final score vector will be evaluated by the diagnostic agent.")
            
            with st.form("assessment_form"):
                user_answers = {}
                for i, q in enumerate(st.session_state.quiz_data):
                    st.write(f"**Question {i+1}: {q['question']}**")
                    user_answers[i] = st.radio(f"Select the correct choice for Q{i+1}:", q['options'], key=f"q_{i}")
                    
                submit_exam = st.form_submit_button("Submit Assessment to Database")
                
                if submit_exam:
                    score = 0
                    wrong_topics = []
                    total = len(st.session_state.quiz_data)
                    
                    for i, q in enumerate(st.session_state.quiz_data):
                        if user_answers[i] == q['answer']:
                            score += (100 / total)
                        else:
                            wrong_topics.append(q['question'])
                            
                    # Log final calculation to MySQL quiz_results
                    from database import get_db_connection
                    conn = get_db_connection()
                    if conn is not None:
                        try:
                            with conn.session as session:
                                from sqlalchemy import text
                                statement = text(
                                    "INSERT INTO quiz_results (reg_number, subject_name, score, wrong_topics_json) "
                                    "VALUES (:reg, :sub, :score, :wrong);"
                                )
                                session.execute(statement, {
                                    "reg": st.session_state.user_info['reg_number'],
                                    "sub": st.session_state.current_quiz_sub,
                                    "score": score,
                                    "wrong": json.dumps(wrong_topics)
                                })
                                session.commit()
                            st.success(f"Exam processing complete! You scored {int(score)}%")
                        except Exception as e:
                            st.error(f"Failed to commit exam results: {e}")
                    
                    st.session_state.quiz_active = False
                    st.session_state.current_quiz_sub = None
                    if "quiz_data" in st.session_state: del st.session_state.quiz_data
                    st.rerun()
            
            if st.button("Cancel Assessment", key="cancel_top_quiz"):
                st.session_state.quiz_active = False
                if "quiz_data" in st.session_state: del st.session_state.quiz_data
                st.rerun()

    # ====================================================================
    # SUB-VIEW B: HOME PAGE WORKSPACE
    # ====================================================================
    elif st.session_state.student_subpage == "Home":
        # Welcome back card matching mobile view screenshot
        st.markdown(f"""
        <div style="background: white; border: 1px solid #E2E8F0; padding: 25px; border-radius: 24px; box-shadow: 0 4px 20px -2px rgba(0,0,0,0.05); margin-bottom: 25px; display: flex; align-items: center;">
            <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=100" style="width: 70px; height: 70px; border-radius: 50%; object-fit: cover; margin-right: 20px; border: 3px solid #4F46E5;" />
            <div>
                <h3 style="margin: 0; font-weight: 800; font-size: 1.4rem; color: #0F172A;">hi {st.session_state.user_info.get('student_name', 'Student')}</h3>
                <p style="margin: 5px 0 0 0; color: #6B7280; font-size: 0.95rem;">Welcome Back</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Dashboard slide banner
        st.markdown("""
        <div style="border-radius: 24px; overflow: hidden; margin-bottom: 30px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.05);">
            <img src="https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=800" style="width: 100%; height: 260px; object-fit: cover;" />
        </div>
        """, unsafe_allow_html=True)
        
        # Featured Category block
        st.write("### Featured Category")
        sub_cols = st.columns(4)
        subjects = ["Literature", "Physics", "Chemistry", "Math"]
        emojis = ["📖", "🔬", "🧪", "🧮"]
        
        for sub, col, emoji in zip(subjects, sub_cols, emojis):
            with col:
                st.markdown(f"""
                <div class="card-wrapper" style="text-align: center; padding: 25px 15px;">
                    <span style="font-size: 2.2rem; display: block; margin-bottom: 12px;">{emoji}</span>
                    <h4 style="margin: 0 0 10px 0; font-size: 1.05rem; font-weight: 700; color: #1E293B;">{sub}</h4>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Go to {sub}", key=f"sub_go_{sub}", use_container_width=True):
                    st.session_state.student_subpage = "Courses"
                    st.rerun()
                    
        st.divider()
        st.write("### Recommended Reading Materials")
        st.info("Head over to the Enrolled tracks tab to read full documents uploaded by teachers!")

    # ====================================================================
    # SUB-VIEW C: PROFILE PAGE WORKSPACE
    # ====================================================================
    elif st.session_state.student_subpage == "Profile":
        st.markdown(f"""
        <div style="background: white; border: 1px solid #E2E8F0; padding: 30px; border-radius: 24px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.05); text-align: center; margin-bottom: 25px;">
            <img src="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=120" style="width: 110px; height: 110px; border-radius: 50%; object-fit: cover; border: 4px solid #4F46E5; margin-bottom: 15px;" />
            <h3 style="margin: 0; font-weight: 800; font-size: 1.6rem; color: #0F172A;">{st.session_state.user_info.get('student_name', 'Student')}</h3>
            <div style="width: 100px; height: 3px; background-color: #4F46E5; margin: 15px auto;"></div>
            <p style="margin: 5px 0; color: #6B7280; font-size: 0.9rem;">Registration ID: <b>{st.session_state.user_info.get('reg_number')}</b></p>
            <p style="margin: 0; color: #6B7280; font-size: 0.9rem;">Member since: <b>09-03-2026</b></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Enrolled tab selector interface simulation
        st.write("### Enrolled Course Tracks")
        if enrolled_subjects:
            for sub in enrolled_subjects:
                st.markdown(f"""
                <div class="card-wrapper">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <h4 style="margin: 0; color: #1E293B;">📖 Subject: {sub}</h4>
                            <p style="margin: 5px 0 0 0; color: #6B7280; font-size: 0.85rem;">Enrolled track status active</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"Go to Classroom: {sub}", key=f"play_{sub}", use_container_width=True):
                    st.session_state.student_subpage = "Courses"
                    st.rerun()
        else:
            st.info("You haven't enrolled in any subjects yet. Head to the Workspace page to enroll!")

    # ====================================================================
    # SUB-VIEW D: NORMAL COURSES WORKSPACE DISPLAY
    # ====================================================================
    elif st.session_state.student_subpage == "Courses":
        dash_left, dash_right = st.columns([2, 1])
        
        with dash_left:
            st.write("### 📖 Your Enrolled Course Tracks")
            
            if len(enrolled_subjects) > 0:
                # Handle singular vs multiple tab views perfectly
                if len(enrolled_subjects) == 1:
                    current_sub = enrolled_subjects[0]
                    st.write(f"#### Active Track: **{current_sub}**")
                    
                    track_data = next(e for e in enrollments if e['subject_name'] == current_sub)
                    st.caption(f"⏱️ Accumulated Study Velocity: {track_data['total_reading_time']} minutes")
                    
                    sub_courses = fetch_courses_by_subject(current_sub, st.session_state.user_info['reg_number'])
                    course_title = sub_courses[0]['title'] if sub_courses else f"Introductory {current_sub} Materials"
                    
                    st.markdown(f"""
                    <div style="background-color: #1E293B; padding: 25px; border-radius: 16px; border: 1px solid #334155; margin-bottom: 20px; color: #F1F5F9;">
                        <h4 style="color: #38BDF8 !important; margin-top: 0;">📖 Active Module: {course_title}</h4>
                        <p style="font-size:0.95rem; line-height:1.6; color:#CBD5E1; margin-bottom:0;">
                            Welcome to your dedicated {current_sub} workspace portal. Read through your assigned files, 
                            track your progress metrics, and use the AI workspace on the right for continuous chat support.
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # NEWLY ADDED: Inline File Viewing Portal for Single Track
                    display_course_materials_section(current_sub)
                    
                    st.write("")
                    if st.button("⏱️ Log 5 Minutes of Study Time", key=f"ping_{current_sub}", use_container_width=True):
                        update_reading_time(st.session_state.user_info['reg_number'], current_sub, 5)
                        st.toast("Telemetry data flushed to XAMPP server!", icon="💾")
                        st.rerun()
                        
                    st.write("")
                    st.markdown("""
                    <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px dashed #0D9488; text-align:center; margin-bottom: 10px;">
                        <span style="font-size:0.85rem; color:#9CA3AF;">Ready to assess your concept mapping metrics?</span>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button(f"🎯 Launch Agentic Quiz Engine: {current_sub}", key=f"quiz_{current_sub}", use_container_width=True):
                        st.session_state.quiz_active = True
                        st.session_state.current_quiz_sub = current_sub
                        st.rerun()
                
                else:
                    selected_tabs = st.tabs(enrolled_subjects)
                    for tab, current_sub in zip(selected_tabs, enrolled_subjects):
                        with tab:
                            track_data = next(e for e in enrollments if e['subject_name'] == current_sub)
                            st.caption(f"⏱️ Accumulated Study Velocity: {track_data['total_reading_time']} minutes")
                            
                            sub_courses = fetch_courses_by_subject(current_sub, st.session_state.user_info['reg_number'])
                            course_title = sub_courses[0]['title'] if sub_courses else f"Introductory {current_sub} Materials"
                            
                            st.markdown(f"""
                            <div style="background-color: #1E293B; padding: 25px; border-radius: 16px; border: 1px solid #334155; margin-bottom: 20px; color: #F1F5F9;">
                                <h4 style="color: #38BDF8 !important; margin-top: 0;">📖 Active Module: {course_title}</h4>
                                <p style="font-size:0.95rem; line-height:1.6; color:#CBD5E1; margin-bottom:0;">
                                    Welcome to your dedicated {current_sub} workspace portal. Read through your assigned files, 
                                    track your progress metrics, and use the AI workspace on the right for continuous chat support.
                                </p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # NEWLY ADDED: Inline File Viewing Portal for Tabbed Track
                            display_course_materials_section(current_sub)
                            
                            st.write("")
                            if st.button("⏱️ Log 5 Minutes of Study Time", key=f"ping_{current_sub}", use_container_width=True):
                                update_reading_time(st.session_state.user_info['reg_number'], current_sub, 5)
                                st.toast("Telemetry data flushed to XAMPP server!", icon="💾")
                                st.rerun()
                                
                            st.write("")
                            st.markdown("""
                            <div style="background-color: #111827; padding: 15px; border-radius: 8px; border: 1px dashed #0D9488; text-align:center; margin-bottom: 10px;">
                                <span style="font-size:0.85rem; color:#9CA3AF;">Ready to assess your concept mapping metrics?</span>
                            </div>
                            """, unsafe_allow_html=True)
                            if st.button(f"🎯 Launch Agentic Quiz Engine: {current_sub}", key=f"quiz_{current_sub}", use_container_width=True):
                                st.session_state.quiz_active = True
                                st.session_state.current_quiz_sub = current_sub
                                st.rerun()

            # Dynamic Enrollment Portal synchronized exactly with DB entries
            st.write("")
            with st.expander("➕ Enroll in an Additional Subject Track"):
                quick_sub = st.selectbox("Select a core track to expand your profile:", ["Literature", "Physics", "Chemistry", "Math"])
                if st.button("Confirm Enrollment", use_container_width=True):
                    if enroll_in_subject(st.session_state.user_info['reg_number'], quick_sub):
                        st.success(f"Enrolled in {quick_sub} successfully!")
                        st.rerun()

        # ====================================================================
        # RIGHT COLUMN: SYSTEM WORKSPACE ASSISTANT PANEL
        # ====================================================================
        with dash_right:
            st.write("### 🤖 Workspace AI Assistant")
            active_chat_sub = enrolled_subjects[0] if enrolled_subjects else "General Studies"
            st.caption(f"Targeting Context: **{active_chat_sub}**")
            
            chat_box = st.container(height=380)
            if "dash_messages" not in st.session_state:
                st.session_state.dash_messages = []
                
            for msg in st.session_state.dash_messages:
                with chat_box.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
            if user_prompt := st.chat_input("Ask about your active syllabus..."):
                st.session_state.dash_messages.append({"role": "user", "content": user_prompt})
                with chat_box.chat_message("user"):
                    st.markdown(user_prompt)
                    
                with chat_box.chat_message("assistant"):
                    with st.spinner("Analyzing profile records..."):
                        try:
                            from database import get_db_connection
                            conn = get_db_connection()
                            df_last = conn.query("SELECT score, wrong_topics_json FROM quiz_results WHERE reg_number = :reg ORDER BY taken_at DESC LIMIT 1;", params={"reg": st.session_state.user_info['reg_number']})
                            
                            if not df_last.empty:
                                last_score = df_last.iloc[0]['score']
                                missed = df_last.iloc[0]['wrong_topics_json']
                                ai_context = f"The student just took a quiz in {active_chat_sub} and scored {last_score}%. They struggled with: {missed}."
                            else:
                                ai_context = f"The student has logged {perf['total_time']} minutes of total reading time in {active_chat_sub}."
                        except Exception:
                            ai_context = "Profile metrics scanning initializing..."

                        augmented_prompt = f"[System Profile Data Context: {ai_context}] Student Query: {user_prompt}"
                        
                        try:
                            from engine import agent_executor
                            response = agent_executor.invoke({"input": augmented_prompt, "chat_history": st.session_state.dash_messages})
                            output_text = response["output"]
                        except Exception:
                            output_text = f"Hey {st.session_state.user_info['student_name']}, your session context is linked! Ask me any structural questions regarding {active_chat_sub}."
                        
                        st.markdown(output_text)
                        st.session_state.dash_messages.append({"role": "assistant", "content": output_text})