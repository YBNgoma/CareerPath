import os
import logging
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, session, g
from werkzeug.security import generate_password_hash, check_password_hash
import json
import uuid

# Langchain components
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

# --- Configuration ---
PDF_DIRECTORY = "./pdfs"
DATABASE_PATH = "./career_guidance.db"

# Placeholder LLM for demo purposes
class PlaceholderLLM:
    def __call__(self, prompt):
        return f"Based on the career guidance documents, here's my advice: {prompt[:100]}... [This is a placeholder response. Replace with a real LLM for production use.]"
    def predict(self, prompt):
        return self.__call__(prompt)

llm = PlaceholderLLM()

# Global variables
qa_chain = None
vector_store = None

# --- Database Setup ---
def init_db():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            phone TEXT,
            education_level TEXT,
            interests TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            profile_completed BOOLEAN DEFAULT FALSE
        )
    ''')
    
    # Chat history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            response_type TEXT DEFAULT 'answer',
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Career assessments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS career_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            assessment_type TEXT NOT NULL,
            questions TEXT NOT NULL,
            answers TEXT NOT NULL,
            results TEXT NOT NULL,
            score INTEGER,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # User bookmarks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            bookmark_type TEXT NOT NULL,
            bookmark_data TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # User progress tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            career_path TEXT NOT NULL,
            current_stage INTEGER DEFAULT 0,
            completed_stages TEXT DEFAULT '[]',
            target_completion_date DATE,
            notes TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db():
    """Get database connection"""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    """Close database connection"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# --- Enhanced Career Data ---
CAREER_PATHWAYS_ZW = {
    "doctor": {
        "title": "Medical Doctor (MBChB) in Zimbabwe",
        "description": "General pathway to becoming a registered Medical Doctor in Zimbabwe.",
        "difficulty": "Very High",
        "job_prospects": "Excellent",
        "salary_range": "$800 - $3000+ USD",
        "stages": [
            {"stage": "O-Levels", "requirements": "Minimum 5 O-Levels including compulsory English Language, Mathematics, and a Science subject (e.g., Biology, Chemistry, Physics, Integrated Science) with good grades (typically Bs or better).", "duration": "4 years (secondary school)"},
            {"stage": "A-Levels", "requirements": "Primarily Biology and Chemistry are mandatory. Physics or Mathematics is often the third required or highly recommended subject. Highly competitive points are needed.", "duration": "2 years"},
            {"stage": "University (MBChB Degree)", "requirements": "Successful admission into a Bachelor of Medicine and Bachelor of Surgery (MBChB) program at accredited universities like University of Zimbabwe (UZ) or National University of Science and Technology (NUST).", "duration": "5-6 years", "universities_list": ["University of Zimbabwe (UZ)", "National University of Science and Technology (NUST)"]},
            {"stage": "Internship (Housemanship)", "requirements": "Completion of a supervised internship program at designated hospitals.", "duration": "2 years (typically)"},
            {"stage": "Registration", "requirements": "Registration with the Medical and Dental Practitioners Council of Zimbabwe (MDPCZ) to obtain a license to practice.", "duration": "Ongoing"}
        ],
        "timeline_data": {
            "labels": ["O-Levels", "A-Levels", "MBChB Degree", "Internship"],
            "durations": [4, 2, 5.5, 2]
        },
        "skills_required": ["Critical thinking", "Communication", "Empathy", "Attention to detail", "Stress management"],
        "notes": "Entry into medical school is highly competitive. Some universities might have foundation programs or alternative entry routes for candidates with relevant diplomas or other qualifications, but direct A-Level entry is most common."
    },
    "nurse": {
        "title": "Registered General Nurse (RGN) in Zimbabwe",
        "description": "Pathway to becoming a Registered General Nurse in Zimbabwe.",
        "difficulty": "High",
        "job_prospects": "Very Good",
        "salary_range": "$300 - $800 USD",
        "stages": [
            {"stage": "O-Levels", "requirements": "Minimum 5 O-Levels including English Language, Mathematics, and a Science subject (e.g., Biology, Chemistry, Physics, Integrated Science) with good grades.", "duration": "4 years (secondary school)"},
            {"stage": "Nurse Training", "requirements": "Successful application and admission into a 3-year Diploma in General Nursing program at a recognized nursing school (usually hospital-based). Some universities also offer BSc Nursing degrees.", "duration": "3 years (Diploma) / 4 years (Degree)"},
            {"stage": "Registration", "requirements": "Registration with the Nurses Council of Zimbabwe (NCZ) after passing a qualifying examination.", "duration": "Ongoing"}
        ],
        "timeline_data": {
            "labels": ["O-Levels", "Nurse Training (Diploma)"],
            "durations": [4, 3]
        },
        "skills_required": ["Compassion", "Communication", "Physical stamina", "Attention to detail", "Teamwork"],
        "notes": "There are various specializations available after becoming an RGN, such as midwifery, psychiatric nursing, etc. Degree programs (BSc Nursing) are also available for higher qualifications."
    },
    "engineer": {
        "title": "Professional Engineer in Zimbabwe",
        "description": "General pathway to becoming a Professional Engineer in Zimbabwe.",
        "difficulty": "High",
        "job_prospects": "Good",
        "salary_range": "$500 - $2000+ USD",
        "stages": [
            {"stage": "O-Levels", "requirements": "Minimum 5 O-Levels including English Language, Mathematics, Physics, and Chemistry (or Integrated Science) with good grades.", "duration": "4 years"},
            {"stage": "A-Levels", "requirements": "Mathematics and Physics are typically mandatory. Chemistry or another relevant science/technical subject is often required or recommended, depending on the engineering discipline.", "duration": "2 years"},
            {"stage": "University (BSc/BEng Degree)", "requirements": "Admission into an accredited Bachelor of Science (BSc) or Bachelor of Engineering (BEng) program in a specific discipline (e.g., Civil, Electrical, Mechanical) at universities like UZ, NUST, HIT.", "duration": "4-5 years", "universities_list": ["University of Zimbabwe (UZ)", "National University of Science and Technology (NUST)", "Harare Institute of Technology (HIT)"]},
            {"stage": "Graduate Training", "requirements": "Period of supervised practical training under a registered professional engineer.", "duration": "2-4 years (varies)"},
            {"stage": "Professional Registration", "requirements": "Meeting the requirements and passing examinations for registration with the Zimbabwe Institution of Engineers (ZIE) and the Engineering Council of Zimbabwe (ECZ).", "duration": "Ongoing"}
        ],
        "timeline_data": {
            "labels": ["O-Levels", "A-Levels", "BSc/BEng Degree", "Graduate Training"],
            "durations": [4, 2, 4.5, 3]
        },
        "skills_required": ["Problem-solving", "Mathematics", "Analytical thinking", "Project management", "Technical communication"],
        "notes": "Specific requirements can vary by engineering discipline and university. Continuous professional development is crucial."
    },
    "teacher": {
        "title": "Qualified Teacher in Zimbabwe",
        "description": "Pathway to becoming a qualified teacher in Zimbabwe.",
        "difficulty": "Moderate",
        "job_prospects": "Good",
        "salary_range": "$200 - $600 USD",
        "stages": [
            {"stage": "O-Levels", "requirements": "Minimum 5 O-Levels including English Language and Mathematics with good grades.", "duration": "4 years"},
            {"stage": "A-Levels or Diploma", "requirements": "A-Levels in relevant subjects or a teaching diploma from a recognized college.", "duration": "2-3 years"},
            {"stage": "Teacher Training", "requirements": "Bachelor of Education (BEd) or Postgraduate Certificate in Education (PGCE) from a recognized institution.", "duration": "3-4 years (BEd) / 1 year (PGCE)"},
            {"stage": "Registration", "requirements": "Registration with the Teachers Service Commission (TSC).", "duration": "Ongoing"}
        ],
        "timeline_data": {
            "labels": ["O-Levels", "A-Levels", "Teacher Training"],
            "durations": [4, 2, 3.5]
        },
        "skills_required": ["Communication", "Patience", "Leadership", "Creativity", "Subject expertise"],
        "notes": "Teaching offers opportunities for specialization in different subjects and age groups. Continuous professional development is encouraged."
    }
}

UNIVERSITIES_ZW = [
    {"name": "University of Zimbabwe (UZ)", "location": "Harare", "website": "https://www.uz.ac.zw", "type": "Public", "established": "1952", "application_info": "Primarily online applications via their official website. Intake periods are announced, usually around Feb-April for August/September intake. Check specific faculty requirements."},
    {"name": "National University of Science and Technology (NUST)", "location": "Bulawayo", "website": "https://www.nust.ac.zw", "type": "Public", "established": "1991", "application_info": "Online application system. Focus on Science, Technology, Engineering, and Mathematics (STEM). Application period typically March-May."},
    {"name": "Midlands State University (MSU)", "location": "Gweru", "website": "https://www.msu.ac.zw", "type": "Public", "established": "1999", "application_info": "Online applications. Offers a wide range of programs. Check website for specific dates and program requirements."},
    {"name": "Harare Institute of Technology (HIT)", "location": "Harare", "website": "https://www.hit.ac.zw", "type": "Public", "established": "1988", "application_info": "Focus on technology and engineering. Online applications. Known for its hands-on approach to learning."},
    {"name": "Chinhoyi University of Technology (CUT)", "location": "Chinhoyi", "website": "https://www.cut.ac.zw", "type": "Public", "established": "2001", "application_info": "Online applications. Strong focus on technology and practical skills. Check website for details."},
    {"name": "Africa University (AU)", "location": "Mutare", "website": "https://www.africau.edu", "type": "Private", "established": "1992", "application_info": "Private, Pan-African, Methodist-related university. International applications welcome. Check their website for specific procedures."}
]

# Career Assessment Questions
CAREER_ASSESSMENT_QUESTIONS = [
    {
        "id": 1,
        "question": "Which activities do you enjoy most?",
        "options": [
            {"text": "Helping and caring for people", "career_weights": {"doctor": 3, "nurse": 3, "teacher": 2}},
            {"text": "Solving complex problems", "career_weights": {"engineer": 3, "doctor": 2}},
            {"text": "Working with technology", "career_weights": {"engineer": 3}},
            {"text": "Teaching and mentoring others", "career_weights": {"teacher": 3, "doctor": 1, "nurse": 1}}
        ]
    },
    {
        "id": 2,
        "question": "How do you handle stress?",
        "options": [
            {"text": "Very well under pressure", "career_weights": {"doctor": 3, "engineer": 2}},
            {"text": "Well with support", "career_weights": {"nurse": 2, "teacher": 2}},
            {"text": "Prefer low-stress environments", "career_weights": {"teacher": 1}},
            {"text": "Thrive in challenging situations", "career_weights": {"doctor": 3, "engineer": 3}}
        ]
    },
    {
        "id": 3,
        "question": "What motivates you most?",
        "options": [
            {"text": "Making a difference in people's lives", "career_weights": {"doctor": 3, "nurse": 3, "teacher": 3}},
            {"text": "Building and creating things", "career_weights": {"engineer": 3}},
            {"text": "Financial stability", "career_weights": {"doctor": 2, "engineer": 2}},
            {"text": "Knowledge and learning", "career_weights": {"teacher": 2, "doctor": 1, "engineer": 1}}
        ]
    }
]

# --- Database Helper Functions ---
def create_user(email, password, full_name=None):
    """Create a new user in the database"""
    db = get_db()
    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password)
    
    try:
        db.execute(
            'INSERT INTO users (id, email, password_hash, full_name) VALUES (?, ?, ?, ?)',
            (user_id, email, password_hash, full_name)
        )
        db.commit()
        return user_id
    except sqlite3.IntegrityError:
        return None

def authenticate_user(email, password):
    """Authenticate user credentials"""
    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE email = ?', (email,)
    ).fetchone()
    
    if user and check_password_hash(user['password_hash'], password):
        # Update last login
        db.execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?',
            (user['id'],)
        )
        db.commit()
        return dict(user)
    return None

def save_chat_message(user_id, message, response, response_type='answer'):
    """Save chat message to database"""
    db = get_db()
    db.execute(
        'INSERT INTO chat_history (user_id, message, response, response_type) VALUES (?, ?, ?, ?)',
        (user_id, message, response, response_type)
    )
    db.commit()

def get_user_chat_history(user_id, limit=50):
    """Get user's chat history"""
    db = get_db()
    return db.execute(
        'SELECT * FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?',
        (user_id, limit)
    ).fetchall()

def save_career_assessment(user_id, assessment_type, questions, answers, results, score):
    """Save career assessment results"""
    db = get_db()
    db.execute(
        'INSERT INTO career_assessments (user_id, assessment_type, questions, answers, results, score) VALUES (?, ?, ?, ?, ?, ?)',
        (user_id, assessment_type, json.dumps(questions), json.dumps(answers), json.dumps(results), score)
    )
    db.commit()

def get_user_assessments(user_id):
    """Get user's assessment history"""
    db = get_db()
    return db.execute(
        'SELECT * FROM career_assessments WHERE user_id = ? ORDER BY completed_at DESC',
        (user_id,)
    ).fetchall()

# --- Langchain Initialization ---
def initialize_langchain():
    global qa_chain, vector_store
    if not os.path.exists(PDF_DIRECTORY) or not os.listdir(PDF_DIRECTORY):
        logging.warning(f"PDF directory '{PDF_DIRECTORY}' is empty or does not exist. QA functionality will be limited.")
        vector_store = None
        qa_chain = None
        return

    try:
        logging.info(f"Loading PDFs from {PDF_DIRECTORY}...")
        loader = PyPDFDirectoryLoader(PDF_DIRECTORY)
        documents = loader.load()

        if not documents:
            logging.warning("No documents loaded from PDFs. QA functionality will be limited.")
            vector_store = None
            qa_chain = None
            return

        logging.info(f"Loaded {len(documents)} pages from PDFs.")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        texts = text_splitter.split_documents(documents)
        logging.info(f"Split documents into {len(texts)} chunks.")

        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
        logging.info("Creating FAISS vector store...")
        vector_store = FAISS.from_documents(texts, embeddings)
        logging.info("FAISS vector store created successfully.")

        qa_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=vector_store.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True
        )
        logging.info("Langchain QA chain initialized successfully.")

    except Exception as e:
        logging.error(f"Error initializing Langchain: {e}", exc_info=True)
        qa_chain = None
        vector_store = None

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your_very_secret_key_for_dev")
logging.basicConfig(level=logging.INFO)

# Initialize database and Langchain
init_db()
initialize_langchain()

@app.teardown_appcontext
def close_db_connection(error):
    close_db(error)

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/profile')
def profile_page():
    return render_template('profile.html')

@app.route('/assessment')
def assessment_page():
    return render_template('assessment.html')

# --- API Endpoints ---
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400
    
    user_id = create_user(email, password, full_name)
    if user_id:
        return jsonify({"success": True, "message": "User created successfully", "user_id": user_id})
    else:
        return jsonify({"success": False, "message": "Email already exists"}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"success": False, "message": "Email and password are required"}), 400
    
    user = authenticate_user(email, password)
    if user:
        session['user_id'] = user['id']
        session['user_email'] = user['email']
        return jsonify({"success": True, "message": "Login successful", "user": {"id": user['id'], "email": user['email'], "full_name": user['full_name']}})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out successfully"})

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"response_type": "error", "data": {"message": "Invalid request. 'message' field is required."}}), 400

    user_message = data['message'].strip()
    user_id = session.get('user_id', 'anonymous')
    
    response_payload = {
        "response_type": "answer",
        "data": {"text": "Sorry, I couldn't understand that command or find an answer."},
        "user_id_for_display": user_id
    }

    if user_message.lower().startswith('/'):
        command_parts = user_message.lower().split()
        command = command_parts[0]

        if command == '/doctor':
            response_payload["response_type"] = "pathway"
            response_payload["data"] = CAREER_PATHWAYS_ZW.get("doctor")
        elif command == '/nurse':
            response_payload["response_type"] = "pathway"
            response_payload["data"] = CAREER_PATHWAYS_ZW.get("nurse")
        elif command == '/engineer':
            response_payload["response_type"] = "pathway"
            response_payload["data"] = CAREER_PATHWAYS_ZW.get("engineer")
        elif command == '/teacher':
            response_payload["response_type"] = "pathway"
            response_payload["data"] = CAREER_PATHWAYS_ZW.get("teacher")
        elif command == '/universities':
            response_payload["response_type"] = "list"
            response_payload["data"] = {
                "list_title": "Universities in Zimbabwe",
                "items": UNIVERSITIES_ZW
            }
        elif command == '/history' and user_id != 'anonymous':
            history = get_user_chat_history(user_id, 20)
            response_payload["response_type"] = "history"
            response_payload["data"] = {
                "history": [{"message": h['message'], "response": h['response'], "timestamp": h['timestamp']} for h in history]
            }
        elif command == '/help':
            commands_list = [
                {"command": "/doctor", "description": "Get pathway for becoming a doctor."},
                {"command": "/nurse", "description": "Get pathway for becoming a nurse."},
                {"command": "/engineer", "description": "Get pathway for becoming an engineer."},
                {"command": "/teacher", "description": "Get pathway for becoming a teacher."},
                {"command": "/universities", "description": "List universities in Zimbabwe."},
                {"command": "/history", "description": "View your chat history (requires login)."},
                {"command": "/help", "description": "Show this help message."},
            ]
            response_payload["response_type"] = "list"
            response_payload["data"] = {
                "list_title": "Available Commands",
                "items": commands_list
            }
        else:
            response_payload["data"]["text"] = f"Unknown command: {command}. Try /help for a list of commands."

    elif qa_chain:
        try:
            logging.info(f"Querying Langchain QA chain with: {user_message}")
            result = qa_chain({"query": user_message})
            answer = result.get("result", "No answer found in documents.")
            sources = []
            if result.get("source_documents"):
                for doc in result["source_documents"]:
                    sources.append({
                        "filename": os.path.basename(doc.metadata.get("source", "Unknown source")) if doc.metadata else "Unknown source",
                        "content_snippet": doc.page_content[:150] + "..."
                    })
            
            response_payload["data"]["text"] = answer
            if sources:
                response_payload["data"]["sources"] = sources

        except Exception as e:
            logging.error(f"Error querying Langchain QA chain: {e}", exc_info=True)
            response_payload["data"]["text"] = "Sorry, an error occurred while processing your question from the documents."
    
    else:
        response_payload["data"]["text"] = "Sorry, the document query system is not available right now. Please try asking a general question or use a command like /help."

    # Save chat message to database if user is logged in
    if user_id != 'anonymous':
        save_chat_message(user_id, user_message, str(response_payload["data"]), response_payload["response_type"])

    return jsonify(response_payload)

@app.route('/api/assessment', methods=['POST'])
def career_assessment_endpoint():
    data = request.get_json()
    answers = data.get('answers', [])
    user_id = session.get('user_id', 'anonymous')
    
    if not answers:
        return jsonify({"success": False, "message": "No answers provided"}), 400
    
    # Calculate career scores
    career_scores = {"doctor": 0, "nurse": 0, "engineer": 0, "teacher": 0}
    
    for i, answer_idx in enumerate(answers):
        if i < len(CAREER_ASSESSMENT_QUESTIONS) and answer_idx < len(CAREER_ASSESSMENT_QUESTIONS[i]['options']):
            option = CAREER_ASSESSMENT_QUESTIONS[i]['options'][answer_idx]
            for career, weight in option['career_weights'].items():
                career_scores[career] += weight
    
    # Sort careers by score
    sorted_careers = sorted(career_scores.items(), key=lambda x: x[1], reverse=True)
    
    results = {
        "scores": career_scores,
        "recommended_careers": [
            {
                "career": career,
                "score": score,
                "percentage": round((score / max(career_scores.values()) * 100) if max(career_scores.values()) > 0 else 0, 1),
                "pathway": CAREER_PATHWAYS_ZW.get(career, {})
            }
            for career, score in sorted_careers if score > 0
        ]
    }
    
    # Save assessment if user is logged in
    if user_id != 'anonymous':
        save_career_assessment(user_id, 'basic_career_match', CAREER_ASSESSMENT_QUESTIONS, answers, results, max(career_scores.values()))
    
    return jsonify({"success": True, "results": results})

@app.route('/api/user/profile', methods=['GET'])
def get_user_profile():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    assessments = get_user_assessments(user_id)
    
    if user:
        return jsonify({
            "success": True,
            "user": dict(user),
            "assessments": [dict(a) for a in assessments]
        })
    
    return jsonify({"success": False, "message": "User not found"}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)