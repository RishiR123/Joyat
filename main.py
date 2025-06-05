from flask import Flask, request, jsonify, render_template, send_from_directory
import json
import os
import random
import string
from datetime import datetime
import threading
import re

app = Flask(__name__)

# File paths for persistent storage
DATA_DIR = 'exam_data'
EXAMS_FILE = os.path.join(DATA_DIR, 'exams.json')
RESULTS_FILE = os.path.join(DATA_DIR, 'results.json')

# Default admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Thread lock for file operations
file_lock = threading.Lock()

# School options
SCHOOLS = [
    "School of Engineering and Technology","School of Design","School of Computational Intelligence","School of Arts & Natural Sciences","School of Agricultural Sciences","School of Law","School of Life & Health Sciences","School of Nursing","School of Pharmacy"
    
]

def ensure_data_directory():
    """Ensure the data directory exists"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def load_exams():
    """Load exams from disk"""
    ensure_data_directory()
    try:
        if os.path.exists(EXAMS_FILE):
            with open(EXAMS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading exams: {e}")
        return {}

def save_exams(exams):
    """Save exams to disk"""
    ensure_data_directory()
    try:
        with file_lock:
            with open(EXAMS_FILE, 'w', encoding='utf-8') as f:
                json.dump(exams, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving exams: {e}")
        return False

def load_results():
    """Load results from disk"""
    ensure_data_directory()
    try:
        if os.path.exists(RESULTS_FILE):
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading results: {e}")
        return []

def save_results(results):
    """Save results to disk"""
    ensure_data_directory()
    try:
        with file_lock:
            with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving results: {e}")
        return False

def generate_exam_code():
    """Generate a random 6-character exam code"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/')
def index():
    """Serve the main HTML page"""
    return send_from_directory('.', 'index.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    """Handle admin login"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401

@app.route('/admin/create-exam', methods=['POST'])
def create_exam():
    """Create a new exam"""
    data = request.get_json()
    
    # Load current exams
    exams = load_exams()
    
    # Generate unique exam code
    exam_code = generate_exam_code()
    while exam_code in exams:
        exam_code = generate_exam_code()
    
    # Create exam object
    exam = {
        'code': exam_code,
        'title': data.get('title'),
        'duration': data.get('duration'),
        'questions': data.get('questions'),
        'created': datetime.now().isoformat(),
        'active': True
    }
    
    # Validate exam data
    if not exam['title'] or not exam['questions'] or len(exam['questions']) == 0:
        return jsonify({"success": False, "message": "Invalid exam data"}), 400
    
    # Validate questions
    for i, question in enumerate(exam['questions']):
        if not all(key in question for key in ['question', 'options', 'correct']):
            return jsonify({"success": False, "message": f"Invalid question {i+1}"}), 400
        
        if not all(option in question['options'] for option in ['A', 'B', 'C', 'D']):
            return jsonify({"success": False, "message": f"Invalid options for question {i+1}"}), 400
        
        if question['correct'] not in ['A', 'B', 'C', 'D']:
            return jsonify({"success": False, "message": f"Invalid correct answer for question {i+1}"}), 400
    
    # Store exam
    exams[exam_code] = exam
    
    # Save to disk
    if not save_exams(exams):
        return jsonify({"success": False, "message": "Failed to save exam"}), 500
    
    return jsonify({
        "success": True, 
        "message": "Exam created successfully",
        "examCode": exam_code
    })

@app.route('/admin/exams', methods=['GET'])
def get_exams():
    """Get all exams for admin"""
    exams = load_exams()
    exam_list = []
    
    for code, exam in exams.items():
        exam_info = {
            'code': code,
            'title': exam['title'],
            'duration': exam['duration'],
            'questions': exam['questions'],
            'created': exam['created'],
            'active': exam['active']
        }
        exam_list.append(exam_info)
    
    # Sort by creation date (newest first)
    exam_list.sort(key=lambda x: x['created'], reverse=True)
    return jsonify(exam_list)

@app.route('/admin/results', methods=['GET'])
def get_results():
    """Get all exam results for admin"""
    results = load_results()
    # Sort results by submission date (newest first)
    sorted_results = sorted(results, key=lambda x: x['submitted'], reverse=True)
    return jsonify(sorted_results)

@app.route('/api/schools', methods=['GET'])
def get_schools():
    """Get list of available schools"""
    return jsonify(SCHOOLS)

@app.route('/student/join', methods=['POST'])
def student_join():
    """Allow student to join an exam using exam code or 'BIOJOY' for random selection"""
    data = request.get_json()
    exam_code = data.get('examCode', '').upper()
    student_name = data.get('name', '').strip()
    student_id = data.get('studentId', '').strip()
    school = data.get('school', '').strip()

    # Validate required fields
    if not exam_code or not student_name or not student_id or not school:
        return jsonify({"success": False, "message": "All fields are required"}), 400
    
    # Validate school selection
    if school not in SCHOOLS or school == "Select School":
        return jsonify({"success": False, "message": "Please select a valid school"}), 400
    
    # Validate student ID format (should be numeric and reasonable length)
    
    if not re.match(r'^[A-Za-z0-9-_]+$', student_id):
      return jsonify({"success": False, "message": "Student ID should contain only letters, numbers, hyphens, or underscores"}), 400

    # Load exams from disk
    exams = load_exams()

    # Special logic for 'BIOJOY'
    if exam_code == 'BIOJOY':
        possible_codes = ["BIO003", "BIO002", "BIO001"]
        active_codes = [code for code in possible_codes if code in exams and exams[code]['active']]
        if not active_codes:
            return jsonify({"success": False, "message": "No active biology exams available"}), 400
        exam_code = random.choice(active_codes)

    if exam_code not in exams:
        return jsonify({"success": False, "message": "Invalid exam code"}), 404

    exam = exams[exam_code]
    if not exam['active']:
        return jsonify({"success": False, "message": "Exam is not active"}), 400

    # Check if student has already taken this exam
    results = load_results()
    existing_result = next((r for r in results if r['examCode'] == exam_code and r['studentId'] == student_id), None)
    if existing_result:
        return jsonify({"success": False, "message": "You have already taken this exam"}), 400

    # Return exam data without correct answers
    exam_data = {
        'code': exam_code,
        'title': exam['title'],
        'duration': exam['duration'],
        'questions': []
    }

    for question in exam['questions']:
        student_question = {
            'question': question['question'],
            'options': question['options']
        }
        exam_data['questions'].append(student_question)

    return jsonify(exam_data)

@app.route('/student/submit', methods=['POST'])
def submit_exam():
    """Handle exam submission by student"""
    data = request.get_json()
    exam_code = data.get('examCode', '').upper()
    student_name = data.get('studentName', '').strip()
    student_id = data.get('studentId', '').strip()
    school = data.get('school', '').strip()
    answers = data.get('answers', {})
    
    if not all([exam_code, student_name, student_id, school, answers]):
        return jsonify({"success": False, "message": "Missing required data"}), 400
    
    # Load exams from disk
    exams = load_exams()
    
    if exam_code not in exams:
        return jsonify({"success": False, "message": "Invalid exam code"}), 404
    
    exam = exams[exam_code]
    
    # Calculate score
    score = 0
    total_questions = len(exam['questions'])
    
    for i, question in enumerate(exam['questions']):
        student_answer = answers.get(f'question_{i}')
        if student_answer == question['correct']:
            score += 1
    
    # Create result object with additional student information
    result = {
        'examCode': exam_code,
        'examTitle': exam['title'],
        'studentName': student_name,
        'studentId': student_id,
        'school': school,
        'score': score,
        'total': total_questions,
        'percentage': round((score / total_questions) * 100, 2),
        'answers': answers,
        'submitted': datetime.now().isoformat()
    }
    
    # Load current results and add new one
    results = load_results()
    results.append(result)
    
    # Save results to disk
    if not save_results(results):
        return jsonify({"success": False, "message": "Failed to save result"}), 500
    
    return jsonify({
        "success": True,
        "message": "Exam submitted successfully",
        "score": score,
        "total": total_questions,
        "percentage": result['percentage']
    })

@app.route('/admin/delete-exam/<exam_code>', methods=['DELETE'])
def delete_exam(exam_code):
    """Delete an exam (admin only)"""
    exam_code = exam_code.upper()
    
    # Load exams from disk
    exams = load_exams()
    
    if exam_code not in exams:
        return jsonify({"success": False, "message": "Exam not found"}), 404
    
    # Delete exam
    del exams[exam_code]
    
    # Save updated exams
    if not save_exams(exams):
        return jsonify({"success": False, "message": "Failed to delete exam"}), 500
    
    return jsonify({"success": True, "message": "Exam deleted successfully"})

@app.route('/admin/toggle-exam/<exam_code>', methods=['POST'])
def toggle_exam(exam_code):
    """Toggle exam active status (admin only)"""
    exam_code = exam_code.upper()
    
    # Load exams from disk
    exams = load_exams()
    
    if exam_code not in exams:
        return jsonify({"success": False, "message": "Exam not found"}), 404
    
    # Toggle active status
    exams[exam_code]['active'] = not exams[exam_code]['active']
    status = "activated" if exams[exam_code]['active'] else "deactivated"
    
    # Save updated exams
    if not save_exams(exams):
        return jsonify({"success": False, "message": "Failed to update exam status"}), 500
    
    return jsonify({
        "success": True, 
        "message": f"Exam {status} successfully",
        "active": exams[exam_code]['active']
    })

@app.route('/admin/exam-details/<exam_code>', methods=['GET'])
def get_exam_details(exam_code):
    """Get detailed exam information including results (admin only)"""
    exam_code = exam_code.upper()
    
    # Load data from disk
    exams = load_exams()
    results = load_results()
    
    if exam_code not in exams:
        return jsonify({"success": False, "message": "Exam not found"}), 404
    
    exam = exams[exam_code]
    
    # Get results for this exam
    exam_results = [r for r in results if r['examCode'] == exam_code]
    
    # Calculate statistics
    if exam_results:
        scores = [r['score'] for r in exam_results]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        pass_rate = len([s for s in scores if s >= len(exam['questions']) * 0.6]) / len(scores) * 100
        
        # School-wise statistics
        school_stats = {}
        for result in exam_results:
            school = result.get('school', 'Unknown')
            if school not in school_stats:
                school_stats[school] = {'count': 0, 'total_score': 0}
            school_stats[school]['count'] += 1
            school_stats[school]['total_score'] += result['score']
        
        for school in school_stats:
            school_stats[school]['avg_score'] = round(school_stats[school]['total_score'] / school_stats[school]['count'], 2)
    else:
        avg_score = 0
        max_score = 0
        min_score = 0
        pass_rate = 0
        school_stats = {}
    
    return jsonify({
        "exam": exam,
        "results": exam_results,
        "statistics": {
            "totalAttempts": len(exam_results),
            "averageScore": round(avg_score, 2),
            "maxScore": max_score,
            "minScore": min_score,
            "passRate": round(pass_rate, 2),
            "schoolStats": school_stats
        }
    })

@app.route('/admin/backup', methods=['GET'])
def backup_data():
    """Create a backup of all data"""
    try:
        exams = load_exams()
        results = load_results()
        
        backup_data = {
            'exams': exams,
            'results': results,
            'backup_date': datetime.now().isoformat(),
            'schools': SCHOOLS
        }
        
        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(DATA_DIR, backup_filename)
        
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        return jsonify({
            "success": True,
            "message": "Backup created successfully",
            "filename": backup_filename
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Backup failed: {str(e)}"}), 500

@app.route('/admin/restore', methods=['POST'])
def restore_data():
    """Restore data from backup"""
    try:
        data = request.get_json()
        backup_filename = data.get('filename')
        
        if not backup_filename:
            return jsonify({"success": False, "message": "Backup filename required"}), 400
        
        backup_path = os.path.join(DATA_DIR, backup_filename)
        
        if not os.path.exists(backup_path):
            return jsonify({"success": False, "message": "Backup file not found"}), 404
        
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Validate backup data structure
        if 'exams' not in backup_data or 'results' not in backup_data:
            return jsonify({"success": False, "message": "Invalid backup file format"}), 400
        
        # Save restored data
        if not save_exams(backup_data['exams']):
            return jsonify({"success": False, "message": "Failed to restore exams"}), 500
        
        if not save_results(backup_data['results']):
            return jsonify({"success": False, "message": "Failed to restore results"}), 500
        
        return jsonify({
            "success": True,
            "message": "Data restored successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Restore failed: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    exams = load_exams()
    results = load_results()
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "exams_count": len(exams),
        "results_count": len(results),
        "storage_type": "disk",
        "data_directory": DATA_DIR,
        "schools_count": len(SCHOOLS)
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"success": False, "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"success": False, "message": "Internal server error"}), 500

def initialize_sample_data():
    """Initialize sample data if no data exists"""
    exams = load_exams()
    # Add initialization code here if needed
    
    # Only create sample data if no exams exist
    if not exams:
        print("No existing data found. Creating sample exams...")
        
        # Sample exam 1
        sample_exam_code = generate_exam_code()
    sample_exam_1 = {
        'code': "BIO001",
        'title': 'Bio-Science Entrance Exam 1',
        'duration': 50,
        'questions': [
    {
      "question": "What is the primary function of xylem?",
      "options": {
        "A": "Transport of water",
        "B": "Photosynthesis",
        "C": "Food storage",
        "D": "Reproduction"
      },
      "correct": "A"
    },
    {
      "question": "Which pigment is responsible for photosynthesis?",
      "options": {
        "A": "Chlorophyll",
        "B": "Carotene",
        "C": "Xanthophyll",
        "D": "Anthocyanin"
      },
      "correct": "A"
    },
    {
      "question": "Which part of the plant conducts photosynthesis?",
      "options": {
        "A": "Root",
        "B": "Stem",
        "C": "Leaf",
        "D": "Flower"
      },
      "correct": "C"
    },
    {
      "question": "Which of the following is a modified stem?",
      "options": {
        "A": "Carrot",
        "B": "Potato",
        "C": "Radish",
        "D": "Beetroot"
      },
      "correct": "B"
    },
    {
      "question": "The process of conversion of nitrogen into usable form is:",
      "options": {
        "A": "Photosynthesis",
        "B": "Nitrification",
        "C": "Fixation",
        "D": "Fermentation"
      },
      "correct": "C"
    },
    {
      "question": "Which is not a part of the flower?",
      "options": {
        "A": "Petal",
        "B": "Sepal",
        "C": "Node",
        "D": "Stigma"
      },
      "correct": "C"
    },
    {
      "question": "Which gas is released during photosynthesis?",
      "options": {
        "A": "Carbon dioxide",
        "B": "Oxygen",
        "C": "Nitrogen",
        "D": "Hydrogen"
      },
      "correct": "B"
    },
    {
      "question": "The female reproductive part of a flower is:",
      "options": {
        "A": "Stamen",
        "B": "Pistil",
        "C": "Petal",
        "D": "Sepal"
      },
      "correct": "B"
    },
    {
      "question": "Which part of the leaf helps in gas exchange?",
      "options": {
        "A": "Vein",
        "B": "Petiole",
        "C": "Stomata",
        "D": "Midrib"
      },
      "correct": "C"
    },
    {
      "question": "The study of plants is called:",
      "options": {
        "A": "Zoology",
        "B": "Botany",
        "C": "Geology",
        "D": "Anatomy"
      },
      "correct": "B"
    },
    {
      "question": "Which organ is responsible for blood purification?",
      "options": {
        "A": "Heart",
        "B": "Lungs",
        "C": "Kidney",
        "D": "Liver"
      },
      "correct": "C"
    },
    {
      "question": "The basic unit of life is:",
      "options": {
        "A": "Tissue",
        "B": "Cell",
        "C": "Organ",
        "D": "Nucleus"
      },
      "correct": "B"
    },
    {
      "question": "Which of these is a vertebrate?",
      "options": {
        "A": "Earthworm",
        "B": "Ant",
        "C": "Frog",
        "D": "Snail"
      },
      "correct": "C"
    },
    {
      "question": "What type of blood cells fight infections?",
      "options": {
        "A": "RBC",
        "B": "Platelets",
        "C": "Plasma",
        "D": "WBC"
      },
      "correct": "D"
    },
    {
      "question": "Which of these animals is cold-blooded?",
      "options": {
        "A": "Dog",
        "B": "Frog",
        "C": "Cat",
        "D": "Cow"
      },
      "correct": "B"
    },
    {
      "question": "Which part of the brain controls breathing?",
      "options": {
        "A": "Cerebrum",
        "B": "Cerebellum",
        "C": "Medulla",
        "D": "Pons"
      },
      "correct": "C"
    },
    {
      "question": "What is the function of hemoglobin?",
      "options": {
        "A": "Digest fats",
        "B": "Carry oxygen",
        "C": "Store energy",
        "D": "Transmit signals"
      },
      "correct": "B"
    },
    {
      "question": "Which animal is known as the ship of the desert?",
      "options": {
        "A": "Elephant",
        "B": "Horse",
        "C": "Camel",
        "D": "Donkey"
      },
      "correct": "C"
    },
    {
      "question": "The powerhouse of the cell is:",
      "options": {
        "A": "Ribosome",
        "B": "Nucleus",
        "C": "Mitochondria",
        "D": "Golgi body"
      },
      "correct": "C"
    },
    {
      "question": "Which system controls body actions?",
      "options": {
        "A": "Circulatory",
        "B": "Digestive",
        "C": "Nervous",
        "D": "Respiratory"
      },
      "correct": "C"
    },
    {
      "question": "What is the SI unit of force?",
      "options": {
        "A": "Pascal",
        "B": "Newton",
        "C": "Joule",
        "D": "Watt"
      },
      "correct": "B"
    },
    {
      "question": "Light travels fastest in:",
      "options": {
        "A": "Water",
        "B": "Air",
        "C": "Glass",
        "D": "Vacuum"
      },
      "correct": "D"
    },
    {
      "question": "Which law explains action and reaction?",
      "options": {
        "A": "First law",
        "B": "Second law",
        "C": "Third law",
        "D": "Law of inertia"
      },
      "correct": "C"
    },
    {
      "question": "Current is measured using a:",
      "options": {
        "A": "Voltmeter",
        "B": "Ammeter",
        "C": "Thermometer",
        "D": "Galvanometer"
      },
      "correct": "B"
    },
    {
      "question": "The unit of electric power is:",
      "options": {
        "A": "Watt",
        "B": "Volt",
        "C": "Ohm",
        "D": "Ampere"
      },
      "correct": "A"
    },
    {
      "question": "The force of attraction between two masses is called:",
      "options": {
        "A": "Friction",
        "B": "Magnetism",
        "C": "Gravitational force",
        "D": "Electric force"
      },
      "correct": "C"
    },
    {
      "question": "What is used to measure temperature?",
      "options": {
        "A": "Barometer",
        "B": "Hygrometer",
        "C": "Thermometer",
        "D": "Voltmeter"
      },
      "correct": "C"
    },
    {
      "question": "What type of lens is used in a magnifying glass?",
      "options": {
        "A": "Concave",
        "B": "Convex",
        "C": "Plano-concave",
        "D": "Cylindrical"
      },
      "correct": "B"
    },
    {
      "question": "Which color has the highest wavelength?",
      "options": {
        "A": "Red",
        "B": "Blue",
        "C": "Green",
        "D": "Violet"
      },
      "correct": "A"
    },
    {
      "question": "The energy stored in a stretched rubber band is:",
      "options": {
        "A": "Kinetic",
        "B": "Thermal",
        "C": "Potential",
        "D": "Chemical"
      },
      "correct": "C"
    },
    {
      "question": "What is the chemical formula of water?",
      "options": {
        "A": "H2O",
        "B": "CO2",
        "C": "O2",
        "D": "NaCl"
      },
      "correct": "A"
    },
    {
      "question": "Which gas turns lime water milky?",
      "options": {
        "A": "Oxygen",
        "B": "Carbon dioxide",
        "C": "Hydrogen",
        "D": "Nitrogen"
      },
      "correct": "B"
    },
    {
      "question": "Atomic number represents:",
      "options": {
        "A": "Protons",
        "B": "Neutrons",
        "C": "Electrons",
        "D": "Mass number"
      },
      "correct": "A"
    },
    {
      "question": "The pH value of a neutral solution is:",
      "options": {
        "A": "7",
        "B": "1",
        "C": "14",
        "D": "0"
      },
      "correct": "A"
    },
    {
      "question": "What is NaCl commonly known as?",
      "options": {
        "A": "Sugar",
        "B": "Salt",
        "C": "Soda",
        "D": "Acid"
      },
      "correct": "B"
    },
    {
      "question": "Which acid is found in vinegar?",
      "options": {
        "A": "Citric acid",
        "B": "Acetic acid",
        "C": "Oxalic acid",
        "D": "Formic acid"
      },
      "correct": "B"
    },
    {
      "question": "Which metal is liquid at room temperature?",
      "options": {
        "A": "Iron",
        "B": "Mercury",
        "C": "Sodium",
        "D": "Zinc"
      },
      "correct": "B"
    },
    {
      "question": "The symbol 'O' stands for:",
      "options": {
        "A": "Osmium",
        "B": "Oxygen",
        "C": "Oxide",
        "D": "Ozone"
      },
      "correct": "B"
    },
    {
      "question": "Which is a noble gas?",
      "options": {
        "A": "Oxygen",
        "B": "Hydrogen",
        "C": "Argon",
        "D": "Nitrogen"
      },
      "correct": "C"
    },
    {
      "question": "Which part of the atom has a negative charge?",
      "options": {
        "A": "Proton",
        "B": "Neutron",
        "C": "Electron",
        "D": "Nucleus"
      },
      "correct": "C"
    },
    {
      "question": "Choose the correct synonym for 'Happy'.",
      "options": {
        "A": "Sad",
        "B": "Joyful",
        "C": "Angry",
        "D": "Cry"
      },
      "correct": "B"
    },
    {
      "question": "Fill in the blank: He ___ to school every day.",
      "options": {
        "A": "go",
        "B": "goes",
        "C": "gone",
        "D": "going"
      },
      "correct": "B"
    },
    {
      "question": "Which is a noun?",
      "options": {
        "A": "Run",
        "B": "Blue",
        "C": "Happiness",
        "D": "Quickly"
      },
      "correct": "C"
    },
    {
      "question": "Which is a verb?",
      "options": {
        "A": "Beautiful",
        "B": "Sing",
        "C": "Hard",
        "D": "Happiness"
      },
      "correct": "B"
    },
    {
      "question": "Choose the antonym of 'Fast'.",
      "options": {
        "A": "Slow",
        "B": "Speed",
        "C": "Rapid",
        "D": "Swift"
      },
      "correct": "A"
    },
    {
      "question": "Choose the correctly punctuated sentence.",
      "options": {
        "A": "Lets eat, Grandma.",
        "B": "Lets, eat Grandma.",
        "C": "Let's eat Grandma.",
        "D": "Let's eat, Grandma."
      },
      "correct": "D"
    },
    {
      "question": "Identify the adjective: 'She wore a red dress.'",
      "options": {
        "A": "She",
        "B": "Wore",
        "C": "Red",
        "D": "Dress"
      },
      "correct": "C"
    },
    {
      "question": "Which sentence is in past tense?",
      "options": {
        "A": "He runs fast.",
        "B": "He will run fast.",
        "C": "He ran fast.",
        "D": "He is running fast."
      },
      "correct": "C"
    },
    {
      "question": "Which word is a conjunction?",
      "options": {
        "A": "And",
        "B": "Quickly",
        "C": "Beautiful",
        "D": "Apple"
      },
      "correct": "A"
    },
    {
      "question": "What is the plural of 'child'?",
      "options": {
        "A": "Childs",
        "B": "Children",
        "C": "Childes",
        "D": "Childern"
      },
      "correct": "B"
    }
  ],
        'created': datetime.now().isoformat(),
        'active': True
    }
    
    exams["BIO001"] = sample_exam_1
    
    # Create second sample exam
    sample_exam_code_2 = generate_exam_code()
    sample_exam_2 = {
        'code': "BIO002",
        'title': 'Bio-Science Entrance Exam 2',
        'duration': 50,
        'questions':  [
    {
      "question": "Which plant hormone is responsible for cell elongation?",
      "options": {
        "A": "Cytokinin",
        "B": "Auxin",
        "C": "Gibberellin",
        "D": "Ethylene"
      },
      "correct": "B"
    },
    {
      "question": "Kranz anatomy is characteristic of which type of plants?",
      "options": {
        "A": "C3 plants",
        "B": "CAM plants",
        "C": "C4 plants",
        "D": "Legumes"
      },
      "correct": "C"
    },
    {
      "question": "Which of the following is not part of the xylem tissue?",
      "options": {
        "A": "Tracheids",
        "B": "Vessels",
        "C": "Sieve tubes",
        "D": "Xylem parenchyma"
      },
      "correct": "C"
    },
    {
      "question": "During photorespiration, the oxygenation of RuBP takes place in:",
      "options": {
        "A": "Chloroplast",
        "B": "Peroxisome",
        "C": "Mitochondria",
        "D": "Cytosol"
      },
      "correct": "A"
    },
    {
      "question": "Which of the following is a C3 plant?",
      "options": {
        "A": "Maize",
        "B": "Sugarcane",
        "C": "Wheat",
        "D": "Sorghum"
      },
      "correct": "C"
    },
    {
      "question": "Which enzyme is responsible for nitrogen fixation in root nodules?",
      "options": {
        "A": "Nitrate reductase",
        "B": "Nitrogenase",
        "C": "Nitrite reductase",
        "D": "Aminase"
      },
      "correct": "B"
    },
    {
      "question": "Which pigment is present in red algae?",
      "options": {
        "A": "Chlorophyll a",
        "B": "Chlorophyll b",
        "C": "Phycoerythrin",
        "D": "Phycocyanin"
      },
      "correct": "C"
    },
    {
      "question": "Double fertilization is a characteristic feature of:",
      "options": {
        "A": "Gymnosperms",
        "B": "Algae",
        "C": "Bryophytes",
        "D": "Angiosperms"
      },
      "correct": "D"
    },
    {
      "question": "Casparian strip is found in:",
      "options": {
        "A": "Cortex",
        "B": "Pericycle",
        "C": "Endodermis",
        "D": "Epidermis"
      },
      "correct": "C"
    },
    {
      "question": "Which element is essential for chlorophyll synthesis?",
      "options": {
        "A": "Iron",
        "B": "Magnesium",
        "C": "Potassium",
        "D": "Calcium"
      },
      "correct": "B"
    },

    {
      "question": "Which phylum includes animals with a notochord?",
      "options": {
        "A": "Arthropoda",
        "B": "Chordata",
        "C": "Mollusca",
        "D": "Echinodermata"
      },
      "correct": "B"
    },
    {
      "question": "Which animal is an example of hermaphroditism?",
      "options": {
        "A": "Earthworm",
        "B": "Frog",
        "C": "Cockroach",
        "D": "Starfish"
      },
      "correct": "A"
    },
    {
      "question": "Which blood cells are primarily involved in clotting?",
      "options": {
        "A": "Leukocytes",
        "B": "Erythrocytes",
        "C": "Platelets",
        "D": "Macrophages"
      },
      "correct": "C"
    },
    {
      "question": "Which of these is a marsupial?",
      "options": {
        "A": "Kangaroo",
        "B": "Elephant",
        "C": "Tiger",
        "D": "Horse"
      },
      "correct": "A"
    },
    {
      "question": "The heart of a frog has how many chambers?",
      "options": {
        "A": "2",
        "B": "3",
        "C": "4",
        "D": "5"
      },
      "correct": "B"
    },
    {
      "question": "Which organ in humans produces insulin?",
      "options": {
        "A": "Liver",
        "B": "Pancreas",
        "C": "Kidney",
        "D": "Thyroid"
      },
      "correct": "B"
    },
    {
      "question": "Birds belong to which class?",
      "options": {
        "A": "Amphibia",
        "B": "Mammalia",
        "C": "Reptilia",
        "D": "Aves"
      },
      "correct": "D"
    },
    {
      "question": "Which structure is responsible for sound detection in humans?",
      "options": {
        "A": "Cochlea",
        "B": "Retina",
        "C": "Olfactory bulb",
        "D": "Semicircular canals"
      },
      "correct": "A"
    },
    {
      "question": "Which is the largest gland in the human body?",
      "options": {
        "A": "Pancreas",
        "B": "Liver",
        "C": "Thyroid",
        "D": "Adrenal"
      },
      "correct": "B"
    },
    {
      "question": "What is the function of hemoglobin?",
      "options": {
        "A": "Transport oxygen",
        "B": "Transport carbon dioxide",
        "C": "Fight infection",
        "D": "Help in clotting"
      },
      "correct": "A"
    },

    {
      "question": "Which force keeps planets in orbit around the sun?",
      "options": {
        "A": "Magnetic force",
        "B": "Gravitational force",
        "C": "Electrostatic force",
        "D": "Nuclear force"
      },
      "correct": "B"
    },
    {
      "question": "What is the unit of electric current?",
      "options": {
        "A": "Volt",
        "B": "Ohm",
        "C": "Ampere",
        "D": "Watt"
      },
      "correct": "C"
    },
    {
      "question": "The phenomenon of total internal reflection occurs in:",
      "options": {
        "A": "Convex lens",
        "B": "Concave lens",
        "C": "Optical fiber",
        "D": "Prism"
      },
      "correct": "C"
    },
    {
      "question": "Which particle has no electric charge?",
      "options": {
        "A": "Proton",
        "B": "Electron",
        "C": "Neutron",
        "D": "Positron"
      },
      "correct": "C"
    },
    {
      "question": "The SI unit of frequency is:",
      "options": {
        "A": "Hertz",
        "B": "Joule",
        "C": "Newton",
        "D": "Tesla"
      },
      "correct": "A"
    },
    {
      "question": "Which law states that pressure applied to a confined fluid is transmitted equally in all directions?",
      "options": {
        "A": "Boyle's law",
        "B": "Pascal's law",
        "C": "Archimedes' principle",
        "D": "Newton's second law"
      },
      "correct": "B"
    },
    {
      "question": "The speed of light in vacuum is approximately:",
      "options": {
        "A": "3 × 10^6 m/s",
        "B": "3 × 10^8 m/s",
        "C": "3 × 10^10 m/s",
        "D": "3 × 10^12 m/s"
      },
      "correct": "B"
    },
    {
      "question": "Which gas is used in fluorescent tubes?",
      "options": {
        "A": "Neon",
        "B": "Argon",
        "C": "Helium",
        "D": "Xenon"
      },
      "correct": "B"
    },
    {
      "question": "Which is a strong acid?",
      "options": {
        "A": "Acetic acid",
        "B": "Sulfuric acid",
        "C": "Formic acid",
        "D": "Citric acid"
      },
      "correct": "B"
    },
    {
      "question": "What is the molecular formula of glucose?",
      "options": {
        "A": "C6H12O6",
        "B": "C2H5OH",
        "C": "CH4",
        "D": "C12H22O11"
      },
      "correct": "A"
    },
    {
      "question": "Which gas is liberated when an acid reacts with a carbonate?",
      "options": {
        "A": "Oxygen",
        "B": "Carbon dioxide",
        "C": "Hydrogen",
        "D": "Nitrogen"
      },
      "correct": "B"
    },
    {
      "question": "Which element is known as 'King of Chemicals'?",
      "options": {
        "A": "Sulfuric acid",
        "B": "Hydrochloric acid",
        "C": "Nitric acid",
        "D": "Acetic acid"
      },
      "correct": "A"
    },
    {
      "question": "What is the pH of pure water?",
      "options": {
        "A": "7",
        "B": "1",
        "C": "14",
        "D": "0"
      },
      "correct": "A"
    },

    {
      "question": "Identify the correct sentence:",
      "options": {
        "A": "She don't like apples.",
        "B": "He does not likes apples.",
        "C": "They are going to the market.",
        "D": "I has a new book."
      },
      "correct": "C"
    },
    {
      "question": "Choose the correct synonym of 'Abundant':",
      "options": {
        "A": "Scarce",
        "B": "Plentiful",
        "C": "Rare",
        "D": "Sparse"
      },
      "correct": "B"
    },
    {
      "question": "Select the correctly spelled word:",
      "options": {
        "A": "Accomodate",
        "B": "Acommodate",
        "C": "Accommodate",
        "D": "Acomodate"
      },
      "correct": "C"
    },
    {
      "question": "Choose the antonym of 'Benevolent':",
      "options": {
        "A": "Kind",
        "B": "Cruel",
        "C": "Generous",
        "D": "Helpful"
      },
      "correct": "B"
    },
    {
      "question": "Fill in the blank: She ___ to the store yesterday.",
      "options": {
        "A": "go",
        "B": "goes",
        "C": "went",
        "D": "gone"
      },
      "correct": "C"
    },
    {
      "question": "Identify the part of speech of the underlined word: 'She runs fast.'",
      "options": {
        "A": "Noun",
        "B": "Verb",
        "C": "Adjective",
        "D": "Adverb"
      },
      "correct": "B"
    },
    {
      "question": "Choose the correct preposition: He is interested ___ science.",
      "options": {
        "A": "at",
        "B": "in",
        "C": "on",
        "D": "for"
      },
      "correct": "B"
    },
    {
      "question": "Select the correctly punctuated sentence:",
      "options": {
        "A": "Lets eat, Grandma!",
        "B": "Let's eat Grandma!",
        "C": "Lets eat Grandma!",
        "D": "Let's eat, Grandma!"
      },
      "correct": "D"
    },
    {
      "question": "Choose the correct form: 'I have ___ my homework.'",
      "options": {
        "A": "do",
        "B": "did",
        "C": "done",
        "D": "doing"
      },
      "correct": "C"
    },
    {
    "question": "Which pigment helps in photosynthesis and gives plants their green color?",
    "options": {
      "A": "Carotenoid",
      "B": "Chlorophyll",
      "C": "Xanthophyll",
      "D": "Anthocyanin"
    },
    "correct": "B"
  },
  {
    "question": "Which part of the brain controls balance and coordination?",
    "options": {
      "A": "Cerebrum",
      "B": "Medulla",
      "C": "Cerebellum",
      "D": "Hypothalamus"
    },
    "correct": "C"
  },
  {
    "question": "What is the SI unit of force?",
    "options": {
      "A": "Newton",
      "B": "Joule",
      "C": "Pascal",
      "D": "Watt"
    },
    "correct": "A"
  },
  {
    "question": "Which of the following is a noble gas?",
    "options": {
      "A": "Oxygen",
      "B": "Nitrogen",
      "C": "Argon",
      "D": "Hydrogen"
    },
    "correct": "C"
  },
  {
    "question": "Identify the adverb in the sentence: 'She sings beautifully.'",
    "options": {
      "A": "She",
      "B": "Sings",
      "C": "Beautifully",
      "D": "None"
    },
    "correct": "C"
  },
  {
    "question": "The process of converting a solid directly into a gas is called:",
    "options": {
      "A": "Condensation",
      "B": "Sublimation",
      "C": "Evaporation",
      "D": "Deposition"
    },
    "correct": "B"
  },
  {
    "question": "Which element is most abundant in the Earth's crust?",
    "options": {
      "A": "Oxygen",
      "B": "Silicon",
      "C": "Aluminium",
      "D": "Iron"
    },
    "correct": "A"
  },
  {
    "question": "Choose the correct form of the verb: 'They ___ to the gym every day.'",
    "options": {
      "A": "go",
      "B": "goes",
      "C": "gone",
      "D": "going"
    },
    "correct": "A"
  }
  ],
        'created': datetime.now().isoformat(),
        'active': True
    }
    
    exams["BIO002"] = sample_exam_2
    sample_exam_code_3 = generate_exam_code()
    sample_exam_3 = {
        'code': "BIO003",
        'title': 'Bio-Science Entrance Exam 3',
        'duration': 50,
        'questions':  [
    {
      "question": "What is the primary advantage of CAM photosynthesis in desert plants?",
      "options": {
        "A": "Higher oxygen production",
        "B": "Water conservation during photosynthesis",
        "C": "Faster growth rate",
        "D": "Increased chlorophyll production"
      },
      "correct": "B"
    },
    {
      "question": "Which vitamin is synthesized in the green parts of plants?",
      "options": {
        "A": "Vitamin A",
        "B": "Vitamin B12",
        "C": "Vitamin C",
        "D": "Vitamin D"
      },
      "correct": "C"
    },
    {
      "question": "In plants, phloem transports:",
      "options": {
        "A": "Water and minerals",
        "B": "Sugars and organic nutrients",
        "C": "Oxygen",
        "D": "Carbon dioxide"
      },
      "correct": "B"
    },
    {
      "question": "Which hormone is responsible for seed dormancy in plants?",
      "options": {
        "A": "Gibberellin",
        "B": "Cytokinin",
        "C": "Abscisic acid",
        "D": "Auxin"
      },
      "correct": "C"
    },
    {
      "question": "What structure in the plant cell is responsible for photosynthesis?",
      "options": {
        "A": "Mitochondria",
        "B": "Chloroplast",
        "C": "Ribosome",
        "D": "Golgi apparatus"
      },
      "correct": "B"
    },
    {
      "question": "Which pigment is NOT directly involved in the light reaction of photosynthesis?",
      "options": {
        "A": "Chlorophyll a",
        "B": "Chlorophyll b",
        "C": "Carotenoids",
        "D": "Xanthophyllase"
      },
      "correct": "D"
    },
    {
      "question": "What is the main component of the plant cell wall?",
      "options": {
        "A": "Cellulose",
        "B": "Chitin",
        "C": "Peptidoglycan",
        "D": "Lignin"
      },
      "correct": "A"
    },
    {
      "question": "Which part of a seed develops into the shoot system?",
      "options": {
        "A": "Radicle",
        "B": "Plumule",
        "C": "Endosperm",
        "D": "Cotyledon"
      },
      "correct": "B"
    },
    {
      "question": "What is the function of root hairs in plants?",
      "options": {
        "A": "Photosynthesis",
        "B": "Water absorption",
        "C": "Reproduction",
        "D": "Support"
      },
      "correct": "B"
    },
    {
      "question": "Which type of plant tissue provides mechanical support?",
      "options": {
        "A": "Parenchyma",
        "B": "Collenchyma",
        "C": "Sclerenchyma",
        "D": "Xylem"
      },
      "correct": "C"
    },

    
    {
      "question": "What is the primary function of the notochord in chordates?",
      "options": {
        "A": "Digest food",
        "B": "Provide skeletal support",
        "C": "Filter blood",
        "D": "Respiration"
      },
      "correct": "B"
    },
    {
      "question": "Which blood cells are primarily responsible for oxygen transport in humans?",
      "options": {
        "A": "White blood cells",
        "B": "Platelets",
        "C": "Red blood cells",
        "D": "Lymphocytes"
      },
      "correct": "C"
    },
    {
      "question": "In vertebrates, which organ produces insulin?",
      "options": {
        "A": "Liver",
        "B": "Pancreas",
        "C": "Kidney",
        "D": "Spleen"
      },
      "correct": "B"
    },
    {
      "question": "Which part of the nephron is responsible for ultrafiltration?",
      "options": {
        "A": "Proximal convoluted tubule",
        "B": "Glomerulus",
        "C": "Loop of Henle",
        "D": "Distal convoluted tubule"
      },
      "correct": "B"
    },
    {
      "question": "What type of symmetry is found in starfish?",
      "options": {
        "A": "Bilateral",
        "B": "Radial",
        "C": "Asymmetry",
        "D": "Spherical"
      },
      "correct": "B"
    },
    {
      "question": "Which hormone regulates molting in arthropods?",
      "options": {
        "A": "Ecdysone",
        "B": "Testosterone",
        "C": "Estrogen",
        "D": "Adrenaline"
      },
      "correct": "A"
    },
    {
      "question": "The primary site of gas exchange in insects is:",
      "options": {
        "A": "Lungs",
        "B": "Tracheae",
        "C": "Gills",
        "D": "Skin"
      },
      "correct": "B"
    },
    {
      "question": "Which nervous system division controls voluntary movements?",
      "options": {
        "A": "Autonomic nervous system",
        "B": "Central nervous system",
        "C": "Somatic nervous system",
        "D": "Peripheral nervous system"
      },
      "correct": "C"
    },
    {
      "question": "Which part of the brain is responsible for regulating heartbeat and breathing?",
      "options": {
        "A": "Cerebrum",
        "B": "Medulla oblongata",
        "C": "Cerebellum",
        "D": "Hypothalamus"
      },
      "correct": "B"
    },
    {
      "question": "Which class of animals are warm-blooded and have hair or fur?",
      "options": {
        "A": "Amphibia",
        "B": "Reptilia",
        "C": "Mammalia",
        "D": "Aves"
      },
      "correct": "C"
    },

    
    {
      "question": "According to Heisenberg's uncertainty principle, which two properties cannot be simultaneously measured with arbitrary precision?",
      "options": {
        "A": "Position and energy",
        "B": "Momentum and energy",
        "C": "Position and momentum",
        "D": "Time and velocity"
      },
      "correct": "C"
    },
    {
      "question": "What is the principle behind the working of a cyclotron?",
      "options": {
        "A": "Magnetic deflection of charged particles",
        "B": "Acceleration of charged particles using a constant magnetic field and an alternating electric field",
        "C": "Acceleration by gravitational field",
        "D": "Reflection of particles by mirrors"
      },
      "correct": "B"
    },
    {
      "question": "Which of the following is a scalar quantity?",
      "options": {
        "A": "Velocity",
        "B": "Displacement",
        "C": "Force",
        "D": "Energy"
      },
      "correct": "D"
    },
    {
      "question": "What happens to the capacitance of a parallel plate capacitor if the distance between the plates is doubled?",
      "options": {
        "A": "It doubles",
        "B": "It halves",
        "C": "It remains the same",
        "D": "It quadruples"
      },
      "correct": "B"
    },
    {
      "question": "In an ideal gas, which of the following remains constant during an isothermal process?",
      "options": {
        "A": "Pressure",
        "B": "Volume",
        "C": "Temperature",
        "D": "Internal energy"
      },
      "correct": "C"
    },
    {
      "question": "What is the SI unit of magnetic flux?",
      "options": {
        "A": "Tesla",
        "B": "Weber",
        "C": "Gauss",
        "D": "Ampere"
      },
      "correct": "B"
    },
    {
      "question": "Which phenomenon explains the bending of light when passing through a prism?",
      "options": {
        "A": "Reflection",
        "B": "Diffraction",
        "C": "Refraction",
        "D": "Interference"
      },
      "correct": "C"
    },
    {
      "question": "The half-life of a radioactive substance is 5 hours. After 15 hours, what fraction of the substance remains?",
      "options": {
        "A": "1/2",
        "B": "1/4",
        "C": "1/8",
        "D": "1/16"
      },
      "correct": "C"
    },
    {
      "question": "Which of the following quantities is a vector?",
      "options": {
        "A": "Work",
        "B": "Speed",
        "C": "Acceleration",
        "D": "Temperature"
      },
      "correct": "C"
    },
    {
      "question": "What does the slope of a velocity-time graph represent?",
      "options": {
        "A": "Displacement",
        "B": "Acceleration",
        "C": "Velocity",
        "D": "Jerk"
      },
      "correct": "B"
    },

    
    {
      "question": "What is the hybridization of sulfur in SF6?",
      "options": {
        "A": "sp3",
        "B": "sp3d",
        "C": "sp3d2",
        "D": "sp2"
      },
      "correct": "C"
    },
    {
      "question": "Le Chatelier's principle predicts that increasing pressure on a reaction favors:",
      "options": {
        "A": "Side with more gas molecules",
        "B": "Side with fewer gas molecules",
        "C": "No effect",
        "D": "Endothermic reactions only"
      },
      "correct": "B"
    },
    {
      "question": "Which acid is found in vinegar?",
      "options": {
        "A": "Hydrochloric acid",
        "B": "Acetic acid",
        "C": "Sulfuric acid",
        "D": "Citric acid"
      },
      "correct": "B"
    },
    {
      "question": "Which of the following is a strong oxidizing agent?",
      "options": {
        "A": "KMnO4 (in acidic medium)",
        "B": "NaCl",
        "C": "H2",
        "D": "CO2"
      },
      "correct": "A"
    },
    {
      "question": "What is the IUPAC name for CH3CH2OH?",
      "options": {
        "A": "Methanol",
        "B": "Ethanol",
        "C": "Ethane",
        "D": "Methane"
      },
      "correct": "B"
    },
    {
      "question": "What type of bond is present in N2 molecule?",
      "options": {
        "A": "Single covalent bond",
        "B": "Double covalent bond",
        "C": "Triple covalent bond",
        "D": "Ionic bond"
      },
      "correct": "C"
    },
    {
      "question": "Which element has the highest electronegativity?",
      "options": {
        "A": "Oxygen",
        "B": "Fluorine",
        "C": "Nitrogen",
        "D": "Chlorine"
      },
      "correct": "B"
    },
    {
      "question": "Which gas is evolved when an acid reacts with a carbonate?",
      "options": {
        "A": "Oxygen",
        "B": "Carbon dioxide",
        "C": "Hydrogen",
        "D": "Nitrogen"
      },
      "correct": "B"
    },
    {
      "question": "What is the pH of a neutral solution at 25°C?",
      "options": {
        "A": "0",
        "B": "7",
        "C": "14",
        "D": "1"
      },
      "correct": "B"
    },
    {
      "question": "Which law relates volume and pressure of a gas at constant temperature?",
      "options": {
        "A": "Boyle's Law",
        "B": "Charles's Law",
        "C": "Gay-Lussac's Law",
        "D": "Avogadro's Law"
      },
      "correct": "A"
    },

    
    {
      "question": "Identify the figure of speech: 'The wind whispered through the trees.'",
      "options": {
        "A": "Simile",
        "B": "Metaphor",
        "C": "Personification",
        "D": "Alliteration"
      },
      "correct": "C"
    },
    {
      "question": "Choose the correct sentence:",
      "options": {
        "A": 'Neither of the boys are coming.',
        "B": 'Neither of the boys is coming.',
        "C": 'Neither of the boys were coming.',
        "D": 'Neither of the boys have come.'
      },
      "correct": "B"
    },
    {
      "question": "Select the correct passive voice form: 'They will finish the project soon.'",
      "options": {
        "A": 'The project will be finished soon.',
        "B": 'The project is finished soon.',
        "C": 'The project has been finished soon.',
        "D": 'The project was finishing soon.'
      },
      "correct": "A"
    },
    {
      "question": "Which word is a synonym of 'Abundant'?",
      "options": {
        "A": "Scarce",
        "B": "Plentiful",
        "C": "Sparse",
        "D": "Rare"
      },
      "correct": "B"
    },
    {
      "question": "Choose the correctly punctuated sentence:",
      "options": {
        "A": "It's raining; let's stay inside.",
        "B": "Its raining, let's stay inside.",
        "C": "Its raining; let's stay inside.",
        "D": "It's raining, let's stay inside."
      },
      "correct": "A"
    },
    {
      "question": "Select the word that best completes the sentence: 'She has a very ___ attitude towards learning.'",
      "options": {
        "A": "apathetic",
        "B": "enthusiastic",
        "C": "indifferent",
        "D": "negligent"
      },
      "correct": "B"
    },
    {
      "question": "Choose the correct verb form: 'If I ___ you, I would apologize.'",
      "options": {
        "A": "was",
        "B": "were",
        "C": "am",
        "D": "be"
      },
      "correct": "B"
    },
    {
      "question": "Identify the error in the sentence: 'Each of the players have a unique skill.'",
      "options": {
        "A": "Each",
        "B": "players",
        "C": "have",
        "D": "unique"
      },
      "correct": "C"
    },
    {
      "question": "What is the meaning of the idiom 'Break the ice'?",
      "options": {
        "A": "To freeze something",
        "B": "To start a conversation",
        "C": "To cause trouble",
        "D": "To end a relationship"
      },
      "correct": "B"
    },
    {
      "question": "Choose the correct preposition: 'She is keen ___ music.'",
      "options": {
        "A": "on",
        "B": "at",
        "C": "in",
        "D": "for"
      },
      "correct": "A"
    }
  ],
        'created': datetime.now().isoformat(),
        'active': True
    }
    
    exams["BIO003"] = sample_exam_3
    sample_exam_code_3 = generate_exam_code()
    sample_exam_4 = {
        'code': "MAT001",
        'title': 'MAT-Science Entrance Exam 1',
        'duration': 50,
        'questions':  [
    {
      "question": "If f(x) = ln(x^2 + 1), what is f''(x)?",
      "options": {
        "A": "(2 - 2x^2)/(x^2 + 1)^2",
        "B": "2x/(x^2 + 1)",
        "C": "2(x^2 - 1)/(x^2 + 1)^2",
        "D": "(2x^2 - 2)/(x^2 + 1)^2"
      }
    },
    {
      "question": "Evaluate the limit: limₓ→0 (sin(3x)/x)",
      "options": {
        "A": "0",
        "B": "1",
        "C": "3",
        "D": "Undefined"
      }
    },
    {
      "question": "The matrix A has eigenvalues 3 and 5. What is the determinant of A?",
      "options": {
        "A": "8",
        "B": "15",
        "C": "0",
        "D": "2"
      }
    },
    {
      "question": "If ∫x·e^x dx = x·e^x - ∫e^x dx, then what is ∫x·e^x dx?",
      "options": {
        "A": "x·e^x - e^x + C",
        "B": "x·e^x + e^x + C",
        "C": "x·e^x - ln|x| + C",
        "D": "x·e^x + ln|x| + C"
      }
    },
    {
      "question": "Solve: ∑ (k=1 to n) k^2",
      "options": {
        "A": "n(n + 1)/2",
        "B": "n(n + 1)(2n + 1)/6",
        "C": "n^2(n + 1)/2",
        "D": "n(n - 1)/2"
      }
    },

    {
      "question": "A ball is projected at 60° with velocity 30 m/s. What is the max height?",
      "options": {
        "A": "34.4 m",
        "B": "44.6 m",
        "C": "22.9 m",
        "D": "14.2 m"
      }
    },
    {
      "question": "What is the dimensional formula of impulse?",
      "options": {
        "A": "MLT^-1",
        "B": "ML^2T^-2",
        "C": "MLT^-2",
        "D": "ML^2T^-1"
      }
    },
    {
      "question": "Which law explains the relation between pressure and volume at constant temperature?",
      "options": {
        "A": "Boyle’s Law",
        "B": "Charles’ Law",
        "C": "Avogadro’s Law",
        "D": "Newton's Law"
      }
    },
    {
      "question": "Which of these represents simple harmonic motion?",
      "options": {
        "A": "x = A sin(ωt)",
        "B": "x = A tan(ωt)",
        "C": "x = A t^2",
        "D": "x = A e^(−ωt)"
      }
    },
    {
      "question": "In Young’s double slit experiment, the fringe width increases if:",
      "options": {
        "A": "Slit separation increases",
        "B": "Screen distance increases",
        "C": "Wavelength decreases",
        "D": "Light intensity increases"
      }
    },

    {
      "question": "Which element has the highest ionization energy?",
      "options": {
        "A": "He",
        "B": "Ne",
        "C": "F",
        "D": "Ar"
      }
    },
    {
      "question": "Which is NOT a postulate of Dalton’s atomic theory?",
      "options": {
        "A": "Atoms are indivisible",
        "B": "Atoms of same element are identical",
        "C": "Atoms can be created or destroyed",
        "D": "Atoms combine in simple ratios"
      }
    },
    {
      "question": "What is the hybridization of the central atom in SF₆?",
      "options": {
        "A": "sp³d",
        "B": "sp³d²",
        "C": "sp³",
        "D": "sp²"
      }
    },
    {
      "question": "Which compound shows resonance?",
      "options": {
        "A": "CH₄",
        "B": "CO₂",
        "C": "O₃",
        "D": "H₂O"
      }
    },
    {
      "question": "pH of 0.01 M HCl is approximately:",
      "options": {
        "A": "2",
        "B": "1",
        "C": "3",
        "D": "0.01"
      }
    },

    {
      "question": "What is the output of: `print('A' + str(1 + 2))`",
      "options": {
        "A": "A3",
        "B": "A1+2",
        "C": "A12",
        "D": "Error"
      }
    },
    {
      "question": "What does Big-O notation describe?",
      "options": {
        "A": "Runtime efficiency",
        "B": "Memory usage",
        "C": "Compilation time",
        "D": "Syntax errors"
      }
    },
    {
      "question": "Which is **not** a characteristic of OOP?",
      "options": {
        "A": "Encapsulation",
        "B": "Inheritance",
        "C": "Polymorphism",
        "D": "Recursion"
      }
    },
    {
      "question": "Which data structure uses FIFO?",
      "options": {
        "A": "Stack",
        "B": "Queue",
        "C": "Tree",
        "D": "Graph"
      }
    },
    {
      "question": "Time complexity of binary search is:",
      "options": {
        "A": "O(n)",
        "B": "O(log n)",
        "C": "O(n log n)",
        "D": "O(1)"
      }
    },

    {
      "question": "Identify the figure of speech: \"The wind whispered through the trees.\"",
      "options": {
        "A": "Simile",
        "B": "Personification",
        "C": "Metaphor",
        "D": "Alliteration"
      }
    },
    {
      "question": "Which sentence is grammatically correct?",
      "options": {
        "A": "He don’t know nothing.",
        "B": "He doesn’t know anything.",
        "C": "He don’t knows nothing.",
        "D": "He doesn’t knows anything."
      }
    },
    {
      "question": "Choose the best synonym for 'obfuscate':",
      "options": {
        "A": "Clarify",
        "B": "Complicate",
        "C": "Hide",
        "D": "Confuse"
      }
    },
    {
      "question": "Choose the word that best completes the sentence: She was _____ by the unexpected question.",
      "options": {
        "A": "elated",
        "B": "confounded",
        "C": "articulated",
        "D": "sustained"
      }
    },
    {
      "question": "What is the antonym of 'ephemeral'?",
      "options": {
        "A": "Brief",
        "B": "Eternal",
        "C": "Fleeting",
        "D": "Transitory"
      }
    }
        ,
    {
      "question": "Solve for x: log₂(x^2 - 5x + 6) = 1",
      "options": {
        "A": "x = 2 or 3",
        "B": "x = 1 or 6",
        "C": "x = 3 or 4",
        "D": "x = 1 or 5"
      }
    },
    {
      "question": "If sin(x) + cos(x) = √2, what is sin(2x)?",
      "options": {
        "A": "1",
        "B": "√2",
        "C": "0",
        "D": "-1"
      }
    },
    {
      "question": "The area under y = x² from x = 1 to 3 is:",
      "options": {
        "A": "26/3",
        "B": "9",
        "C": "8",
        "D": "10"
      }
    },
    {
      "question": "Which conic section is defined by the equation x² - y² = 1?",
      "options": {
        "A": "Circle",
        "B": "Ellipse",
        "C": "Parabola",
        "D": "Hyperbola"
      }
    },
    {
      "question": "The general solution of dy/dx = ky is:",
      "options": {
        "A": "y = Ce^(kx)",
        "B": "y = kx + C",
        "C": "y = ln(kx)",
        "D": "y = C/k"
      }
    },

    {
      "question": "Which law governs the reflection of light?",
      "options": {
        "A": "Snell's Law",
        "B": "Newton's Second Law",
        "C": "Law of Reflection",
        "D": "Kirchhoff’s Law"
      }
    },
    {
      "question": "Which physical quantity has the unit of Tesla?",
      "options": {
        "A": "Magnetic field",
        "B": "Electric current",
        "C": "Voltage",
        "D": "Resistance"
      }
    },
    {
      "question": "A transformer works on which principle?",
      "options": {
        "A": "Conservation of charge",
        "B": "Electromagnetic induction",
        "C": "Heat conduction",
        "D": "Photoelectric effect"
      }
    },
    {
      "question": "Which of the following particles is not affected by electric field?",
      "options": {
        "A": "Electron",
        "B": "Proton",
        "C": "Neutron",
        "D": "Alpha particle"
      }
    },
    {
      "question": "Which one has the highest refractive index?",
      "options": {
        "A": "Air",
        "B": "Water",
        "C": "Glass",
        "D": "Diamond"
      }
    },

    {
      "question": "Which compound does not exhibit hydrogen bonding?",
      "options": {
        "A": "NH₃",
        "B": "HF",
        "C": "CH₄",
        "D": "H₂O"
      }
    },
    {
      "question": "What is the IUPAC name of CH₃CH₂OH?",
      "options": {
        "A": "Methanol",
        "B": "Ethanol",
        "C": "Propanol",
        "D": "Butanol"
      }
    },
    {
      "question": "Which is the strongest acid?",
      "options": {
        "A": "HCl",
        "B": "H₂SO₄",
        "C": "HNO₃",
        "D": "HI"
      }
    },
    {
      "question": "What is the oxidation number of Mn in KMnO₄?",
      "options": {
        "A": "+2",
        "B": "+4",
        "C": "+7",
        "D": "+6"
      }
    },
    {
      "question": "Which of these has aromatic character?",
      "options": {
        "A": "Cyclohexane",
        "B": "Benzene",
        "C": "Ethene",
        "D": "Butyne"
      }
    },

    {
      "question": "Which keyword is used to define a function in Python?",
      "options": {
        "A": "func",
        "B": "define",
        "C": "def",
        "D": "function"
      }
    },
    {
      "question": "Which of these is not a valid Python data type?",
      "options": {
        "A": "set",
        "B": "tuple",
        "C": "array",
        "D": "dictionary"
      }
    },
    {
      "question": "Which of the following is used for comments in Python?",
      "options": {
        "A": "/* comment */",
        "B": "// comment",
        "C": "# comment",
        "D": "-- comment"
      }
    },
    {
      "question": "What is the result of 5 // 2 in Python?",
      "options": {
        "A": "2.5",
        "B": "3",
        "C": "2",
        "D": "Error"
      }
    },
    {
      "question": "Which algorithm is best for finding shortest path in graphs?",
      "options": {
        "A": "Bubble Sort",
        "B": "DFS",
        "C": "Dijkstra’s Algorithm",
        "D": "Binary Search"
      }
    },

    {
      "question": "Identify the grammatical error: \"Neither of the books are available.\"",
      "options": {
        "A": "books",
        "B": "are",
        "C": "Neither",
        "D": "available"
      }
    },
    {
      "question": "Choose the correct indirect speech: He said, \"I will go to school.\"",
      "options": {
        "A": "He said that he would go to school.",
        "B": "He said he will go to school.",
        "C": "He said that he will go school.",
        "D": "He said he would gone to school."
      }
    },
    {
      "question": "Which of these is a complex sentence?",
      "options": {
        "A": "I came, I saw, I conquered.",
        "B": "He slept early.",
        "C": "I went home because I was tired.",
        "D": "He is tall and smart."
      }
    },
    {
      "question": "Choose the best antonym for 'lucid':",
      "options": {
        "A": "Clear",
        "B": "Ambiguous",
        "C": "Bright",
        "D": "Logical"
      }
    },
    {
      "question": "Fill in the blank: The committee _____ divided in their opinions.",
      "options": {
        "A": "was",
        "B": "are",
        "C": "were",
        "D": "be"
      }
    }
 

  ],
        'created': datetime.now().isoformat(),
        'active': True
    }
        
        # Save sample data
    if save_exams(exams):
            print("Sample exams created successfully!")
    else:
            print("Failed to create sample exams.")

if __name__ == '__main__':
    # Initialize sample data on first run
    initialize_sample_data()
    
    print(f"Data will be stored in: {os.path.abspath(DATA_DIR)}")
    print("Starting Flask application with disk storage...")
    
    app.run(debug=True, host='0.0.0.0', port=5000)