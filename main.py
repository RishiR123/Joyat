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
DATA_DIR = "exam_data"
EXAMS_FILE = os.path.join(DATA_DIR, "exams.json")
RESULTS_FILE = os.path.join(DATA_DIR, "results.json")

# Default admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

# Thread lock for file operations
file_lock = threading.Lock()

# School options
SCHOOLS = [
    "School of Entrepreneurship and Management",
    "School of Engineering and Technology",
    "School of Design",
    "School of Computational Intelligence",
    "School of Arts & Natural Sciences",
    "School of Agricultural Sciences",
    "School of Law",
    "School of Life & Health Sciences",
    "School of Nursing",
    "School of Pharmacy",
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
            with open(EXAMS_FILE, "r", encoding="utf-8") as f:
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
            with open(EXAMS_FILE, "w", encoding="utf-8") as f:
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
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
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
            with open(RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving results: {e}")
        return False


def generate_exam_code():
    """Generate a random 6-character exam code"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


@app.route("/")
def index():
    """Serve the main HTML page"""
    return send_from_directory(".", "index.html")


@app.route("/admin/login", methods=["POST"])
def admin_login():
    """Handle admin login"""
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({"success": True, "message": "Login successful"})
    else:
        return jsonify({"success": False, "message": "Invalid credentials"}), 401


@app.route("/admin/create-exam", methods=["POST"])
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
        "code": exam_code,
        "title": data.get("title"),
        "duration": data.get("duration"),
        "questions": data.get("questions"),
        "created": datetime.now().isoformat(),
        "active": True,
    }

    # Validate exam data
    if not exam["title"] or not exam["questions"] or len(exam["questions"]) == 0:
        return jsonify({"success": False, "message": "Invalid exam data"}), 400

    # Validate questions
    for i, question in enumerate(exam["questions"]):
        if not all(key in question for key in ["question", "options", "correct"]):
            return (
                jsonify({"success": False, "message": f"Invalid question {i+1}"}),
                400,
            )

        if not all(option in question["options"] for option in ["A", "B", "C", "D"]):
            return (
                jsonify(
                    {"success": False, "message": f"Invalid options for question {i+1}"}
                ),
                400,
            )

        if question["correct"] not in ["A", "B", "C", "D"]:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Invalid correct answer for question {i+1}",
                    }
                ),
                400,
            )

    # Store exam
    exams[exam_code] = exam

    # Save to disk
    if not save_exams(exams):
        return jsonify({"success": False, "message": "Failed to save exam"}), 500

    return jsonify(
        {"success": True, "message": "Exam created successfully", "examCode": exam_code}
    )


@app.route("/admin/exams", methods=["GET"])
def get_exams():
    """Get all exams for admin"""
    exams = load_exams()
    exam_list = []

    for code, exam in exams.items():
        exam_info = {
            "code": code,
            "title": exam["title"],
            "duration": exam["duration"],
            "questions": exam["questions"],
            "created": exam["created"],
            "active": exam["active"],
        }
        exam_list.append(exam_info)

    # Sort by creation date (newest first)
    exam_list.sort(key=lambda x: x["created"], reverse=True)
    return jsonify(exam_list)


@app.route("/admin/results", methods=["GET"])
def get_results():
    """Get all exam results for admin"""
    results = load_results()
    # Sort results by submission date (newest first)
    sorted_results = sorted(results, key=lambda x: x["submitted"], reverse=True)
    return jsonify(sorted_results)


@app.route("/api/schools", methods=["GET"])
def get_schools():
    """Get list of available schools"""
    return jsonify(SCHOOLS)


@app.route("/student/join", methods=["POST"])
def student_join():
    """Allow student to join an exam using exam code or 'BIOJOY' for random selection"""
    data = request.get_json()
    exam_code = data.get("examCode", "").upper()
    student_name = data.get("name", "").strip()
    student_id = data.get("studentId", "").strip()
    school = data.get("school", "").strip()

    # Validate required fields
    if not exam_code or not student_name or not student_id or not school:
        return jsonify({"success": False, "message": "All fields are required"}), 400

    # Validate school selection
    if school not in SCHOOLS or school == "Select School":
        return (
            jsonify({"success": False, "message": "Please select a valid school"}),
            400,
        )

    # Validate student ID format (should be numeric and reasonable length)

    if not re.match(r"^[A-Za-z0-9-_]+$", student_id):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Student ID should contain only letters, numbers, hyphens, or underscores",
                }
            ),
            400,
        )

    # Load exams from disk
    exams = load_exams()

    # Special logic for 'BIOJOY'
    if exam_code == "BIOJOY":
        possible_codes = ["BIO005", "BIO004", "BIO003", "BIO002", "BIO001"]
        active_codes = [
            code for code in possible_codes if code in exams and exams[code]["active"]
        ]
        if not active_codes:
            return (
                jsonify(
                    {"success": False, "message": "No active biology exams available"}
                ),
                400,
            )
        exam_code = random.choice(active_codes)

    if exam_code == "COMJOY":
        possible_codes = ["COM005", "COM004", "COM003", "COM002", "COM001"]
        active_codes = [
            code for code in possible_codes if code in exams and exams[code]["active"]
        ]
        if not active_codes:
            return (
                jsonify(
                    {"success": False, "message": "No active computer exams available"}
                ),
                400,
            )
        exam_code = random.choice(active_codes)
    if exam_code == "APTJOY":
        possible_codes = ["APT003", "APT002", "APT001"]
        active_codes = [
            code for code in possible_codes if code in exams and exams[code]["active"]
        ]
        if not active_codes:
            return (
                jsonify(
                    {"success": False, "message": "No active computer exams available"}
                ),
                400,
            )
        exam_code = random.choice(active_codes)

    if exam_code not in exams:
        return jsonify({"success": False, "message": "Invalid exam code"}), 404

    exam = exams[exam_code]
    if not exam["active"]:
        return jsonify({"success": False, "message": "Exam is not active"}), 400

    # Check if student has already taken this exam
    results = load_results()
    existing_result = next(
        (
            r
            for r in results
            if r["examCode"] == exam_code and r["studentId"] == student_id
        ),
        None,
    )
    if existing_result:
        return (
            jsonify({"success": False, "message": "You have already taken this exam"}),
            400,
        )

    # Return exam data without correct answers
    exam_data = {
        "code": exam_code,
        "title": exam["title"],
        "duration": exam["duration"],
        "questions": [],
    }

    for question in exam["questions"]:
        student_question = {
            "question": question["question"],
            "options": question["options"],
        }
        exam_data["questions"].append(student_question)

    return jsonify(exam_data)


@app.route("/student/submit", methods=["POST"])
def submit_exam():
    """Handle exam submission by student"""
    data = request.get_json()
    exam_code = data.get("examCode", "").upper()
    student_name = data.get("studentName", "").strip()
    student_id = data.get("studentId", "").strip()
    school = data.get("school", "").strip()
    answers = data.get("answers", {})

    if not all([exam_code, student_name, student_id, school, answers]):
        return jsonify({"success": False, "message": "Missing required data"}), 400

    # Load exams from disk
    exams = load_exams()

    if exam_code not in exams:
        return jsonify({"success": False, "message": "Invalid exam code"}), 404

    exam = exams[exam_code]

    # Calculate score
    score = 0
    total_questions = len(exam["questions"])

    for i, question in enumerate(exam["questions"]):
        student_answer = answers.get(f"question_{i}")
        if student_answer == question["correct"]:
            score += 1

    # Create result object with additional student information
    result = {
        "examCode": exam_code,
        "examTitle": exam["title"],
        "studentName": student_name,
        "studentId": student_id,
        "school": school,
        "score": score,
        "total": total_questions,
        "percentage": round((score / total_questions) * 100, 2),
        "answers": answers,
        "submitted": datetime.now().isoformat(),
    }

    # Load current results and add new one
    results = load_results()
    results.append(result)

    # Save results to disk
    if not save_results(results):
        return jsonify({"success": False, "message": "Failed to save result"}), 500

    return jsonify(
        {
            "success": True,
            "message": "Exam submitted successfully",
            "score": score,
            "total": total_questions,
            "percentage": result["percentage"],
        }
    )


@app.route("/admin/delete-exam/<exam_code>", methods=["DELETE"])
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


@app.route("/admin/toggle-exam/<exam_code>", methods=["POST"])
def toggle_exam(exam_code):
    """Toggle exam active status (admin only)"""
    exam_code = exam_code.upper()

    # Load exams from disk
    exams = load_exams()

    if exam_code not in exams:
        return jsonify({"success": False, "message": "Exam not found"}), 404

    # Toggle active status
    exams[exam_code]["active"] = not exams[exam_code]["active"]
    status = "activated" if exams[exam_code]["active"] else "deactivated"

    # Save updated exams
    if not save_exams(exams):
        return (
            jsonify({"success": False, "message": "Failed to update exam status"}),
            500,
        )

    return jsonify(
        {
            "success": True,
            "message": f"Exam {status} successfully",
            "active": exams[exam_code]["active"],
        }
    )


@app.route("/admin/exam-details/<exam_code>", methods=["GET"])
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
    exam_results = [r for r in results if r["examCode"] == exam_code]

    # Calculate statistics
    if exam_results:
        scores = [r["score"] for r in exam_results]
        avg_score = sum(scores) / len(scores)
        max_score = max(scores)
        min_score = min(scores)
        pass_rate = (
            len([s for s in scores if s >= len(exam["questions"]) * 0.6])
            / len(scores)
            * 100
        )

        # School-wise statistics
        school_stats = {}
        for result in exam_results:
            school = result.get("school", "Unknown")
            if school not in school_stats:
                school_stats[school] = {"count": 0, "total_score": 0}
            school_stats[school]["count"] += 1
            school_stats[school]["total_score"] += result["score"]

        for school in school_stats:
            school_stats[school]["avg_score"] = round(
                school_stats[school]["total_score"] / school_stats[school]["count"], 2
            )
    else:
        avg_score = 0
        max_score = 0
        min_score = 0
        pass_rate = 0
        school_stats = {}

    return jsonify(
        {
            "exam": exam,
            "results": exam_results,
            "statistics": {
                "totalAttempts": len(exam_results),
                "averageScore": round(avg_score, 2),
                "maxScore": max_score,
                "minScore": min_score,
                "passRate": round(pass_rate, 2),
                "schoolStats": school_stats,
            },
        }
    )


@app.route("/admin/backup", methods=["GET"])
def backup_data():
    """Create a backup of all data"""
    try:
        exams = load_exams()
        results = load_results()

        backup_data = {
            "exams": exams,
            "results": results,
            "backup_date": datetime.now().isoformat(),
            "schools": SCHOOLS,
        }

        backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        backup_path = os.path.join(DATA_DIR, backup_filename)

        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        return jsonify(
            {
                "success": True,
                "message": "Backup created successfully",
                "filename": backup_filename,
            }
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Backup failed: {str(e)}"}), 500


@app.route("/admin/restore", methods=["POST"])
def restore_data():
    """Restore data from backup"""
    try:
        data = request.get_json()
        backup_filename = data.get("filename")

        if not backup_filename:
            return (
                jsonify({"success": False, "message": "Backup filename required"}),
                400,
            )

        backup_path = os.path.join(DATA_DIR, backup_filename)

        if not os.path.exists(backup_path):
            return jsonify({"success": False, "message": "Backup file not found"}), 404

        with open(backup_path, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        # Validate backup data structure
        if "exams" not in backup_data or "results" not in backup_data:
            return (
                jsonify({"success": False, "message": "Invalid backup file format"}),
                400,
            )

        # Save restored data
        if not save_exams(backup_data["exams"]):
            return (
                jsonify({"success": False, "message": "Failed to restore exams"}),
                500,
            )

        if not save_results(backup_data["results"]):
            return (
                jsonify({"success": False, "message": "Failed to restore results"}),
                500,
            )

        return jsonify({"success": True, "message": "Data restored successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Restore failed: {str(e)}"}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    exams = load_exams()
    results = load_results()

    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "exams_count": len(exams),
            "results_count": len(results),
            "storage_type": "disk",
            "data_directory": DATA_DIR,
            "schools_count": len(SCHOOLS),
        }
    )


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
        "code": "BIO001",
        "title": "Bio-Science Entrance Exam 1",
        "duration": 50,
        "questions": [
            {
                "question": "Which type of cell division reduces chromosome number by half?",
                "options": {
                    "A": "Mitosis",
                    "B": "Meiosis",
                    "C": "Binary fission",
                    "D": "Budding",
                },
                "correct": "B",
            },
            {
                "question": "The Calvin cycle occurs in which part of the chloroplast?",
                "options": {
                    "A": "Thylakoid membrane",
                    "B": "Stroma",
                    "C": "Grana",
                    "D": "Outer membrane",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is a sex-linked disorder?",
                "options": {
                    "A": "Sickle cell anemia",
                    "B": "Thalassemia",
                    "C": "Hemophilia",
                    "D": "Phenylketonuria",
                },
                "correct": "C",
            },
            {
                "question": "The enzyme that unwinds DNA during replication is:",
                "options": {
                    "A": "DNA polymerase",
                    "B": "DNA ligase",
                    "C": "Helicase",
                    "D": "Primase",
                },
                "correct": "C",
            },
            {
                "question": "Which plant tissue is responsible for secondary growth?",
                "options": {
                    "A": "Apical meristem",
                    "B": "Lateral meristem",
                    "C": "Ground tissue",
                    "D": "Dermal tissue",
                },
                "correct": "B",
            },
            {
                "question": "The site of protein synthesis in a cell is:",
                "options": {
                    "A": "Nucleus",
                    "B": "Mitochondria",
                    "C": "Ribosome",
                    "D": "Golgi apparatus",
                },
                "correct": "C",
            },
            {
                "question": "Which hormone regulates blood glucose levels?",
                "options": {
                    "A": "Thyroxine",
                    "B": "Insulin",
                    "C": "Adrenaline",
                    "D": "Growth hormone",
                },
                "correct": "B",
            },
            {
                "question": "The phospholipid bilayer is a component of:",
                "options": {
                    "A": "Cell wall",
                    "B": "Cell membrane",
                    "C": "Cytoplasm",
                    "D": "Nuclear envelope only",
                },
                "correct": "B",
            },
            {
                "question": "Which process converts atmospheric nitrogen into ammonia?",
                "options": {
                    "A": "Nitrification",
                    "B": "Denitrification",
                    "C": "Nitrogen fixation",
                    "D": "Ammonification",
                },
                "correct": "C",
            },
            {
                "question": "The term 'biodiversity hotspot' refers to regions with:",
                "options": {
                    "A": "High temperature",
                    "B": "High species richness and endemism",
                    "C": "High altitude",
                    "D": "High rainfall",
                },
                "correct": "B",
            },
            {
                "question": "Which quantum number determines the shape of an orbital?",
                "options": {
                    "A": "Principal quantum number (n)",
                    "B": "Azimuthal quantum number (l)",
                    "C": "Magnetic quantum number (m)",
                    "D": "Spin quantum number (s)",
                },
                "correct": "B",
            },
            {
                "question": "The hybridization of carbon in methane (CH4) is:",
                "options": {"A": "sp", "B": "sp2", "C": "sp3", "D": "sp3d"},
                "correct": "C",
            },
            {
                "question": "Which of the following exhibits hydrogen bonding?",
                "options": {"A": "HCl", "B": "H2O", "C": "CH4", "D": "CO2"},
                "correct": "B",
            },
            {
                "question": "The IUPAC name of CH3-CH2-CHO is:",
                "options": {
                    "A": "Propanal",
                    "B": "Propanone",
                    "C": "Propanoic acid",
                    "D": "Propanol",
                },
                "correct": "A",
            },
            {
                "question": "Which catalyst is used in the Haber process?",
                "options": {
                    "A": "Platinum",
                    "B": "Iron",
                    "C": "Nickel",
                    "D": "Vanadium pentoxide",
                },
                "correct": "B",
            },
            {
                "question": "The oxidation state of chromium in K2Cr2O7 is:",
                "options": {"A": "+3", "B": "+6", "C": "+7", "D": "+2"},
                "correct": "B",
            },
            {
                "question": "Which type of isomerism is exhibited by [Co(NH3)4Cl2]+?",
                "options": {
                    "A": "Optical isomerism",
                    "B": "Geometrical isomerism",
                    "C": "Linkage isomerism",
                    "D": "Coordination isomerism",
                },
                "correct": "B",
            },
            {
                "question": "The rate of reaction is directly proportional to:",
                "options": {
                    "A": "Temperature only",
                    "B": "Concentration of reactants",
                    "C": "Pressure only",
                    "D": "Volume of the container",
                },
                "correct": "B",
            },
            {
                "question": "Which reagent is used to distinguish between aldehydes and ketones?",
                "options": {
                    "A": "Fehling's reagent",
                    "B": "Lucas reagent",
                    "C": "Grignard reagent",
                    "D": "Schiff's reagent",
                },
                "correct": "A",
            },
            {
                "question": "The molecular geometry of SF6 is:",
                "options": {
                    "A": "Tetrahedral",
                    "B": "Octahedral",
                    "C": "Square planar",
                    "D": "Trigonal bipyramidal",
                },
                "correct": "B",
            },
            {
                "question": "The dimensional formula of angular momentum is:",
                "options": {
                    "A": "[ML2T-1]",
                    "B": "[MLT-1]",
                    "C": "[ML2T-2]",
                    "D": "[MLT-2]",
                },
                "correct": "A",
            },
            {
                "question": "The work function of a metal in photoelectric effect represents:",
                "options": {
                    "A": "Maximum kinetic energy of emitted electrons",
                    "B": "Minimum energy required to remove an electron",
                    "C": "Energy of incident photon",
                    "D": "Total energy of the system",
                },
                "correct": "B",
            },
            {
                "question": "In a uniform magnetic field, a charged particle moves in:",
                "options": {
                    "A": "Straight line",
                    "B": "Parabolic path",
                    "C": "Circular path",
                    "D": "Elliptical path",
                },
                "correct": "C",
            },
            {
                "question": "The capacitance of a parallel plate capacitor is directly proportional to:",
                "options": {
                    "A": "Distance between plates",
                    "B": "Area of plates",
                    "C": "Voltage applied",
                    "D": "Charge stored",
                },
                "correct": "B",
            },
            {
                "question": "The phenomenon of interference of light proves its:",
                "options": {
                    "A": "Particle nature",
                    "B": "Wave nature",
                    "C": "Electromagnetic nature",
                    "D": "Quantum nature",
                },
                "correct": "B",
            },
            {
                "question": "The de Broglie wavelength is inversely proportional to:",
                "options": {
                    "A": "Mass",
                    "B": "Velocity",
                    "C": "Momentum",
                    "D": "Energy",
                },
                "correct": "C",
            },
            {
                "question": "In a step-up transformer, the turns ratio is:",
                "options": {
                    "A": "Np > Ns",
                    "B": "Np < Ns",
                    "C": "Np = Ns",
                    "D": "Independent of voltage",
                },
                "correct": "B",
            },
            {
                "question": "The critical angle for total internal reflection depends on:",
                "options": {
                    "A": "Angle of incidence only",
                    "B": "Wavelength of light only",
                    "C": "Refractive indices of both media",
                    "D": "Intensity of light",
                },
                "correct": "C",
            },
            {
                "question": "The binding energy per nucleon is maximum for:",
                "options": {
                    "A": "Hydrogen",
                    "B": "Iron",
                    "C": "Uranium",
                    "D": "Helium",
                },
                "correct": "B",
            },
            {
                "question": "The escape velocity from Earth's surface is approximately:",
                "options": {
                    "A": "7.9 km/s",
                    "B": "11.2 km/s",
                    "C": "15.0 km/s",
                    "D": "9.8 km/s",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct passive voice: 'She teaches English.'",
                "options": {
                    "A": "English is taught by her.",
                    "B": "English was taught by her.",
                    "C": "English has been taught by her.",
                    "D": "English will be taught by her.",
                },
                "correct": "A",
            },
            {
                "question": "Identify the figure of speech: 'The wind whispered through the trees.'",
                "options": {
                    "A": "Metaphor",
                    "B": "Simile",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct indirect speech: He said, 'I am going home.'",
                "options": {
                    "A": "He said that he is going home.",
                    "B": "He said that he was going home.",
                    "C": "He said that he will go home.",
                    "D": "He said that he goes home.",
                },
                "correct": "B",
            },
            {
                "question": "The word 'bibliography' means:",
                "options": {
                    "A": "Study of books",
                    "B": "List of books and sources",
                    "C": "Writing books",
                    "D": "Collection of books",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct collective noun for 'fish':",
                "options": {"A": "Herd", "B": "Flock", "C": "School", "D": "Pack"},
                "correct": "C",
            },
            {
                "question": "Identify the type of sentence: 'What a beautiful day it is!'",
                "options": {
                    "A": "Interrogative",
                    "B": "Imperative",
                    "C": "Exclamatory",
                    "D": "Declarative",
                },
                "correct": "C",
            },
            {
                "question": "The prefix 'un-' in 'unfriendly' indicates:",
                "options": {"A": "Before", "B": "Not", "C": "Again", "D": "Very"},
                "correct": "B",
            },
            {
                "question": "Choose the correct conjunction: 'Study hard ___ you will fail.'",
                "options": {"A": "and", "B": "but", "C": "or", "D": "so"},
                "correct": "C",
            },
            {
                "question": "The literary device used in 'Life is a journey' is:",
                "options": {
                    "A": "Simile",
                    "B": "Metaphor",
                    "C": "Alliteration",
                    "D": "Onomatopoeia",
                },
                "correct": "B",
            },
            {
                "question": "Select the correct comparative form: 'This book is ___ than that one.'",
                "options": {"A": "good", "B": "better", "C": "best", "D": "well"},
                "correct": "B",
            },
            {
                "question": "Which type of symmetry do cnidarians exhibit?",
                "options": {
                    "A": "Bilateral symmetry",
                    "B": "Radial symmetry",
                    "C": "Asymmetry",
                    "D": "Spherical symmetry",
                },
                "correct": "B",
            },
            {
                "question": "The excretory organ in insects is:",
                "options": {
                    "A": "Kidney",
                    "B": "Malpighian tubules",
                    "C": "Nephridia",
                    "D": "Flame cells",
                },
                "correct": "B",
            },
            {
                "question": "Which class of vertebrates has a two-chambered heart?",
                "options": {"A": "Mammals", "B": "Birds", "C": "Fish", "D": "Reptiles"},
                "correct": "C",
            },
            {
                "question": "The larval stage of a butterfly is called:",
                "options": {
                    "A": "Pupa",
                    "B": "Caterpillar",
                    "C": "Nymph",
                    "D": "Tadpole",
                },
                "correct": "B",
            },
            {
                "question": "Which animal shows bioluminescence?",
                "options": {
                    "A": "Jellyfish",
                    "B": "Octopus",
                    "C": "Starfish",
                    "D": "Sea cucumber",
                },
                "correct": "A",
            },
            {
                "question": "The study of insects is called:",
                "options": {
                    "A": "Entomology",
                    "B": "Ornithology",
                    "C": "Herpetology",
                    "D": "Ichthyology",
                },
                "correct": "A",
            },
            {
                "question": "Which phylum includes animals with jointed legs?",
                "options": {
                    "A": "Mollusca",
                    "B": "Arthropoda",
                    "C": "Annelida",
                    "D": "Echinodermata",
                },
                "correct": "B",
            },
            {
                "question": "The respiratory organ in spiders is:",
                "options": {
                    "A": "Gills",
                    "B": "Lungs",
                    "C": "Book lungs",
                    "D": "Trachea",
                },
                "correct": "C",
            },
            {
                "question": "Which animal undergoes complete metamorphosis?",
                "options": {
                    "A": "Grasshopper",
                    "B": "Dragonfly",
                    "C": "Beetle",
                    "D": "Cockroach",
                },
                "correct": "C",
            },
            {
                "question": "The phenomenon of animals being active during twilight is called:",
                "options": {
                    "A": "Diurnal",
                    "B": "Nocturnal",
                    "C": "Crepuscular",
                    "D": "Arrhythmic",
                },
                "correct": "C",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }

    exams["BIO001"] = sample_exam_1

    # Create second sample exam
    sample_exam_code_2 = generate_exam_code()
    sample_exam_2 = {
        "code": "BIO002",
        "title": "Bio-Science Entrance Exam 2",
        "duration": 50,
        "questions": [
            {
                "question": "Which of the following is the site of light reaction in photosynthesis?",
                "options": {
                    "A": "Stroma",
                    "B": "Thylakoid membrane",
                    "C": "Mitochondrial matrix",
                    "D": "Cytoplasm",
                },
                "correct": "B",
            },
            {
                "question": "The lac operon is an example of:",
                "options": {
                    "A": "Positive regulation",
                    "B": "Negative regulation",
                    "C": "Both positive and negative regulation",
                    "D": "Constitutive expression",
                },
                "correct": "C",
            },
            {
                "question": "Which vitamin is synthesized by bacteria in the human intestine?",
                "options": {
                    "A": "Vitamin C",
                    "B": "Vitamin D",
                    "C": "Vitamin K",
                    "D": "Vitamin A",
                },
                "correct": "C",
            },
            {
                "question": "The phenomenon of apoptosis is:",
                "options": {
                    "A": "Programmed cell death",
                    "B": "Cell division",
                    "C": "Cell differentiation",
                    "D": "Cell migration",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following is not a stop codon?",
                "options": {"A": "UAG", "B": "UAA", "C": "UGA", "D": "AUG"},
                "correct": "D",
            },
            {
                "question": "Mendel's law of independent assortment is applicable when genes are:",
                "options": {
                    "A": "Linked",
                    "B": "Located on different chromosomes",
                    "C": "Located on the same chromosome",
                    "D": "Allelic",
                },
                "correct": "B",
            },
            {
                "question": "Which plant hormone promotes seed germination?",
                "options": {
                    "A": "Abscisic acid",
                    "B": "Cytokinin",
                    "C": "Gibberellin",
                    "D": "Ethylene",
                },
                "correct": "C",
            },
            {
                "question": "The process of translation occurs in:",
                "options": {
                    "A": "Nucleus",
                    "B": "Ribosomes",
                    "C": "Mitochondria",
                    "D": "Golgi apparatus",
                },
                "correct": "B",
            },
            {
                "question": "Which enzyme is involved in DNA replication?",
                "options": {
                    "A": "RNA polymerase",
                    "B": "DNA polymerase",
                    "C": "Ligase",
                    "D": "Both B and C",
                },
                "correct": "D",
            },
            {
                "question": "The Hardy-Weinberg principle assumes:",
                "options": {
                    "A": "Random mating",
                    "B": "No mutations",
                    "C": "No gene flow",
                    "D": "All of the above",
                },
                "correct": "D",
            },
            {
                "question": "Which of the following exhibits tautomerism?",
                "options": {
                    "A": "Acetone",
                    "B": "Acetaldehyde",
                    "C": "Phenol",
                    "D": "Both A and B",
                },
                "correct": "D",
            },
            {
                "question": "The hybridization of carbon in diamond is:",
                "options": {"A": "sp", "B": "sp2", "C": "sp3", "D": "sp3d"},
                "correct": "C",
            },
            {
                "question": "Which reagent is used for the oxidation of primary alcohols to aldehydes?",
                "options": {"A": "KMnO4", "B": "PCC", "C": "K2Cr2O7", "D": "H2SO4"},
                "correct": "B",
            },
            {
                "question": "The IUPAC name of CH3-CH(OH)-CH3 is:",
                "options": {
                    "A": "Propanol",
                    "B": "2-Propanol",
                    "C": "Isopropanol",
                    "D": "Both B and C",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is an electrophile?",
                "options": {"A": "NH3", "B": "OH-", "C": "BF3", "D": "CN-"},
                "correct": "C",
            },
            {
                "question": "The Cannizzaro reaction occurs with:",
                "options": {
                    "A": "Aldehydes having α-hydrogen",
                    "B": "Aldehydes having no α-hydrogen",
                    "C": "Ketones",
                    "D": "Alcohols",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following shows optical isomerism?",
                "options": {
                    "A": "CH3CH2CHClCH3",
                    "B": "CH3CH2CH2CH3",
                    "C": "CH3CHClCH2CH3",
                    "D": "Both A and C",
                },
                "correct": "D",
            },
            {
                "question": "The reaction between benzene and chlorine in presence of FeCl3 is:",
                "options": {
                    "A": "Addition reaction",
                    "B": "Substitution reaction",
                    "C": "Elimination reaction",
                    "D": "Condensation reaction",
                },
                "correct": "B",
            },
            {
                "question": "Which compound is formed when ethanoic acid reacts with ethanol?",
                "options": {
                    "A": "Ethyl acetate",
                    "B": "Acetic anhydride",
                    "C": "Ethyl formate",
                    "D": "Diethyl ether",
                },
                "correct": "A",
            },
            {
                "question": "The number of π electrons in benzene is:",
                "options": {"A": "4", "B": "6", "C": "8", "D": "10"},
                "correct": "B",
            },
            {
                "question": "The unit of electric field intensity is:",
                "options": {"A": "N/C", "B": "C/N", "C": "J/C", "D": "C/J"},
                "correct": "A",
            },
            {
                "question": "Young's double slit experiment demonstrates:",
                "options": {
                    "A": "Particle nature of light",
                    "B": "Wave nature of light",
                    "C": "Dual nature of light",
                    "D": "Polarization of light",
                },
                "correct": "B",
            },
            {
                "question": "The phenomenon of photoelectric effect supports:",
                "options": {
                    "A": "Wave theory of light",
                    "B": "Particle theory of light",
                    "C": "Both wave and particle theory",
                    "D": "Neither wave nor particle theory",
                },
                "correct": "B",
            },
            {
                "question": "The de Broglie wavelength is associated with:",
                "options": {
                    "A": "Only photons",
                    "B": "Only electrons",
                    "C": "All particles",
                    "D": "Only charged particles",
                },
                "correct": "C",
            },
            {
                "question": "In a transformer, the ratio of secondary to primary voltage is equal to:",
                "options": {
                    "A": "Ratio of secondary to primary current",
                    "B": "Ratio of primary to secondary turns",
                    "C": "Ratio of secondary to primary turns",
                    "D": "Square of turn ratio",
                },
                "correct": "C",
            },
            {
                "question": "The magnetic field inside a solenoid is:",
                "options": {
                    "A": "Zero",
                    "B": "Uniform",
                    "C": "Non-uniform",
                    "D": "Maximum at the center",
                },
                "correct": "B",
            },
            {
                "question": "Lenz's law is related to:",
                "options": {
                    "A": "Conservation of energy",
                    "B": "Conservation of momentum",
                    "C": "Conservation of charge",
                    "D": "Conservation of mass",
                },
                "correct": "A",
            },
            {
                "question": "The work function of a metal is 2 eV. The threshold frequency is:",
                "options": {
                    "A": "4.8 × 10^14 Hz",
                    "B": "8.3 × 10^14 Hz",
                    "C": "2.4 × 10^14 Hz",
                    "D": "1.6 × 10^14 Hz",
                },
                "correct": "A",
            },
            {
                "question": "The angular momentum of an electron in the nth orbit is:",
                "options": {"A": "nh/2π", "B": "nh/4π", "C": "2πnh", "D": "n²h/2π"},
                "correct": "A",
            },
            {
                "question": "The principle of superposition is applicable to:",
                "options": {
                    "A": "Longitudinal waves only",
                    "B": "Transverse waves only",
                    "C": "Both longitudinal and transverse waves",
                    "D": "Sound waves only",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct passive voice: 'The teacher teaches the students.'",
                "options": {
                    "A": "The students are taught by the teacher.",
                    "B": "The students were taught by the teacher.",
                    "C": "The students have been taught by the teacher.",
                    "D": "The students will be taught by the teacher.",
                },
                "correct": "A",
            },
            {
                "question": "Identify the figure of speech: 'The classroom was a zoo.'",
                "options": {
                    "A": "Simile",
                    "B": "Metaphor",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct article: '___ honest man is respected everywhere.'",
                "options": {"A": "A", "B": "An", "C": "The", "D": "No article needed"},
                "correct": "B",
            },
            {
                "question": "Select the correct indirect speech: He said, 'I am going to Delhi.'",
                "options": {
                    "A": "He said that he was going to Delhi.",
                    "B": "He said that he is going to Delhi.",
                    "C": "He told that he was going to Delhi.",
                    "D": "He said that I was going to Delhi.",
                },
                "correct": "A",
            },
            {
                "question": "Choose the correct meaning of the idiom 'Break the ice':",
                "options": {
                    "A": "To start a conversation",
                    "B": "To break something",
                    "C": "To make ice",
                    "D": "To freeze water",
                },
                "correct": "A",
            },
            {
                "question": "Identify the type of sentence: 'What a beautiful day it is!'",
                "options": {
                    "A": "Declarative",
                    "B": "Interrogative",
                    "C": "Imperative",
                    "D": "Exclamatory",
                },
                "correct": "D",
            },
            {
                "question": "Choose the antonym of 'Zenith':",
                "options": {"A": "Peak", "B": "Summit", "C": "Nadir", "D": "Top"},
                "correct": "C",
            },
            {
                "question": "Select the correctly punctuated sentence:",
                "options": {
                    "A": "The man, who was walking down the street was tall.",
                    "B": "The man who was walking down the street, was tall.",
                    "C": "The man, who was walking down the street, was tall.",
                    "D": "The man who was walking down the street was tall.",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct comparative form: 'This book is ___ than that one.'",
                "options": {
                    "A": "more interesting",
                    "B": "most interesting",
                    "C": "interestinger",
                    "D": "interest",
                },
                "correct": "A",
            },
            {
                "question": "Identify the conjunction in: 'He studied hard, but he failed.'",
                "options": {"A": "He", "B": "Hard", "C": "But", "D": "Failed"},
                "correct": "C",
            },
            {
                "question": "Which system is responsible for producing antibodies?",
                "options": {
                    "A": "Nervous system",
                    "B": "Immune system",
                    "C": "Endocrine system",
                    "D": "Circulatory system",
                },
                "correct": "B",
            },
            {
                "question": "The study of insects is called:",
                "options": {
                    "A": "Ornithology",
                    "B": "Herpetology",
                    "C": "Entomology",
                    "D": "Ichthyology",
                },
                "correct": "C",
            },
            {
                "question": "Which hormone regulates calcium levels in blood?",
                "options": {
                    "A": "Insulin",
                    "B": "Thyroxine",
                    "C": "Parathormone",
                    "D": "Adrenaline",
                },
                "correct": "C",
            },
            {
                "question": "The excretory product of birds is:",
                "options": {
                    "A": "Ammonia",
                    "B": "Urea",
                    "C": "Uric acid",
                    "D": "Creatinine",
                },
                "correct": "C",
            },
            {
                "question": "Which animal shows regeneration?",
                "options": {"A": "Hydra", "B": "Elephant", "C": "Tiger", "D": "Eagle"},
                "correct": "A",
            },
            {
                "question": "The largest artery in the human body is:",
                "options": {
                    "A": "Pulmonary artery",
                    "B": "Carotid artery",
                    "C": "Aorta",
                    "D": "Renal artery",
                },
                "correct": "C",
            },
            {
                "question": "Which phylum does Hydra belong to?",
                "options": {
                    "A": "Porifera",
                    "B": "Cnidaria",
                    "C": "Platyhelminthes",
                    "D": "Nematoda",
                },
                "correct": "B",
            },
            {
                "question": "The process of metamorphosis is complete in:",
                "options": {
                    "A": "Grasshopper",
                    "B": "Cockroach",
                    "C": "Butterfly",
                    "D": "Dragonfly",
                },
                "correct": "C",
            },
            {
                "question": "Which vitamin deficiency causes scurvy?",
                "options": {
                    "A": "Vitamin A",
                    "B": "Vitamin B",
                    "C": "Vitamin C",
                    "D": "Vitamin D",
                },
                "correct": "C",
            },
            {
                "question": "The alimentary canal is longest in:",
                "options": {
                    "A": "Carnivores",
                    "B": "Herbivores",
                    "C": "Omnivores",
                    "D": "All are equal",
                },
                "correct": "B",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }

    exams["BIO002"] = sample_exam_2
    sample_exam_code_3 = generate_exam_code()
    sample_exam_3 = {
        "code": "BIO003",
        "title": "Bio-Science Entrance Exam 3",
        "duration": 50,
        "questions": [
            {
                "question": "Which of the following is the correct sequence of electron transport chain in mitochondria?",
                "options": {
                    "A": "NADH → Complex II → Cytochrome c → Complex IV",
                    "B": "NADH → Complex I → Complex III → Complex IV",
                    "C": "FADH2 → Complex I → Complex II → Complex IV",
                    "D": "NADH → Complex III → Complex I → Complex IV",
                },
                "correct": "B",
            },
            {
                "question": "In which phase of meiosis does crossing over occur?",
                "options": {
                    "A": "Prophase I",
                    "B": "Metaphase I",
                    "C": "Anaphase I",
                    "D": "Prophase II",
                },
                "correct": "A",
            },
            {
                "question": "Which plant hormone is known as the stress hormone?",
                "options": {
                    "A": "Auxin",
                    "B": "Cytokinin",
                    "C": "Abscisic acid",
                    "D": "Gibberellin",
                },
                "correct": "C",
            },
            {
                "question": "The lac operon is an example of:",
                "options": {
                    "A": "Positive regulation",
                    "B": "Negative regulation",
                    "C": "Both positive and negative regulation",
                    "D": "Constitutive expression",
                },
                "correct": "C",
            },
            {
                "question": "Which enzyme is deficient in phenylketonuria (PKU)?",
                "options": {
                    "A": "Phenylalanine hydroxylase",
                    "B": "Tyrosinase",
                    "C": "Tryptophan pyrrolase",
                    "D": "Histidase",
                },
                "correct": "A",
            },
            {
                "question": "The Calvin cycle occurs in which part of the chloroplast?",
                "options": {
                    "A": "Thylakoid membrane",
                    "B": "Stroma",
                    "C": "Grana",
                    "D": "Inner membrane",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is not a component of the cytoskeleton?",
                "options": {
                    "A": "Microtubules",
                    "B": "Microfilaments",
                    "C": "Intermediate filaments",
                    "D": "Ribosomes",
                },
                "correct": "D",
            },
            {
                "question": "In DNA replication, which enzyme removes RNA primers?",
                "options": {
                    "A": "DNA polymerase I",
                    "B": "DNA polymerase III",
                    "C": "Primase",
                    "D": "Ligase",
                },
                "correct": "A",
            },
            {
                "question": "Which type of chromosomal aberration involves the loss of a chromosome segment?",
                "options": {
                    "A": "Duplication",
                    "B": "Inversion",
                    "C": "Deletion",
                    "D": "Translocation",
                },
                "correct": "C",
            },
            {
                "question": "The principle of complementarity was proposed by:",
                "options": {
                    "A": "Watson and Crick",
                    "B": "Chargaff",
                    "C": "Franklin",
                    "D": "Meselson and Stahl",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following has the highest lattice energy?",
                "options": {"A": "NaCl", "B": "MgO", "C": "CaO", "D": "KCl"},
                "correct": "B",
            },
            {
                "question": "The number of unpaired electrons in Mn²⁺ ion is:",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct": "C",
            },
            {
                "question": "Which of the following is an example of a nucleophilic substitution reaction?",
                "options": {
                    "A": "CH₃CH₂Br + OH⁻ → CH₃CH₂OH + Br⁻",
                    "B": "CH₄ + Cl₂ → CH₃Cl + HCl",
                    "C": "C₂H₄ + HBr → C₂H₅Br",
                    "D": "C₆H₆ + Br₂ → C₆H₅Br + HBr",
                },
                "correct": "A",
            },
            {
                "question": "The IUPAC name of CH₃CH(OH)CH₂CHO is:",
                "options": {
                    "A": "3-hydroxybutanal",
                    "B": "2-hydroxybutanal",
                    "C": "4-hydroxybutanal",
                    "D": "1-hydroxybutanal",
                },
                "correct": "A",
            },
            {
                "question": "Which catalyst is used in the Haber process?",
                "options": {"A": "Pt", "B": "Ni", "C": "Fe", "D": "V₂O₅"},
                "correct": "C",
            },
            {
                "question": "The hybridization of carbon in diamond is:",
                "options": {"A": "sp", "B": "sp²", "C": "sp³", "D": "sp³d"},
                "correct": "C",
            },
            {
                "question": "Which of the following is most acidic?",
                "options": {
                    "A": "Phenol",
                    "B": "Ethanol",
                    "C": "Acetic acid",
                    "D": "Formic acid",
                },
                "correct": "D",
            },
            {
                "question": "The oxidation state of chromium in K₂Cr₂O₇ is:",
                "options": {"A": "+3", "B": "+6", "C": "+7", "D": "+4"},
                "correct": "B",
            },
            {
                "question": "Which type of isomerism is shown by [Co(NH₃)₄Cl₂]⁺?",
                "options": {
                    "A": "Optical isomerism",
                    "B": "Geometric isomerism",
                    "C": "Linkage isomerism",
                    "D": "Ionization isomerism",
                },
                "correct": "B",
            },
            {
                "question": "The entropy change is maximum in which process?",
                "options": {
                    "A": "Melting of ice",
                    "B": "Boiling of water",
                    "C": "Sublimation of dry ice",
                    "D": "Crystallization",
                },
                "correct": "C",
            },
            {
                "question": "A particle moves in a circle of radius R. The ratio of distance to displacement after half revolution is:",
                "options": {"A": "π:2", "B": "2:π", "C": "π:1", "D": "1:π"},
                "correct": "A",
            },
            {
                "question": "The escape velocity from Earth's surface is approximately:",
                "options": {
                    "A": "7.9 km/s",
                    "B": "11.2 km/s",
                    "C": "9.8 km/s",
                    "D": "15.0 km/s",
                },
                "correct": "B",
            },
            {
                "question": "In Young's double slit experiment, if the distance between slits is doubled, the fringe width becomes:",
                "options": {
                    "A": "Double",
                    "B": "Half",
                    "C": "Four times",
                    "D": "One-fourth",
                },
                "correct": "B",
            },
            {
                "question": "Which physical quantity has the same dimensions as impulse?",
                "options": {"A": "Force", "B": "Momentum", "C": "Energy", "D": "Power"},
                "correct": "B",
            },
            {
                "question": "The working principle of a transformer is based on:",
                "options": {
                    "A": "Self-induction",
                    "B": "Mutual induction",
                    "C": "Electromagnetic induction",
                    "D": "Both B and C",
                },
                "correct": "D",
            },
            {
                "question": "In a photoelectric effect experiment, stopping potential depends on:",
                "options": {
                    "A": "Intensity of light",
                    "B": "Frequency of light",
                    "C": "Both intensity and frequency",
                    "D": "Neither intensity nor frequency",
                },
                "correct": "B",
            },
            {
                "question": "The de Broglie wavelength of a particle is inversely proportional to:",
                "options": {
                    "A": "Mass",
                    "B": "Velocity",
                    "C": "Momentum",
                    "D": "Energy",
                },
                "correct": "C",
            },
            {
                "question": "Which type of semiconductor is formed when silicon is doped with phosphorus?",
                "options": {
                    "A": "Intrinsic",
                    "B": "p-type",
                    "C": "n-type",
                    "D": "Compound",
                },
                "correct": "C",
            },
            {
                "question": "The magnetic field at the center of a circular loop carrying current is:",
                "options": {
                    "A": "Directly proportional to radius",
                    "B": "Inversely proportional to radius",
                    "C": "Independent of radius",
                    "D": "Proportional to square of radius",
                },
                "correct": "B",
            },
            {
                "question": "In simple harmonic motion, the acceleration is:",
                "options": {
                    "A": "Maximum at mean position",
                    "B": "Zero at extreme position",
                    "C": "Maximum at extreme position",
                    "D": "Constant throughout",
                },
                "correct": "C",
            },
            {
                "question": "Choose the sentence with correct subject-verb agreement:",
                "options": {
                    "A": "Each of the students have submitted their assignments.",
                    "B": "Neither John nor his friends is coming to the party.",
                    "C": "The team is practicing for the championship.",
                    "D": "Mathematics are my favorite subject.",
                },
                "correct": "C",
            },
            {
                "question": "Which of the following is a complex sentence?",
                "options": {
                    "A": "She went to the store and bought groceries.",
                    "B": "Although it was raining, we went for a walk.",
                    "C": "The sun is shining brightly today.",
                    "D": "He studied hard, yet he failed the exam.",
                },
                "correct": "B",
            },
            {
                "question": "Identify the figure of speech in: 'The classroom was a zoo.'",
                "options": {
                    "A": "Simile",
                    "B": "Metaphor",
                    "C": "Personification",
                    "D": "Alliteration",
                },
                "correct": "B",
            },
            {
                "question": "Which word is spelled correctly?",
                "options": {
                    "A": "Occurance",
                    "B": "Occurence",
                    "C": "Occurrence",
                    "D": "Occurrance",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct passive voice form: 'The chef prepared the meal.'",
                "options": {
                    "A": "The meal was prepared by the chef.",
                    "B": "The meal is prepared by the chef.",
                    "C": "The meal has been prepared by the chef.",
                    "D": "The meal had been prepared by the chef.",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following is an example of a dangling modifier?",
                "options": {
                    "A": "Walking to school, the rain started pouring.",
                    "B": "The book on the table is mine.",
                    "C": "She quickly finished her homework.",
                    "D": "After eating dinner, we watched a movie.",
                },
                "correct": "A",
            },
            {
                "question": "Identify the type of clause: 'When the bell rings' in 'When the bell rings, class will begin.'",
                "options": {
                    "A": "Independent clause",
                    "B": "Dependent clause",
                    "C": "Relative clause",
                    "D": "Noun clause",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct form: 'If I _____ you, I would accept the offer.'",
                "options": {"A": "am", "B": "was", "C": "were", "D": "will be"},
                "correct": "C",
            },
            {
                "question": "Which punctuation mark is used to show possession?",
                "options": {
                    "A": "Comma",
                    "B": "Apostrophe",
                    "C": "Semicolon",
                    "D": "Colon",
                },
                "correct": "B",
            },
            {
                "question": "Select the sentence with correct parallelism:",
                "options": {
                    "A": "She likes reading, writing, and to paint.",
                    "B": "He is smart, dedicated, and works hard.",
                    "C": "The presentation was clear, informative, and engaging.",
                    "D": "They enjoy swimming, hiking, and to cycle.",
                },
                "correct": "C",
            },
            {
                "question": "Which type of circulatory system is found in arthropods?",
                "options": {
                    "A": "Closed circulatory system",
                    "B": "Open circulatory system",
                    "C": "Both open and closed",
                    "D": "No circulatory system",
                },
                "correct": "B",
            },
            {
                "question": "The excretory organ in flatworms is:",
                "options": {
                    "A": "Nephridia",
                    "B": "Malpighian tubules",
                    "C": "Flame cells",
                    "D": "Kidneys",
                },
                "correct": "C",
            },
            {
                "question": "Which phylum is characterized by the presence of cnidocytes?",
                "options": {
                    "A": "Porifera",
                    "B": "Cnidaria",
                    "C": "Platyhelminthes",
                    "D": "Nematoda",
                },
                "correct": "B",
            },
            {
                "question": "The body cavity in roundworms is called:",
                "options": {
                    "A": "Coelom",
                    "B": "Pseudocoelom",
                    "C": "Haemocoel",
                    "D": "Acoelomate",
                },
                "correct": "B",
            },
            {
                "question": "Which class of mollusks includes squid and octopus?",
                "options": {
                    "A": "Gastropoda",
                    "B": "Bivalvia",
                    "C": "Cephalopoda",
                    "D": "Polyplacophora",
                },
                "correct": "C",
            },
            {
                "question": "The water vascular system is characteristic of:",
                "options": {
                    "A": "Mollusca",
                    "B": "Arthropoda",
                    "C": "Echinodermata",
                    "D": "Annelida",
                },
                "correct": "C",
            },
            {
                "question": "Which structure is used for respiration in fish?",
                "options": {"A": "Lungs", "B": "Gills", "C": "Skin", "D": "Spiracles"},
                "correct": "B",
            },
            {
                "question": "The larval stage of a frog is called:",
                "options": {
                    "A": "Caterpillar",
                    "B": "Tadpole",
                    "C": "Pupa",
                    "D": "Nymph",
                },
                "correct": "B",
            },
            {
                "question": "Which animal shows external fertilization?",
                "options": {
                    "A": "Mammals",
                    "B": "Birds",
                    "C": "Reptiles",
                    "D": "Amphibians",
                },
                "correct": "D",
            },
            {
                "question": "The study of insects is called:",
                "options": {
                    "A": "Ornithology",
                    "B": "Herpetology",
                    "C": "Entomology",
                    "D": "Ichthyology",
                },
                "correct": "C",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }

    exams["BIO003"] = sample_exam_3
    sample_exam_code_3 = generate_exam_code()
    sample_exam_4 = {
        "code": "BIO004",
        "title": "Bio-Science Entrance Exam 4",
        "duration": 50,
        "questions": [
            {
                "question": "Which of the following is the powerhouse of the cell?",
                "options": {
                    "A": "Nucleus",
                    "B": "Mitochondria",
                    "C": "Ribosome",
                    "D": "Golgi apparatus",
                },
                "correct": "B",
            },
            {
                "question": "The process of formation of gametes is called:",
                "options": {
                    "A": "Mitosis",
                    "B": "Meiosis",
                    "C": "Binary fission",
                    "D": "Budding",
                },
                "correct": "B",
            },
            {
                "question": "Which enzyme breaks down starch into maltose?",
                "options": {
                    "A": "Pepsin",
                    "B": "Trypsin",
                    "C": "Amylase",
                    "D": "Lipase",
                },
                "correct": "C",
            },
            {
                "question": "The site of protein synthesis in a cell is:",
                "options": {
                    "A": "Nucleus",
                    "B": "Mitochondria",
                    "C": "Ribosome",
                    "D": "Lysosome",
                },
                "correct": "C",
            },
            {
                "question": "Which tissue is responsible for transport of water in plants?",
                "options": {
                    "A": "Phloem",
                    "B": "Xylem",
                    "C": "Collenchyma",
                    "D": "Sclerenchyma",
                },
                "correct": "B",
            },
            {
                "question": "The genetic material DNA is located in:",
                "options": {
                    "A": "Cytoplasm",
                    "B": "Nucleus",
                    "C": "Mitochondria",
                    "D": "Both B and C",
                },
                "correct": "D",
            },
            {
                "question": "Which hormone regulates blood sugar levels?",
                "options": {
                    "A": "Thyroxine",
                    "B": "Insulin",
                    "C": "Adrenaline",
                    "D": "Growth hormone",
                },
                "correct": "B",
            },
            {
                "question": "Photosynthesis occurs in which part of the plant cell?",
                "options": {
                    "A": "Nucleus",
                    "B": "Mitochondria",
                    "C": "Chloroplast",
                    "D": "Vacuole",
                },
                "correct": "C",
            },
            {
                "question": "The functional unit of kidney is:",
                "options": {
                    "A": "Neuron",
                    "B": "Nephron",
                    "C": "Alveoli",
                    "D": "Hepatocyte",
                },
                "correct": "B",
            },
            {
                "question": "Which type of cell division reduces chromosome number by half?",
                "options": {
                    "A": "Mitosis",
                    "B": "Meiosis",
                    "C": "Amitosis",
                    "D": "Binary fission",
                },
                "correct": "B",
            },
            {
                "question": "The atomic number of carbon is:",
                "options": {"A": "4", "B": "6", "C": "8", "D": "12"},
                "correct": "B",
            },
            {
                "question": "Which of the following is an example of a homogeneous mixture?",
                "options": {
                    "A": "Sand and water",
                    "B": "Oil and water",
                    "C": "Salt solution",
                    "D": "Iron filings and sulfur",
                },
                "correct": "C",
            },
            {
                "question": "The electronic configuration of sodium (Na) is:",
                "options": {
                    "A": "2, 8, 1",
                    "B": "2, 8, 2",
                    "C": "2, 7, 2",
                    "D": "2, 8, 8",
                },
                "correct": "A",
            },
            {
                "question": "Which gas is produced when metals react with acids?",
                "options": {
                    "A": "Oxygen",
                    "B": "Carbon dioxide",
                    "C": "Hydrogen",
                    "D": "Nitrogen",
                },
                "correct": "C",
            },
            {
                "question": "The chemical formula of methane is:",
                "options": {"A": "CH3", "B": "CH4", "C": "C2H4", "D": "C2H6"},
                "correct": "B",
            },
            {
                "question": "Which of the following is a reducing agent?",
                "options": {
                    "A": "Oxygen",
                    "B": "Chlorine",
                    "C": "Hydrogen",
                    "D": "Fluorine",
                },
                "correct": "C",
            },
            {
                "question": "The pH of lemon juice is approximately:",
                "options": {"A": "2", "B": "7", "C": "9", "D": "12"},
                "correct": "A",
            },
            {
                "question": "Which element is used in making pencil leads?",
                "options": {"A": "Lead", "B": "Carbon", "C": "Silicon", "D": "Sulfur"},
                "correct": "B",
            },
            {
                "question": "The process of rusting requires the presence of:",
                "options": {
                    "A": "Only oxygen",
                    "B": "Only water",
                    "C": "Both oxygen and water",
                    "D": "Neither oxygen nor water",
                },
                "correct": "C",
            },
            {
                "question": "Which of the following is an alkali?",
                "options": {"A": "HCl", "B": "H2SO4", "C": "NaOH", "D": "CH3COOH"},
                "correct": "C",
            },
            {
                "question": "The SI unit of work is:",
                "options": {"A": "Newton", "B": "Joule", "C": "Watt", "D": "Pascal"},
                "correct": "B",
            },
            {
                "question": "Which law states that energy can neither be created nor destroyed?",
                "options": {
                    "A": "Newton's first law",
                    "B": "Law of conservation of energy",
                    "C": "Ohm's law",
                    "D": "Archimedes' principle",
                },
                "correct": "B",
            },
            {
                "question": "The formula for kinetic energy is:",
                "options": {"A": "mgh", "B": "1/2 mv²", "C": "Fd", "D": "P/t"},
                "correct": "B",
            },
            {
                "question": "Which mirror is used as a rear-view mirror in vehicles?",
                "options": {
                    "A": "Plane mirror",
                    "B": "Concave mirror",
                    "C": "Convex mirror",
                    "D": "Spherical mirror",
                },
                "correct": "C",
            },
            {
                "question": "The resistance of a conductor depends on:",
                "options": {
                    "A": "Length only",
                    "B": "Area only",
                    "C": "Material only",
                    "D": "All of the above",
                },
                "correct": "D",
            },
            {
                "question": "Sound travels fastest in:",
                "options": {"A": "Vacuum", "B": "Air", "C": "Water", "D": "Steel"},
                "correct": "D",
            },
            {
                "question": "The power of a lens is measured in:",
                "options": {
                    "A": "Meters",
                    "B": "Diopters",
                    "C": "Watts",
                    "D": "Joules",
                },
                "correct": "B",
            },
            {
                "question": "Which electromagnetic radiation has the longest wavelength?",
                "options": {
                    "A": "X-rays",
                    "B": "Visible light",
                    "C": "Radio waves",
                    "D": "Gamma rays",
                },
                "correct": "C",
            },
            {
                "question": "The acceleration due to gravity on Earth is approximately:",
                "options": {
                    "A": "9.8 m/s²",
                    "B": "10.8 m/s²",
                    "C": "8.8 m/s²",
                    "D": "11.8 m/s²",
                },
                "correct": "A",
            },
            {
                "question": "Which device is used to measure electric current?",
                "options": {
                    "A": "Voltmeter",
                    "B": "Ammeter",
                    "C": "Galvanometer",
                    "D": "Multimeter",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct passive voice: 'She writes a letter.'",
                "options": {
                    "A": "A letter is written by her.",
                    "B": "A letter was written by her.",
                    "C": "A letter is being written by her.",
                    "D": "A letter has been written by her.",
                },
                "correct": "A",
            },
            {
                "question": "Identify the figure of speech: 'The stars danced in the sky.'",
                "options": {
                    "A": "Simile",
                    "B": "Metaphor",
                    "C": "Personification",
                    "D": "Alliteration",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct article: '___ university is a place of learning.'",
                "options": {"A": "A", "B": "An", "C": "The", "D": "No article"},
                "correct": "A",
            },
            {
                "question": "Select the correct indirect speech: He said, 'I am going home.'",
                "options": {
                    "A": "He said that he is going home.",
                    "B": "He said that he was going home.",
                    "C": "He said that he will go home.",
                    "D": "He said that he has gone home.",
                },
                "correct": "B",
            },
            {
                "question": "Choose the synonym of 'Meticulous':",
                "options": {"A": "Careless", "B": "Careful", "C": "Lazy", "D": "Hasty"},
                "correct": "B",
            },
            {
                "question": "Fill in the blank with the correct conjunction: 'He is poor ___ honest.'",
                "options": {"A": "and", "B": "but", "C": "or", "D": "so"},
                "correct": "B",
            },
            {
                "question": "Identify the type of sentence: 'What a beautiful day!'",
                "options": {
                    "A": "Declarative",
                    "B": "Interrogative",
                    "C": "Exclamatory",
                    "D": "Imperative",
                },
                "correct": "C",
            },
            {
                "question": "Choose the antonym of 'Transparent':",
                "options": {"A": "Clear", "B": "Opaque", "C": "Visible", "D": "Bright"},
                "correct": "B",
            },
            {
                "question": "Select the correctly punctuated sentence:",
                "options": {
                    "A": "Yes I am coming.",
                    "B": "Yes, I am coming.",
                    "C": "Yes; I am coming.",
                    "D": "Yes: I am coming.",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct comparative form: 'This book is ___ than that one.'",
                "options": {"A": "good", "B": "better", "C": "best", "D": "more good"},
                "correct": "B",
            },
            {
                "question": "Which system is responsible for filtering blood in vertebrates?",
                "options": {
                    "A": "Digestive system",
                    "B": "Respiratory system",
                    "C": "Excretory system",
                    "D": "Circulatory system",
                },
                "correct": "C",
            },
            {
                "question": "The largest phylum in the animal kingdom is:",
                "options": {
                    "A": "Chordata",
                    "B": "Arthropoda",
                    "C": "Mollusca",
                    "D": "Cnidaria",
                },
                "correct": "B",
            },
            {
                "question": "Which animal has an open circulatory system?",
                "options": {"A": "Human", "B": "Fish", "C": "Cockroach", "D": "Frog"},
                "correct": "C",
            },
            {
                "question": "The process of shedding old skin in snakes is called:",
                "options": {
                    "A": "Moulting",
                    "B": "Metamorphosis",
                    "C": "Regeneration",
                    "D": "Hibernation",
                },
                "correct": "A",
            },
            {
                "question": "Which organ is vestigial in humans?",
                "options": {"A": "Heart", "B": "Liver", "C": "Appendix", "D": "Kidney"},
                "correct": "C",
            },
            {
                "question": "The study of insects is called:",
                "options": {
                    "A": "Ornithology",
                    "B": "Entomology",
                    "C": "Herpetology",
                    "D": "Ichthyology",
                },
                "correct": "B",
            },
            {
                "question": "Which animal is known for echolocation?",
                "options": {"A": "Eagle", "B": "Bat", "C": "Owl", "D": "Snake"},
                "correct": "B",
            },
            {
                "question": "The breathing organs of fish are:",
                "options": {"A": "Lungs", "B": "Gills", "C": "Skin", "D": "Spiracles"},
                "correct": "B",
            },
            {
                "question": "Which animal shows complete metamorphosis?",
                "options": {
                    "A": "Grasshopper",
                    "B": "Cockroach",
                    "C": "Butterfly",
                    "D": "Dragonfly",
                },
                "correct": "C",
            },
            {
                "question": "The hormone responsible for milk production in mammals is:",
                "options": {
                    "A": "Oxytocin",
                    "B": "Prolactin",
                    "C": "Estrogen",
                    "D": "Progesterone",
                },
                "correct": "B",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["BIO004"] = sample_exam_4

    sample_exam_5 = {
        "code": "BIO005",
        "title": "Bio-Science Entrance Exam 5",
        "duration": 50,
        "questions": [
            {
                "question": "Which of the following is the most abundant enzyme in the world?",
                "options": {
                    "A": "Pepsin",
                    "B": "RuBisCO",
                    "C": "Trypsin",
                    "D": "Amylase",
                },
                "correct": "B",
            },
            {
                "question": "The phenomenon of apical dominance is due to which hormone?",
                "options": {
                    "A": "Cytokinin",
                    "B": "Gibberellin",
                    "C": "Auxin",
                    "D": "Abscisic acid",
                },
                "correct": "C",
            },
            {
                "question": "Which of the following represents the correct pathway of water movement in plants?",
                "options": {
                    "A": "Root hair → Cortex → Endodermis → Pericycle → Xylem",
                    "B": "Root hair → Endodermis → Cortex → Pericycle → Xylem",
                    "C": "Root hair → Pericycle → Cortex → Endodermis → Xylem",
                    "D": "Root hair → Xylem → Cortex → Endodermis → Pericycle",
                },
                "correct": "A",
            },
            {
                "question": "In which phase of meiosis does crossing over occur?",
                "options": {
                    "A": "Prophase I",
                    "B": "Metaphase I",
                    "C": "Anaphase I",
                    "D": "Telophase I",
                },
                "correct": "A",
            },
            {
                "question": "Which biomolecule is the primary component of cell walls in fungi?",
                "options": {
                    "A": "Cellulose",
                    "B": "Chitin",
                    "C": "Pectin",
                    "D": "Lignin",
                },
                "correct": "B",
            },
            {
                "question": "The 'lock and key' model explains the mechanism of:",
                "options": {
                    "A": "DNA replication",
                    "B": "Enzyme action",
                    "C": "Protein synthesis",
                    "D": "Photosynthesis",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is not a post-transcriptional modification in eukaryotes?",
                "options": {
                    "A": "5' capping",
                    "B": "3' polyadenylation",
                    "C": "Splicing",
                    "D": "Methylation of promoter",
                },
                "correct": "D",
            },
            {
                "question": "The primary acceptor of CO2 in C4 plants is:",
                "options": {"A": "RuBP", "B": "PEP", "C": "OAA", "D": "Malate"},
                "correct": "B",
            },
            {
                "question": "Which tissue is responsible for secondary growth in dicot stems?",
                "options": {
                    "A": "Cambium",
                    "B": "Pericycle",
                    "C": "Cortex",
                    "D": "Epidermis",
                },
                "correct": "A",
            },
            {
                "question": "The codon UGA codes for:",
                "options": {
                    "A": "Tryptophan",
                    "B": "Cysteine",
                    "C": "Stop codon",
                    "D": "Serine",
                },
                "correct": "C",
            },
            {
                "question": "Which class of vertebrates exhibits double circulation for the first time?",
                "options": {
                    "A": "Pisces",
                    "B": "Amphibia",
                    "C": "Reptilia",
                    "D": "Aves",
                },
                "correct": "B",
            },
            {
                "question": "The hormone that stimulates milk ejection is:",
                "options": {
                    "A": "Prolactin",
                    "B": "Oxytocin",
                    "C": "Estrogen",
                    "D": "Progesterone",
                },
                "correct": "B",
            },
            {
                "question": "Which part of the nephron is impermeable to water?",
                "options": {
                    "A": "Glomerulus",
                    "B": "Proximal convoluted tubule",
                    "C": "Ascending limb of loop of Henle",
                    "D": "Collecting duct",
                },
                "correct": "C",
            },
            {
                "question": "The cavity present in the blastula stage is called:",
                "options": {
                    "A": "Blastocoel",
                    "B": "Archenteron",
                    "C": "Coelom",
                    "D": "Neural canal",
                },
                "correct": "A",
            },
            {
                "question": "Which antibody is present in colostrum?",
                "options": {"A": "IgG", "B": "IgM", "C": "IgA", "D": "IgE"},
                "correct": "C",
            },
            {
                "question": "The site of fertilization in human females is:",
                "options": {
                    "A": "Ovary",
                    "B": "Uterus",
                    "C": "Fallopian tube",
                    "D": "Cervix",
                },
                "correct": "C",
            },
            {
                "question": "Which cell organelle is known as the 'powerhouse of the cell'?",
                "options": {
                    "A": "Nucleus",
                    "B": "Ribosome",
                    "C": "Mitochondria",
                    "D": "Golgi apparatus",
                },
                "correct": "C",
            },
            {
                "question": "The most primitive mammals are:",
                "options": {
                    "A": "Marsupials",
                    "B": "Placentals",
                    "C": "Monotremes",
                    "D": "Primates",
                },
                "correct": "C",
            },
            {
                "question": "Which nerve controls the movement of the diaphragm?",
                "options": {
                    "A": "Vagus nerve",
                    "B": "Phrenic nerve",
                    "C": "Intercostal nerve",
                    "D": "Hypoglossal nerve",
                },
                "correct": "B",
            },
            {
                "question": "The yellow color of urine is due to:",
                "options": {
                    "A": "Bilirubin",
                    "B": "Urochrome",
                    "C": "Hemoglobin",
                    "D": "Creatinine",
                },
                "correct": "B",
            },
            {
                "question": "The work function of a metal is 3.2 eV. The maximum kinetic energy of photoelectrons when light of wavelength 300 nm is incident on it is:",
                "options": {
                    "A": "0.94 eV",
                    "B": "1.12 eV",
                    "C": "1.94 eV",
                    "D": "4.14 eV",
                },
                "correct": "A",
            },
            {
                "question": "The de Broglie wavelength of an electron accelerated through a potential of 100 V is:",
                "options": {"A": "1.23 Å", "B": "12.3 Å", "C": "0.123 Å", "D": "123 Å"},
                "correct": "A",
            },
            {
                "question": "In Young's double slit experiment, the fringe width is:",
                "options": {
                    "A": "Directly proportional to the wavelength",
                    "B": "Inversely proportional to the distance between slits",
                    "C": "Directly proportional to the distance from screen",
                    "D": "All of the above",
                },
                "correct": "D",
            },
            {
                "question": "The electric field inside a conductor in electrostatic equilibrium is:",
                "options": {
                    "A": "Maximum",
                    "B": "Minimum",
                    "C": "Zero",
                    "D": "Varies with position",
                },
                "correct": "C",
            },
            {
                "question": "The time period of a simple pendulum on the moon (g_moon = g_earth/6) will be:",
                "options": {
                    "A": "6 times that on earth",
                    "B": "√6 times that on earth",
                    "C": "1/6 times that on earth",
                    "D": "1/√6 times that on earth",
                },
                "correct": "B",
            },
            {
                "question": "The dimensional formula of coefficient of viscosity is:",
                "options": {
                    "A": "[ML⁻¹T⁻¹]",
                    "B": "[M⁰L⁰T⁻¹]",
                    "C": "[ML⁻²T⁻²]",
                    "D": "[MLT⁻¹]",
                },
                "correct": "A",
            },
            {
                "question": "A charged particle enters a uniform magnetic field perpendicularly. The path followed is:",
                "options": {
                    "A": "Straight line",
                    "B": "Parabolic",
                    "C": "Circular",
                    "D": "Helical",
                },
                "correct": "C",
            },
            {
                "question": "The ratio of kinetic energies of a proton and an α-particle accelerated through the same potential is:",
                "options": {"A": "1:2", "B": "1:4", "C": "2:1", "D": "4:1"},
                "correct": "A",
            },
            {
                "question": "The efficiency of a Carnot engine operating between 27°C and 227°C is:",
                "options": {"A": "40%", "B": "50%", "C": "60%", "D": "80%"},
                "correct": "A",
            },
            {
                "question": "The self-inductance of a solenoid is independent of:",
                "options": {
                    "A": "Number of turns",
                    "B": "Cross-sectional area",
                    "C": "Current flowing through it",
                    "D": "Permeability of core material",
                },
                "correct": "C",
            },
            {
                "question": "The oxidation state of chromium in K₂Cr₂O₇ is:",
                "options": {"A": "+3", "B": "+6", "C": "+7", "D": "+2"},
                "correct": "B",
            },
            {
                "question": "Which of the following has the highest boiling point?",
                "options": {"A": "HF", "B": "HCl", "C": "HBr", "D": "HI"},
                "correct": "A",
            },
            {
                "question": "The hybridization of carbon in diamond is:",
                "options": {"A": "sp", "B": "sp²", "C": "sp³", "D": "sp³d"},
                "correct": "C",
            },
            {
                "question": "Which of the following is an intensive property?",
                "options": {
                    "A": "Mass",
                    "B": "Volume",
                    "C": "Density",
                    "D": "Number of moles",
                },
                "correct": "C",
            },
            {
                "question": "The number of π bonds in benzene is:",
                "options": {"A": "3", "B": "6", "C": "9", "D": "12"},
                "correct": "A",
            },
            {
                "question": "Which gas is evolved when zinc reacts with dilute HCl?",
                "options": {
                    "A": "Oxygen",
                    "B": "Chlorine",
                    "C": "Hydrogen",
                    "D": "Carbon dioxide",
                },
                "correct": "C",
            },
            {
                "question": "The IUPAC name of CH₃CH(OH)CH₃ is:",
                "options": {
                    "A": "1-propanol",
                    "B": "2-propanol",
                    "C": "Propan-1-ol",
                    "D": "Propan-2-ol",
                },
                "correct": "D",
            },
            {
                "question": "Which of the following exhibits tautomerism?",
                "options": {
                    "A": "Acetone",
                    "B": "Acetaldehyde",
                    "C": "Both A and B",
                    "D": "Neither A nor B",
                },
                "correct": "C",
            },
            {
                "question": "The shape of PCl₅ molecule is:",
                "options": {
                    "A": "Trigonal planar",
                    "B": "Tetrahedral",
                    "C": "Trigonal bipyramidal",
                    "D": "Octahedral",
                },
                "correct": "C",
            },
            {
                "question": "Which of the following is used as a catalyst in Haber's process?",
                "options": {
                    "A": "Platinum",
                    "B": "Iron",
                    "C": "Nickel",
                    "D": "Vanadium pentoxide",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct passive voice: 'The teacher teaches the students.'",
                "options": {
                    "A": "The students are taught by the teacher.",
                    "B": "The students were taught by the teacher.",
                    "C": "The students have been taught by the teacher.",
                    "D": "The students will be taught by the teacher.",
                },
                "correct": "A",
            },
            {
                "question": "Select the word that is closest in meaning to 'Ephemeral':",
                "options": {
                    "A": "Permanent",
                    "B": "Temporary",
                    "C": "Eternal",
                    "D": "Continuous",
                },
                "correct": "B",
            },
            {
                "question": "Identify the figure of speech in: 'The wind whispered through the trees.'",
                "options": {
                    "A": "Metaphor",
                    "B": "Simile",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct article: '__ honest man is respected by all.'",
                "options": {"A": "A", "B": "An", "C": "The", "D": "No article"},
                "correct": "B",
            },
            {
                "question": "Select the correctly punctuated sentence:",
                "options": {
                    "A": "The book, which I read yesterday was interesting.",
                    "B": "The book which I read yesterday, was interesting.",
                    "C": "The book, which I read yesterday, was interesting.",
                    "D": "The book which I read yesterday was interesting.",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct form: 'If I ___ you, I would accept the offer.'",
                "options": {"A": "am", "B": "were", "C": "was", "D": "will be"},
                "correct": "B",
            },
            {
                "question": "Identify the type of clause in: 'I know the man who lives next door.'",
                "options": {
                    "A": "Noun clause",
                    "B": "Adjective clause",
                    "C": "Adverb clause",
                    "D": "Independent clause",
                },
                "correct": "B",
            },
            {
                "question": "Choose the antonym of 'Verbose':",
                "options": {
                    "A": "Talkative",
                    "B": "Concise",
                    "C": "Wordy",
                    "D": "Lengthy",
                },
                "correct": "B",
            },
            {
                "question": "Select the correct spelling:",
                "options": {
                    "A": "Occurrence",
                    "B": "Occurence",
                    "C": "Occurance",
                    "D": "Occurrance",
                },
                "correct": "A",
            },
            {
                "question": "Fill in the blank with the appropriate conjunction: 'He studied hard ___ he could pass the exam.'",
                "options": {
                    "A": "so that",
                    "B": "because",
                    "C": "although",
                    "D": "unless",
                },
                "correct": "A",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["BIO005"] = sample_exam_5

    com_exam_1 = {
        "code": "COM005",
        "title": "Computer Science Entrance Exam 1",
        "duration": 50,
        "questions": [
            {
                "question": "If log₂x + log₄x = 6, then x equals:",
                "options": {"A": "16", "B": "32", "C": "64", "D": "128"},
                "correct": "A",
            },
            {
                "question": "The derivative of sin⁻¹(2x/(1+x²)) with respect to x is:",
                "options": {
                    "A": "2/(1+x²)",
                    "B": "1/(1+x²)",
                    "C": "2x/(1+x²)",
                    "D": "x/(1+x²)",
                },
                "correct": "A",
            },
            {
                "question": "If the roots of x² - 3x + k = 0 are in the ratio 2:1, then k equals:",
                "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
                "correct": "B",
            },
            {
                "question": "The value of ∫₀^π x sin x dx is:",
                "options": {"A": "π", "B": "2π", "C": "π/2", "D": "0"},
                "correct": "A",
            },
            {
                "question": "If |z₁| = |z₂| = 1 and arg(z₁/z₂) = π/3, then |z₁ + z₂| equals:",
                "options": {"A": "√3", "B": "1", "C": "2", "D": "√2"},
                "correct": "A",
            },
            {
                "question": "The number of ways to arrange the letters of MATHEMATICS is:",
                "options": {
                    "A": "4989600",
                    "B": "2494800",
                    "C": "1247400",
                    "D": "4989600",
                },
                "correct": "A",
            },
            {
                "question": "If ᶜPᵣ = 210 and ᶜCᵣ = 35, then r equals:",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct": "A",
            },
            {
                "question": "The equation of the tangent to the circle x² + y² = 25 at point (3,4) is:",
                "options": {
                    "A": "3x + 4y = 25",
                    "B": "4x + 3y = 25",
                    "C": "3x - 4y = 25",
                    "D": "4x - 3y = 25",
                },
                "correct": "A",
            },
            {
                "question": "If matrices A and B are such that AB = BA = I, then B is called:",
                "options": {
                    "A": "Transpose of A",
                    "B": "Adjoint of A",
                    "C": "Inverse of A",
                    "D": "Determinant of A",
                },
                "correct": "C",
            },
            {
                "question": "The sum of the series 1 + 2x + 3x² + 4x³ + ... to ∞ (|x| < 1) is:",
                "options": {
                    "A": "1/(1-x)²",
                    "B": "1/(1+x)²",
                    "C": "x/(1-x)²",
                    "D": "1/(1-x)",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following compounds exhibits geometrical isomerism?",
                "options": {
                    "A": "CH₃-CH₂-CH₃",
                    "B": "CH₃-CH=CH-CH₃",
                    "C": "CH₃-CH₂-OH",
                    "D": "CH₃-CO-CH₃",
                },
                "correct": "B",
            },
            {
                "question": "The hybridization of carbon in diamond is:",
                "options": {"A": "sp", "B": "sp²", "C": "sp³", "D": "sp³d"},
                "correct": "C",
            },
            {
                "question": "According to VSEPR theory, the shape of NH₃ molecule is:",
                "options": {
                    "A": "Trigonal planar",
                    "B": "Pyramidal",
                    "C": "Tetrahedral",
                    "D": "Linear",
                },
                "correct": "B",
            },
            {
                "question": "The oxidation number of chromium in K₂Cr₂O₇ is:",
                "options": {"A": "+3", "B": "+6", "C": "+7", "D": "+2"},
                "correct": "B",
            },
            {
                "question": "Which of the following is the strongest reducing agent?",
                "options": {"A": "Li", "B": "Na", "C": "K", "D": "Rb"},
                "correct": "A",
            },
            {
                "question": "The IUPAC name of CH₃-CH(CH₃)-CH₂-OH is:",
                "options": {
                    "A": "2-methylpropan-1-ol",
                    "B": "2-methylpropan-2-ol",
                    "C": "1-methylpropan-2-ol",
                    "D": "Isobutanol",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following reactions is an example of nucleophilic substitution?",
                "options": {
                    "A": "CH₃Br + OH⁻ → CH₃OH + Br⁻",
                    "B": "CH₄ + Cl₂ → CH₃Cl + HCl",
                    "C": "C₂H₄ + Br₂ → C₂H₄Br₂",
                    "D": "C₆H₆ + HNO₃ → C₆H₅NO₂ + H₂O",
                },
                "correct": "A",
            },
            {
                "question": "The pH of 0.01 M NaOH solution is:",
                "options": {"A": "12", "B": "2", "C": "10", "D": "14"},
                "correct": "A",
            },
            {
                "question": "Which of the following is an aldehyde?",
                "options": {
                    "A": "CH₃COCH₃",
                    "B": "CH₃CHO",
                    "C": "CH₃COOH",
                    "D": "CH₃OH",
                },
                "correct": "B",
            },
            {
                "question": "The number of unpaired electrons in Fe³⁺ ion is:",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct": "C",
            },
            {
                "question": "A particle moves in a circle of radius R with constant speed v. Its acceleration is:",
                "options": {
                    "A": "v²/R directed radially inward",
                    "B": "v²/R directed radially outward",
                    "C": "v/R directed tangentially",
                    "D": "Zero",
                },
                "correct": "A",
            },
            {
                "question": "The dimensional formula of angular momentum is:",
                "options": {
                    "A": "[ML²T⁻¹]",
                    "B": "[MLT⁻¹]",
                    "C": "[ML²T⁻²]",
                    "D": "[MLT⁻²]",
                },
                "correct": "A",
            },
            {
                "question": "A spring of force constant k is cut into two equal parts. The force constant of each part is:",
                "options": {"A": "k/2", "B": "k", "C": "2k", "D": "k/4"},
                "correct": "C",
            },
            {
                "question": "The work done in moving a charge q through a potential difference V is:",
                "options": {"A": "qV", "B": "q/V", "C": "V/q", "D": "q²V"},
                "correct": "A",
            },
            {
                "question": "For a photon, the relationship between energy E and momentum p is:",
                "options": {
                    "A": "E = pc",
                    "B": "E = p²c",
                    "C": "E = pc²",
                    "D": "E = p/c",
                },
                "correct": "A",
            },
            {
                "question": "The magnetic field at the center of a current-carrying circular coil is proportional to:",
                "options": {"A": "I/R", "B": "IR", "C": "I/R²", "D": "IR²"},
                "correct": "A",
            },
            {
                "question": "In Young's double slit experiment, the fringe width is:",
                "options": {"A": "λD/d", "B": "λd/D", "C": "Dd/λ", "D": "λDd"},
                "correct": "A",
            },
            {
                "question": "The de Broglie wavelength of a particle is given by:",
                "options": {"A": "h/p", "B": "hp", "C": "h/mv", "D": "Both A and C"},
                "correct": "D",
            },
            {
                "question": "The maximum kinetic energy of photoelectrons depends on:",
                "options": {
                    "A": "Intensity of light",
                    "B": "Frequency of light",
                    "C": "Time of exposure",
                    "D": "Material of the surface",
                },
                "correct": "B",
            },
            {
                "question": "The efficiency of a Carnot engine operating between temperatures T₁ and T₂ (T₁ > T₂) is:",
                "options": {
                    "A": "1 - T₂/T₁",
                    "B": "1 - T₁/T₂",
                    "C": "T₁/T₂",
                    "D": "T₂/T₁",
                },
                "correct": "A",
            },
            {
                "question": "Choose the correct passive voice: 'She is writing a letter.'",
                "options": {
                    "A": "A letter is written by her.",
                    "B": "A letter is being written by her.",
                    "C": "A letter was written by her.",
                    "D": "A letter has been written by her.",
                },
                "correct": "B",
            },
            {
                "question": "Identify the figure of speech: 'The stars danced in the sky.'",
                "options": {
                    "A": "Simile",
                    "B": "Metaphor",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct indirect speech: He said, 'I am going home.'",
                "options": {
                    "A": "He said that he is going home.",
                    "B": "He said that he was going home.",
                    "C": "He said that he will go home.",
                    "D": "He said that he goes home.",
                },
                "correct": "B",
            },
            {
                "question": "The word 'Bibliography' means:",
                "options": {
                    "A": "Study of life",
                    "B": "List of books",
                    "C": "Art of writing",
                    "D": "Study of words",
                },
                "correct": "B",
            },
            {
                "question": "Choose the one-word substitution for 'A person who speaks many languages':",
                "options": {
                    "A": "Linguist",
                    "B": "Polyglot",
                    "C": "Interpreter",
                    "D": "Translator",
                },
                "correct": "B",
            },
            {
                "question": "Identify the type of sentence: 'What a beautiful day it is!'",
                "options": {
                    "A": "Declarative",
                    "B": "Interrogative",
                    "C": "Imperative",
                    "D": "Exclamatory",
                },
                "correct": "D",
            },
            {
                "question": "Choose the correct meaning of the idiom 'Break the ice':",
                "options": {
                    "A": "To start something",
                    "B": "To end a relationship",
                    "C": "To make someone comfortable",
                    "D": "To destroy something",
                },
                "correct": "C",
            },
            {
                "question": "The plural of 'Phenomenon' is:",
                "options": {
                    "A": "Phenomenons",
                    "B": "Phenomena",
                    "C": "Phenomenas",
                    "D": "Phenomenes",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct spelling:",
                "options": {
                    "A": "Definitely",
                    "B": "Definately",
                    "C": "Definitly",
                    "D": "Definetly",
                },
                "correct": "A",
            },
            {
                "question": "The antonym of 'Verbose' is:",
                "options": {
                    "A": "Talkative",
                    "B": "Concise",
                    "C": "Eloquent",
                    "D": "Wordy",
                },
                "correct": "B",
            },
            {
                "question": "Which data structure uses LIFO (Last In First Out) principle?",
                "options": {
                    "A": "Queue",
                    "B": "Stack",
                    "C": "Array",
                    "D": "Linked List",
                },
                "correct": "B",
            },
            {
                "question": "The time complexity of binary search algorithm is:",
                "options": {
                    "A": "O(n)",
                    "B": "O(n²)",
                    "C": "O(log n)",
                    "D": "O(n log n)",
                },
                "correct": "C",
            },
            {
                "question": "Which of the following is NOT a programming paradigm?",
                "options": {
                    "A": "Object-oriented",
                    "B": "Functional",
                    "C": "Procedural",
                    "D": "Sequential",
                },
                "correct": "D",
            },
            {
                "question": "In object-oriented programming, which concept allows a class to inherit properties from another class?",
                "options": {
                    "A": "Encapsulation",
                    "B": "Inheritance",
                    "C": "Polymorphism",
                    "D": "Abstraction",
                },
                "correct": "B",
            },
            {
                "question": "Which sorting algorithm has the best average case time complexity?",
                "options": {
                    "A": "Bubble Sort",
                    "B": "Selection Sort",
                    "C": "Merge Sort",
                    "D": "Insertion Sort",
                },
                "correct": "C",
            },
            {
                "question": "The decimal number 15 in binary is:",
                "options": {"A": "1111", "B": "1110", "C": "1101", "D": "1011"},
                "correct": "A",
            },
            {
                "question": "Which of the following is a relational database management system?",
                "options": {
                    "A": "MongoDB",
                    "B": "Redis",
                    "C": "MySQL",
                    "D": "Cassandra",
                },
                "correct": "C",
            },
            {
                "question": "In networking, what does TCP stand for?",
                "options": {
                    "A": "Transfer Control Protocol",
                    "B": "Transmission Control Protocol",
                    "C": "Transport Control Protocol",
                    "D": "Terminal Control Protocol",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is used for version control?",
                "options": {"A": "Git", "B": "Docker", "C": "Jenkins", "D": "Apache"},
                "correct": "A",
            },
            {
                "question": "The primary key in a database table:",
                "options": {
                    "A": "Can have duplicate values",
                    "B": "Can be NULL",
                    "C": "Must be unique and not NULL",
                    "D": "Is optional",
                },
                "correct": "C",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["COM005"] = com_exam_1

    com_exam_2 = {
        "code": "COM005",
        "title": "Computer Science Entrance Exam 2",
        "duration": 50,
        "questions": [
            {
                "question": "If the roots of the equation x² - 3x + k = 0 are in the ratio 2:3, then the value of k is:",
                "options": {"A": "2", "B": "18/25", "C": "6/5", "D": "9/4"},
                "correct": "B",
            },
            {
                "question": "The number of ways to arrange the letters of the word 'MATHEMATICS' is:",
                "options": {
                    "A": "11!/2!2!",
                    "B": "11!/2!2!2!",
                    "C": "11!/2!",
                    "D": "11!",
                },
                "correct": "A",
            },
            {
                "question": "The derivative of sin⁻¹(2x/(1+x²)) with respect to x is:",
                "options": {
                    "A": "2/(1+x²)",
                    "B": "1/(1+x²)",
                    "C": "2x/(1+x²)",
                    "D": "4x/(1+x²)²",
                },
                "correct": "A",
            },
            {
                "question": "If |z₁| = |z₂| = |z₃| = 1 and z₁ + z₂ + z₃ = 0, then |z₁² + z₂² + z₃²| equals:",
                "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
                "correct": "C",
            },
            {
                "question": "The area of the region bounded by y = x², y = 0, x = 1, and x = 2 is:",
                "options": {"A": "7/3", "B": "8/3", "C": "5/3", "D": "4/3"},
                "correct": "A",
            },
            {
                "question": "If A = [1 2; 3 4] and B = [2 0; 1 3], then det(AB) is:",
                "options": {"A": "-10", "B": "-12", "C": "12", "D": "10"},
                "correct": "B",
            },
            {
                "question": "The coefficient of x⁵ in the expansion of (1 + x)⁸ is:",
                "options": {"A": "56", "B": "70", "C": "84", "D": "126"},
                "correct": "A",
            },
            {
                "question": "The equation of the tangent to the circle x² + y² = 25 at the point (3, 4) is:",
                "options": {
                    "A": "3x + 4y = 25",
                    "B": "4x + 3y = 25",
                    "C": "3x - 4y = 25",
                    "D": "4x - 3y = 25",
                },
                "correct": "A",
            },
            {
                "question": "If the vectors a⃗ = î + 2ĵ + 3k̂ and b⃗ = 3î + 2ĵ + k̂, then a⃗ × b⃗ is:",
                "options": {
                    "A": "-4î + 8ĵ - 4k̂",
                    "B": "4î - 8ĵ + 4k̂",
                    "C": "-4î - 8ĵ + 4k̂",
                    "D": "4î + 8ĵ - 4k̂",
                },
                "correct": "A",
            },
            {
                "question": "The value of ∫₀^(π/2) sin²x dx is:",
                "options": {"A": "π/2", "B": "π/4", "C": "π/8", "D": "1"},
                "correct": "B",
            },
            {
                "question": "Which of the following compounds shows geometrical isomerism?",
                "options": {
                    "A": "CH₃CH₂CH₂CH₃",
                    "B": "CH₃CH=CHCH₃",
                    "C": "CH₃CH₂OH",
                    "D": "CH₃COCH₃",
                },
                "correct": "B",
            },
            {
                "question": "The IUPAC name of CH₃CH(OH)CH₂CH₃ is:",
                "options": {
                    "A": "2-butanol",
                    "B": "1-butanol",
                    "C": "3-butanol",
                    "D": "sec-butanol",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following has the highest boiling point?",
                "options": {"A": "HF", "B": "HCl", "C": "HBr", "D": "HI"},
                "correct": "A",
            },
            {
                "question": "The hybridization of carbon in diamond is:",
                "options": {"A": "sp", "B": "sp²", "C": "sp³", "D": "sp³d"},
                "correct": "C",
            },
            {
                "question": "Which quantum number determines the shape of an orbital?",
                "options": {
                    "A": "Principal (n)",
                    "B": "Azimuthal (l)",
                    "C": "Magnetic (m)",
                    "D": "Spin (s)",
                },
                "correct": "B",
            },
            {
                "question": "The rate of a first-order reaction is 0.04 mol L⁻¹ s⁻¹ when the concentration is 0.2 M. The rate constant is:",
                "options": {
                    "A": "0.2 s⁻¹",
                    "B": "0.008 s⁻¹",
                    "C": "5 s⁻¹",
                    "D": "0.04 s⁻¹",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following is an example of a coordination compound?",
                "options": {
                    "A": "NaCl",
                    "B": "[Cu(NH₃)₄]SO₄",
                    "C": "H₂SO₄",
                    "D": "CH₄",
                },
                "correct": "B",
            },
            {
                "question": "The oxidation number of Cr in K₂Cr₂O₇ is:",
                "options": {"A": "+6", "B": "+7", "C": "+3", "D": "+2"},
                "correct": "A",
            },
            {
                "question": "Which of the following is not an aldol condensation product?",
                "options": {
                    "A": "CH₃CH(OH)CH₂CHO",
                    "B": "CH₃CH=CHCHO",
                    "C": "CH₃COOH",
                    "D": "C₆H₅CH=CHCHO",
                },
                "correct": "C",
            },
            {
                "question": "The pH of 0.01 M NaOH solution is:",
                "options": {"A": "12", "B": "2", "C": "10", "D": "14"},
                "correct": "A",
            },
            {
                "question": "A particle moves in a circle of radius R with constant angular velocity ω. Its centripetal acceleration is:",
                "options": {"A": "ω²R", "B": "ωR", "C": "ω/R", "D": "ω²/R"},
                "correct": "A",
            },
            {
                "question": "The work function of a metal is 4 eV. The maximum kinetic energy of photoelectrons when light of energy 6 eV is incident on it is:",
                "options": {"A": "2 eV", "B": "4 eV", "C": "6 eV", "D": "10 eV"},
                "correct": "A",
            },
            {
                "question": "A wire of resistance R is stretched to double its length. Its new resistance becomes:",
                "options": {"A": "R/2", "B": "2R", "C": "4R", "D": "R/4"},
                "correct": "C",
            },
            {
                "question": "The de Broglie wavelength of an electron moving with velocity v is:",
                "options": {"A": "h/mv", "B": "mv/h", "C": "hv/m", "D": "m/hv"},
                "correct": "A",
            },
            {
                "question": "In Young's double slit experiment, the fringe width is proportional to:",
                "options": {"A": "1/λ", "B": "λ", "C": "1/D", "D": "d"},
                "correct": "B",
            },
            {
                "question": "The magnetic field at the center of a circular coil of radius R carrying current I is:",
                "options": {
                    "A": "μ₀I/2R",
                    "B": "μ₀I/4πR",
                    "C": "μ₀I/2πR",
                    "D": "μ₀IR/2",
                },
                "correct": "A",
            },
            {
                "question": "A capacitor of capacitance C is charged to potential V. The energy stored is:",
                "options": {"A": "CV", "B": "CV²", "C": "CV²/2", "D": "2CV²"},
                "correct": "C",
            },
            {
                "question": "The escape velocity from Earth's surface is approximately:",
                "options": {
                    "A": "7.9 km/s",
                    "B": "11.2 km/s",
                    "C": "9.8 km/s",
                    "D": "15.0 km/s",
                },
                "correct": "B",
            },
            {
                "question": "In an LCR circuit at resonance, the impedance is:",
                "options": {
                    "A": "Maximum",
                    "B": "Minimum",
                    "C": "Zero",
                    "D": "Infinite",
                },
                "correct": "B",
            },
            {
                "question": "The binding energy per nucleon is maximum for:",
                "options": {
                    "A": "Hydrogen",
                    "B": "Iron",
                    "C": "Uranium",
                    "D": "Helium",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct passive voice form: 'The teacher explained the lesson.'",
                "options": {
                    "A": "The lesson is explained by the teacher.",
                    "B": "The lesson was explained by the teacher.",
                    "C": "The lesson has been explained by the teacher.",
                    "D": "The lesson will be explained by the teacher.",
                },
                "correct": "B",
            },
            {
                "question": "Identify the figure of speech in: 'The classroom was a zoo.'",
                "options": {
                    "A": "Simile",
                    "B": "Metaphor",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct meaning of the idiom 'Break the ice':",
                "options": {
                    "A": "To start a conversation",
                    "B": "To break something made of ice",
                    "C": "To be very cold",
                    "D": "To stop talking",
                },
                "correct": "A",
            },
            {
                "question": "Select the sentence with correct subject-verb agreement:",
                "options": {
                    "A": "Neither of the boys were present.",
                    "B": "Each of the students have a book.",
                    "C": "Either John or his friends are coming.",
                    "D": "The team is playing well.",
                },
                "correct": "D",
            },
            {
                "question": "Choose the correct form: 'I wish I ___ there yesterday.'",
                "options": {"A": "was", "B": "were", "C": "had been", "D": "have been"},
                "correct": "C",
            },
            {
                "question": "Identify the type of clause: 'Although it was raining, we went out.'",
                "options": {
                    "A": "Noun clause",
                    "B": "Adjective clause",
                    "C": "Adverb clause",
                    "D": "Independent clause",
                },
                "correct": "C",
            },
            {
                "question": "Choose the antonym of 'Ephemeral':",
                "options": {
                    "A": "Temporary",
                    "B": "Permanent",
                    "C": "Brief",
                    "D": "Short-lived",
                },
                "correct": "B",
            },
            {
                "question": "Select the correctly punctuated sentence:",
                "options": {
                    "A": "The book, that I bought yesterday is interesting.",
                    "B": "The book that I bought yesterday, is interesting.",
                    "C": "The book that I bought yesterday is interesting.",
                    "D": "The book, that I bought, yesterday is interesting.",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct preposition: 'He is good ___ mathematics.'",
                "options": {"A": "in", "B": "at", "C": "on", "D": "with"},
                "correct": "B",
            },
            {
                "question": "Identify the correct reported speech: He said, 'I am going home.'",
                "options": {
                    "A": "He said that he is going home.",
                    "B": "He said that he was going home.",
                    "C": "He said that he will go home.",
                    "D": "He said that he goes home.",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is not a valid variable name in most programming languages?",
                "options": {
                    "A": "myVariable",
                    "B": "_variable",
                    "C": "2variable",
                    "D": "variable2",
                },
                "correct": "C",
            },
            {
                "question": "In object-oriented programming, which concept allows a class to inherit properties from another class?",
                "options": {
                    "A": "Encapsulation",
                    "B": "Polymorphism",
                    "C": "Inheritance",
                    "D": "Abstraction",
                },
                "correct": "C",
            },
            {
                "question": "What is the time complexity of binary search?",
                "options": {"A": "O(n)", "B": "O(n²)", "C": "O(log n)", "D": "O(1)"},
                "correct": "C",
            },
            {
                "question": "Which data structure follows the LIFO (Last In First Out) principle?",
                "options": {
                    "A": "Queue",
                    "B": "Stack",
                    "C": "Array",
                    "D": "Linked List",
                },
                "correct": "B",
            },
            {
                "question": "In a relational database, a primary key:",
                "options": {
                    "A": "Can have duplicate values",
                    "B": "Can be NULL",
                    "C": "Uniquely identifies each record",
                    "D": "Is always numeric",
                },
                "correct": "C",
            },
            {
                "question": "Which of the following is a scripting language?",
                "options": {"A": "C++", "B": "Java", "C": "Python", "D": "Assembly"},
                "correct": "C",
            },
            {
                "question": "What does HTML stand for?",
                "options": {
                    "A": "High Tech Markup Language",
                    "B": "HyperText Markup Language",
                    "C": "Home Tool Markup Language",
                    "D": "Hyperlink and Text Markup Language",
                },
                "correct": "B",
            },
            {
                "question": "In binary number system, what is the decimal equivalent of 1101?",
                "options": {"A": "11", "B": "12", "C": "13", "D": "14"},
                "correct": "C",
            },
            {
                "question": "Which sorting algorithm has the best average-case time complexity?",
                "options": {
                    "A": "Bubble Sort",
                    "B": "Selection Sort",
                    "C": "Quick Sort",
                    "D": "Insertion Sort",
                },
                "correct": "C",
            },
            {
                "question": "What is the purpose of a compiler?",
                "options": {
                    "A": "To execute programs",
                    "B": "To debug programs",
                    "C": "To translate source code into machine code",
                    "D": "To manage memory",
                },
                "correct": "C",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["COM002"] = com_exam_2

    com_exam_3 = {
        "code": "COM005",
        "title": "Computer Science Entrance Exam 3",
        "duration": 50,
        "questions": [
            {
                "question": "If the function f(x) = x³ - 6x² + 11x - 6 has roots α, β, γ, then the value of α² + β² + γ² is:",
                "options": {"A": "14", "B": "16", "C": "18", "D": "20"},
                "correct": "A",
            },
            {
                "question": "The number of solutions of the equation sin⁻¹x = 2cos⁻¹x in [-1, 1] is:",
                "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
                "correct": "B",
            },
            {
                "question": "If the vectors a⃗ = î + 2ĵ + 3k̂ and b⃗ = 3î + 2ĵ + k̂, then the unit vector perpendicular to both a⃗ and b⃗ is:",
                "options": {
                    "A": "(4î + 8ĵ - 4k̂)/√96",
                    "B": "(-4î + 8ĵ - 4k̂)/√96",
                    "C": "(4î - 8ĵ + 4k̂)/√96",
                    "D": "(-4î - 8ĵ + 4k̂)/√96",
                },
                "correct": "B",
            },
            {
                "question": "The derivative of f(x) = sin⁻¹(2x/(1+x²)) with respect to x is:",
                "options": {
                    "A": "2/(1+x²)",
                    "B": "1/(1+x²)",
                    "C": "2x/(1+x²)",
                    "D": "x/(1+x²)",
                },
                "correct": "A",
            },
            {
                "question": "If ∫₀^π x sin x dx = k, then the value of k is:",
                "options": {"A": "π", "B": "2π", "C": "π/2", "D": "0"},
                "correct": "A",
            },
            {
                "question": "The probability that in a family of 4 children, there are exactly 2 boys and 2 girls is:",
                "options": {"A": "3/8", "B": "1/4", "C": "1/2", "D": "5/8"},
                "correct": "A",
            },
            {
                "question": "If z = 1 + i, then z^8 equals:",
                "options": {"A": "16", "B": "-16", "C": "16i", "D": "-16i"},
                "correct": "A",
            },
            {
                "question": "The equation of the tangent to the circle x² + y² = 25 at the point (3, 4) is:",
                "options": {
                    "A": "3x + 4y = 25",
                    "B": "4x + 3y = 25",
                    "C": "3x - 4y = 25",
                    "D": "4x - 3y = 25",
                },
                "correct": "A",
            },
            {
                "question": "If the coefficient of x^r in the expansion of (1 + x)^n is equal to the coefficient of x^(r+1), then r equals:",
                "options": {"A": "(n-1)/2", "B": "n/2", "C": "(n+1)/2", "D": "n-1"},
                "correct": "A",
            },
            {
                "question": "The area bounded by the curves y = x² and y = 2x - x² is:",
                "options": {"A": "4/3", "B": "2/3", "C": "1/3", "D": "8/3"},
                "correct": "A",
            },
            {
                "question": "The hybridization of carbon atoms in ethyne (C₂H₂) is:",
                "options": {"A": "sp³", "B": "sp²", "C": "sp", "D": "sp³d"},
                "correct": "C",
            },
            {
                "question": "Which of the following has the highest boiling point?",
                "options": {"A": "HF", "B": "HCl", "C": "HBr", "D": "HI"},
                "correct": "A",
            },
            {
                "question": "The oxidation state of chromium in K₂Cr₂O₇ is:",
                "options": {"A": "+6", "B": "+7", "C": "+5", "D": "+4"},
                "correct": "A",
            },
            {
                "question": "Which of the following is an example of a nucleophilic substitution reaction?",
                "options": {
                    "A": "CH₃Cl + OH⁻ → CH₃OH + Cl⁻",
                    "B": "C₂H₄ + Br₂ → C₂H₄Br₂",
                    "C": "C₆H₆ + Cl₂ → C₆H₅Cl + HCl",
                    "D": "CH₄ + Cl₂ → CH₃Cl + HCl",
                },
                "correct": "A",
            },
            {
                "question": "The IUPAC name of CH₃-CH(CH₃)-CH₂-COOH is:",
                "options": {
                    "A": "3-methylbutanoic acid",
                    "B": "2-methylbutanoic acid",
                    "C": "3-methylpropanoic acid",
                    "D": "2-methylpropanoic acid",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following exhibits tautomerism?",
                "options": {
                    "A": "Acetone",
                    "B": "Acetaldehyde",
                    "C": "Benzene",
                    "D": "Methanol",
                },
                "correct": "B",
            },
            {
                "question": "The number of stereoisomers of 2,3-dibromobutane is:",
                "options": {"A": "2", "B": "3", "C": "4", "D": "6"},
                "correct": "B",
            },
            {
                "question": "Which catalyst is used in the Haber process for ammonia synthesis?",
                "options": {
                    "A": "Platinum",
                    "B": "Iron",
                    "C": "Nickel",
                    "D": "Vanadium pentoxide",
                },
                "correct": "B",
            },
            {
                "question": "The pH of 0.1 M solution of weak acid (Ka = 10⁻⁵) is approximately:",
                "options": {"A": "2", "B": "3", "C": "4", "D": "5"},
                "correct": "B",
            },
            {
                "question": "Which of the following compounds will exhibit geometrical isomerism?",
                "options": {
                    "A": "CH₃CH=CHCH₃",
                    "B": "CH₃CH=CH₂",
                    "C": "CH₂=CH₂",
                    "D": "CH₃CH₂CH=CH₂",
                },
                "correct": "A",
            },
            {
                "question": "A particle moves in a circle of radius r with constant angular velocity ω. Its centripetal acceleration is:",
                "options": {"A": "ω²r", "B": "ωr", "C": "ω/r", "D": "ω²/r"},
                "correct": "A",
            },
            {
                "question": "The de Broglie wavelength of an electron moving with velocity v is:",
                "options": {"A": "h/mv", "B": "mv/h", "C": "h/m", "D": "mv/c"},
                "correct": "A",
            },
            {
                "question": "Two resistors of 4Ω and 6Ω are connected in parallel. The equivalent resistance is:",
                "options": {"A": "2.4Ω", "B": "10Ω", "C": "5Ω", "D": "1.2Ω"},
                "correct": "A",
            },
            {
                "question": "The work function of a metal is 2.5 eV. The maximum kinetic energy of photoelectrons when light of frequency 10¹⁵ Hz is incident on it is: (h = 6.63 × 10⁻³⁴ J·s, 1 eV = 1.6 × 10⁻¹⁹ J)",
                "options": {
                    "A": "1.64 eV",
                    "B": "2.64 eV",
                    "C": "3.64 eV",
                    "D": "4.64 eV",
                },
                "correct": "A",
            },
            {
                "question": "A convex lens of focal length 20 cm forms a real image at a distance of 60 cm from the lens. The object distance is:",
                "options": {"A": "30 cm", "B": "15 cm", "C": "12 cm", "D": "10 cm"},
                "correct": "A",
            },
            {
                "question": "The magnetic field at the center of a circular coil carrying current I and having n turns of radius r is:",
                "options": {
                    "A": "μ₀nI/2r",
                    "B": "μ₀nI/r",
                    "C": "μ₀I/2r",
                    "D": "2μ₀nI/r",
                },
                "correct": "A",
            },
            {
                "question": "In Young's double slit experiment, if the distance between slits is doubled, the fringe width:",
                "options": {
                    "A": "becomes half",
                    "B": "becomes double",
                    "C": "remains same",
                    "D": "becomes four times",
                },
                "correct": "A",
            },
            {
                "question": "The energy stored in a capacitor of capacitance C charged to potential V is:",
                "options": {"A": "½CV²", "B": "CV²", "C": "½CV", "D": "2CV²"},
                "correct": "A",
            },
            {
                "question": "For a satellite in circular orbit around Earth, the ratio of kinetic energy to potential energy is:",
                "options": {"A": "-1/2", "B": "1/2", "C": "-1", "D": "1"},
                "correct": "A",
            },
            {
                "question": "The dimensional formula of coefficient of viscosity is:",
                "options": {
                    "A": "[ML⁻¹T⁻¹]",
                    "B": "[MLT⁻¹]",
                    "C": "[ML⁻²T⁻¹]",
                    "D": "[ML²T⁻¹]",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following sentences uses the subjunctive mood correctly?",
                "options": {
                    "A": "If I was rich, I would travel the world",
                    "B": "If I were rich, I would travel the world",
                    "C": "If I am rich, I would travel the world",
                    "D": "If I will be rich, I would travel the world",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct meaning of the idiom 'break the ice':",
                "options": {
                    "A": "To start a conversation",
                    "B": "To break something",
                    "C": "To be very cold",
                    "D": "To finish a task",
                },
                "correct": "A",
            },
            {
                "question": "Identify the figure of speech in: 'The wind whispered through the trees':",
                "options": {
                    "A": "Metaphor",
                    "B": "Simile",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct passive voice form: 'They are building a new hospital':",
                "options": {
                    "A": "A new hospital is being built by them",
                    "B": "A new hospital was being built by them",
                    "C": "A new hospital is built by them",
                    "D": "A new hospital has been built by them",
                },
                "correct": "A",
            },
            {
                "question": "Select the word that best completes the analogy: Book : Author :: Painting : ?",
                "options": {"A": "Canvas", "B": "Artist", "C": "Color", "D": "Gallery"},
                "correct": "B",
            },
            {
                "question": "Choose the correct form: 'Neither of the students ___ present today':",
                "options": {"A": "are", "B": "is", "C": "were", "D": "have been"},
                "correct": "B",
            },
            {
                "question": "Identify the type of clause in: 'When she arrived, everyone was waiting':",
                "options": {
                    "A": "Noun clause",
                    "B": "Adjective clause",
                    "C": "Adverb clause",
                    "D": "Independent clause",
                },
                "correct": "C",
            },
            {
                "question": "Choose the antonym of 'Ephemeral':",
                "options": {
                    "A": "Temporary",
                    "B": "Permanent",
                    "C": "Brief",
                    "D": "Fleeting",
                },
                "correct": "B",
            },
            {
                "question": "Select the correctly punctuated sentence:",
                "options": {
                    "A": "The teacher said, 'Complete your homework.'",
                    "B": 'The teacher said, "Complete your homework".',
                    "C": "The teacher said 'Complete your homework'.",
                    "D": "The teacher said; 'Complete your homework.'",
                },
                "correct": "A",
            },
            {
                "question": "Identify the error in: 'Each of the boys have completed their assignment':",
                "options": {
                    "A": "Subject-verb disagreement",
                    "B": "Wrong pronoun",
                    "C": "Wrong tense",
                    "D": "No error",
                },
                "correct": "A",
            },
            {
                "question": "Which data structure uses LIFO (Last In First Out) principle?",
                "options": {
                    "A": "Queue",
                    "B": "Stack",
                    "C": "Array",
                    "D": "Linked List",
                },
                "correct": "B",
            },
            {
                "question": "In Object-Oriented Programming, which concept allows a class to inherit properties from another class?",
                "options": {
                    "A": "Encapsulation",
                    "B": "Polymorphism",
                    "C": "Inheritance",
                    "D": "Abstraction",
                },
                "correct": "C",
            },
            {
                "question": "What is the time complexity of binary search algorithm?",
                "options": {
                    "A": "O(n)",
                    "B": "O(log n)",
                    "C": "O(n²)",
                    "D": "O(n log n)",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is not a programming paradigm?",
                "options": {
                    "A": "Procedural",
                    "B": "Object-Oriented",
                    "C": "Functional",
                    "D": "Sequential",
                },
                "correct": "D",
            },
            {
                "question": "In a relational database, what does SQL stand for?",
                "options": {
                    "A": "Simple Query Language",
                    "B": "Structured Query Language",
                    "C": "Standard Query Language",
                    "D": "System Query Language",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following is a correct way to declare an array in C++?",
                "options": {
                    "A": "int arr[10];",
                    "B": "array int arr[10];",
                    "C": "int array arr[10];",
                    "D": "declare int arr[10];",
                },
                "correct": "A",
            },
            {
                "question": "What does HTML stand for?",
                "options": {
                    "A": "Hyper Text Markup Language",
                    "B": "High Tech Modern Language",
                    "C": "Home Tool Markup Language",
                    "D": "Hyperlink and Text Markup Language",
                },
                "correct": "A",
            },
            {
                "question": "Which sorting algorithm has the best average-case time complexity?",
                "options": {
                    "A": "Bubble Sort",
                    "B": "Selection Sort",
                    "C": "Quick Sort",
                    "D": "Insertion Sort",
                },
                "correct": "C",
            },
            {
                "question": "In computer networks, what does IP stand for?",
                "options": {
                    "A": "Internet Protocol",
                    "B": "Internal Protocol",
                    "C": "International Protocol",
                    "D": "Information Protocol",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following is used to connect multiple networks?",
                "options": {"A": "Hub", "B": "Switch", "C": "Router", "D": "Repeater"},
                "correct": "C",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["COM003"] = com_exam_3
    com_exam_4 = {
        "code": "COM005",
        "title": "Computer Science Entrance Exam 4",
        "duration": 50,
        "questions": [
            {
                "question": "If the sum of first n terms of an AP is 3n² + 2n, then the common difference is:",
                "options": {"A": "6", "B": "5", "C": "4", "D": "3"},
                "correct": "A",
            },
            {
                "question": "The number of ways to arrange the letters of the word 'MATHEMATICS' is:",
                "options": {
                    "A": "11!/2!2!",
                    "B": "11!/2!2!2!",
                    "C": "11!/4!2!",
                    "D": "11!/2!4!",
                },
                "correct": "B",
            },
            {
                "question": "If sin θ + cos θ = √2, then the value of tan θ + cot θ is:",
                "options": {"A": "1", "B": "2", "C": "√2", "D": "2√2"},
                "correct": "B",
            },
            {
                "question": "The area of the region bounded by y = |x| and y = 1 is:",
                "options": {"A": "1", "B": "2", "C": "3", "D": "4"},
                "correct": "B",
            },
            {
                "question": "If A = [1 2; 3 4], then A⁻¹ equals:",
                "options": {
                    "A": "[-2 1; 3/2 -1/2]",
                    "B": "[4 -2; -3 1]/(-2)",
                    "C": "[-4 2; 3 -1]/2",
                    "D": "[4 -2; -3 1]/2",
                },
                "correct": "B",
            },
            {
                "question": "The coefficient of x⁵ in the expansion of (1+x)¹⁰ is:",
                "options": {"A": "126", "B": "210", "C": "252", "D": "300"},
                "correct": "C",
            },
            {
                "question": "The equation of the parabola with vertex at origin and focus at (2,0) is:",
                "options": {
                    "A": "y² = 8x",
                    "B": "y² = 4x",
                    "C": "x² = 8y",
                    "D": "y² = 2x",
                },
                "correct": "A",
            },
            {
                "question": "If lim(x→0) (sin ax)/(sin bx) = 2, then a/b equals:",
                "options": {"A": "1/2", "B": "2", "C": "1", "D": "4"},
                "correct": "B",
            },
            {
                "question": "The distance between the parallel lines 3x + 4y + 5 = 0 and 3x + 4y - 10 = 0 is:",
                "options": {"A": "2", "B": "3", "C": "5", "D": "15"},
                "correct": "B",
            },
            {
                "question": "If f(x) = e^(x²), then f'(x) equals:",
                "options": {
                    "A": "2x·e^(x²)",
                    "B": "x²·e^(x²)",
                    "C": "e^(2x)",
                    "D": "2e^(x²)",
                },
                "correct": "A",
            },
            {
                "question": "The geometry around the central atom in SF₆ is:",
                "options": {
                    "A": "Tetrahedral",
                    "B": "Octahedral",
                    "C": "Square planar",
                    "D": "Trigonal bipyramidal",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following has maximum bond angle?",
                "options": {"A": "NH₃", "B": "H₂O", "C": "CH₄", "D": "H₂S"},
                "correct": "C",
            },
            {
                "question": "The number of unpaired electrons in Fe³⁺ (Z=26) is:",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct": "C",
            },
            {
                "question": "Which of the following is the strongest acid?",
                "options": {"A": "HF", "B": "HCl", "C": "HBr", "D": "HI"},
                "correct": "D",
            },
            {
                "question": "The major product of the reaction CH₃CH₂Br + KOH (alcoholic) → is:",
                "options": {
                    "A": "CH₃CH₂OH",
                    "B": "CH₂=CH₂",
                    "C": "CH₃CHO",
                    "D": "CH₃COOH",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following shows +2 oxidation state most readily?",
                "options": {"A": "Ge", "B": "Sn", "C": "Pb", "D": "C"},
                "correct": "C",
            },
            {
                "question": "The entropy change for the process H₂O(s) → H₂O(l) at 0°C is:",
                "options": {
                    "A": "Positive",
                    "B": "Negative",
                    "C": "Zero",
                    "D": "Cannot be determined",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following is a biodegradable polymer?",
                "options": {
                    "A": "Polyethylene",
                    "B": "Polystyrene",
                    "C": "Polyhydroxybutyrate",
                    "D": "PVC",
                },
                "correct": "C",
            },
            {
                "question": "The coordination number of Ni in [Ni(CO)₄] is:",
                "options": {"A": "2", "B": "4", "C": "6", "D": "8"},
                "correct": "B",
            },
            {
                "question": "Which vitamin is synthesized in human body?",
                "options": {
                    "A": "Vitamin A",
                    "B": "Vitamin B₁₂",
                    "C": "Vitamin D",
                    "D": "Vitamin E",
                },
                "correct": "C",
            },
            {
                "question": "A block of mass 2 kg is placed on a rough inclined plane of angle 30°. If μ = 0.5, the acceleration down the plane is: (g = 10 m/s²)",
                "options": {
                    "A": "0.67 m/s²",
                    "B": "1.34 m/s²",
                    "C": "2.5 m/s²",
                    "D": "5 m/s²",
                },
                "correct": "B",
            },
            {
                "question": "The escape velocity from Earth's surface is approximately:",
                "options": {
                    "A": "7.9 km/s",
                    "B": "11.2 km/s",
                    "C": "15.0 km/s",
                    "D": "21.1 km/s",
                },
                "correct": "B",
            },
            {
                "question": "In SHM, when the displacement is half of the amplitude, the ratio of kinetic energy to potential energy is:",
                "options": {"A": "1:3", "B": "3:1", "C": "1:1", "D": "2:1"},
                "correct": "B",
            },
            {
                "question": "The binding energy per nucleon is maximum for:",
                "options": {
                    "A": "Hydrogen",
                    "B": "Helium",
                    "C": "Iron",
                    "D": "Uranium",
                },
                "correct": "C",
            },
            {
                "question": "For a gas following van der Waals equation, the compressibility factor Z at high pressure is:",
                "options": {
                    "A": "Less than 1",
                    "B": "Greater than 1",
                    "C": "Equal to 1",
                    "D": "Zero",
                },
                "correct": "B",
            },
            {
                "question": "The phase difference between electric and magnetic field vectors in an electromagnetic wave is:",
                "options": {"A": "0", "B": "π/4", "C": "π/2", "D": "π"},
                "correct": "A",
            },
            {
                "question": "In a step-up transformer with turn ratio 1:10, if the primary current is 10 A, the secondary current is:",
                "options": {"A": "100 A", "B": "10 A", "C": "1 A", "D": "0.1 A"},
                "correct": "C",
            },
            {
                "question": "The intensity of sound waves is proportional to:",
                "options": {
                    "A": "Amplitude",
                    "B": "Square of amplitude",
                    "C": "Frequency",
                    "D": "Square of frequency",
                },
                "correct": "B",
            },
            {
                "question": "The drift velocity of electrons in a conductor is of the order of:",
                "options": {
                    "A": "10⁸ m/s",
                    "B": "10⁶ m/s",
                    "C": "10⁻⁴ m/s",
                    "D": "10⁻⁶ m/s",
                },
                "correct": "C",
            },
            {
                "question": "The total energy of an electron in the nth orbit of hydrogen atom is proportional to:",
                "options": {"A": "n", "B": "1/n", "C": "n²", "D": "1/n²"},
                "correct": "D",
            },
            {
                "question": "Choose the correct sentence:",
                "options": {
                    "A": "One of my friends are coming",
                    "B": "One of my friends is coming",
                    "C": "One of my friend is coming",
                    "D": "One of my friend are coming",
                },
                "correct": "B",
            },
            {
                "question": "The synonym of 'Ubiquitous' is:",
                "options": {
                    "A": "Rare",
                    "B": "Omnipresent",
                    "C": "Ancient",
                    "D": "Modern",
                },
                "correct": "B",
            },
            {
                "question": "Identify the type of sentence: 'Although it was raining, we went out':",
                "options": {
                    "A": "Simple",
                    "B": "Compound",
                    "C": "Complex",
                    "D": "Compound-Complex",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct preposition: 'He is good ___ mathematics':",
                "options": {"A": "in", "B": "at", "C": "on", "D": "with"},
                "correct": "B",
            },
            {
                "question": "The past participle of 'arise' is:",
                "options": {"A": "arised", "B": "arose", "C": "arisen", "D": "arising"},
                "correct": "C",
            },
            {
                "question": "Choose the correctly spelled word:",
                "options": {
                    "A": "Accommodate",
                    "B": "Accomodate",
                    "C": "Acomodate",
                    "D": "Acommodate",
                },
                "correct": "A",
            },
            {
                "question": "The literary device used in 'Peter Piper picked a peck of pickled peppers' is:",
                "options": {
                    "A": "Alliteration",
                    "B": "Assonance",
                    "C": "Consonance",
                    "D": "Onomatopoeia",
                },
                "correct": "A",
            },
            {
                "question": "Choose the correct indirect speech: He said, 'I am going home':",
                "options": {
                    "A": "He said that he is going home",
                    "B": "He said that he was going home",
                    "C": "He said that he will go home",
                    "D": "He said that he goes home",
                },
                "correct": "B",
            },
            {
                "question": "The meaning of the phrase 'break a leg' is:",
                "options": {
                    "A": "To injure oneself",
                    "B": "Good luck",
                    "C": "To fail",
                    "D": "To work hard",
                },
                "correct": "B",
            },
            {
                "question": "Identify the error: 'Neither John nor his friends was present':",
                "options": {
                    "A": "Subject-verb disagreement",
                    "B": "Wrong pronoun",
                    "C": "Wrong preposition",
                    "D": "No error",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following is a non-linear data structure?",
                "options": {"A": "Array", "B": "Stack", "C": "Queue", "D": "Tree"},
                "correct": "D",
            },
            {
                "question": "In which programming language was the first compiler written?",
                "options": {
                    "A": "Assembly language",
                    "B": "Machine language",
                    "C": "FORTRAN",
                    "D": "COBOL",
                },
                "correct": "A",
            },
            {
                "question": "What is the maximum number of nodes at level 'l' of a binary tree?",
                "options": {"A": "2^l", "B": "2^(l-1)", "C": "2*l", "D": "l^2"},
                "correct": "A",
            },
            {
                "question": "Which protocol is used for secure communication over the internet?",
                "options": {"A": "HTTP", "B": "FTP", "C": "HTTPS", "D": "SMTP"},
                "correct": "C",
            },
            {
                "question": "In database normalization, which normal form eliminates transitive dependency?",
                "options": {"A": "1NF", "B": "2NF", "C": "3NF", "D": "BCNF"},
                "correct": "C",
            },
            {
                "question": "What does CPU stand for?",
                "options": {
                    "A": "Central Processing Unit",
                    "B": "Computer Processing Unit",
                    "C": "Central Program Unit",
                    "D": "Computer Program Unit",
                },
                "correct": "A",
            },
            {
                "question": "Which of the following is not a valid identifier in most programming languages?",
                "options": {
                    "A": "_variable",
                    "B": "variable123",
                    "C": "123variable",
                    "D": "Variable_",
                },
                "correct": "C",
            },
            {
                "question": "The space complexity of recursive fibonacci algorithm is:",
                "options": {"A": "O(1)", "B": "O(n)", "C": "O(log n)", "D": "O(n²)"},
                "correct": "B",
            },
            {
                "question": "Which layer of OSI model is responsible for routing?",
                "options": {
                    "A": "Physical Layer",
                    "B": "Data Link Layer",
                    "C": "Network Layer",
                    "D": "Transport Layer",
                },
                "correct": "C",
            },
            {
                "question": "In operating systems, what is deadlock?",
                "options": {
                    "A": "Process termination",
                    "B": "Memory overflow",
                    "C": "Circular wait condition",
                    "D": "File corruption",
                },
                "correct": "C",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["COM005"] = com_exam_4

    com_exam_5 = {
        "code": "COM005",
        "title": "Computer Science Entrance Exam 5",
        "duration": 50,
        "questions": [
            {
                "question": "If the roots of the equation x² - px + q = 0 are α and β, then the equation whose roots are α² and β² is:",
                "options": {
                    "A": "x² - (p² - 2q)x + q² = 0",
                    "B": "x² - (p² + 2q)x + q² = 0",
                    "C": "x² + (p² - 2q)x - q² = 0",
                    "D": "x² - (p² - 2q)x - q² = 0",
                },
                "correct": "A",
            },
            {
                "question": "The value of ∫₀^π sin⁴x dx is:",
                "options": {"A": "π/2", "B": "3π/8", "C": "π/4", "D": "π/8"},
                "correct": "B",
            },
            {
                "question": "If |z₁| = |z₂| = |z₃| = 1 and z₁ + z₂ + z₃ = 0, then |z₁² + z₂² + z₃²| equals:",
                "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
                "correct": "C",
            },
            {
                "question": "The number of ways to arrange the letters of the word 'BANANA' is:",
                "options": {"A": "60", "B": "120", "C": "720", "D": "360"},
                "correct": "A",
            },
            {
                "question": "If the position vector of a point P is r⃗ = 2î + 3ĵ - k̂, then the distance of P from the origin is:",
                "options": {"A": "√6", "B": "√14", "C": "√10", "D": "√12"},
                "correct": "B",
            },
            {
                "question": "The eccentricity of the hyperbola 9x² - 16y² = 144 is:",
                "options": {"A": "5/4", "B": "5/3", "C": "4/3", "D": "3/4"},
                "correct": "A",
            },
            {
                "question": "If f(x) = x³ - 3x + 2, then the number of real roots of f(x) = 0 is:",
                "options": {"A": "1", "B": "2", "C": "3", "D": "0"},
                "correct": "C",
            },
            {
                "question": "The sum of the series 1 + 3x + 5x² + 7x³ + ... to infinity, where |x| < 1, is:",
                "options": {
                    "A": "(1+x)/(1-x)²",
                    "B": "(1-x)/(1+x)²",
                    "C": "1/(1-x)²",
                    "D": "(1+x)²/(1-x)",
                },
                "correct": "A",
            },
            {
                "question": "The derivative of tan⁻¹(x) with respect to x is:",
                "options": {
                    "A": "1/(1-x²)",
                    "B": "1/(1+x²)",
                    "C": "-1/(1+x²)",
                    "D": "x/(1+x²)",
                },
                "correct": "B",
            },
            {
                "question": "If A = [1 2; 3 4], then det(A²) equals:",
                "options": {"A": "4", "B": "16", "C": "-4", "D": "-2"},
                "correct": "A",
            },
            {
                "question": "Which of the following compounds exhibits geometrical isomerism?",
                "options": {
                    "A": "CH₃CH₂CH₃",
                    "B": "CH₃CH=CHCH₃",
                    "C": "CH₃CH₂OH",
                    "D": "CH₃COCH₃",
                },
                "correct": "B",
            },
            {
                "question": "The hybridization of carbon in diamond is:",
                "options": {"A": "sp", "B": "sp²", "C": "sp³", "D": "sp³d"},
                "correct": "C",
            },
            {
                "question": "Which quantum number determines the shape of an orbital?",
                "options": {
                    "A": "Principal quantum number (n)",
                    "B": "Azimuthal quantum number (l)",
                    "C": "Magnetic quantum number (m)",
                    "D": "Spin quantum number (s)",
                },
                "correct": "B",
            },
            {
                "question": "The IUPAC name of CH₃CH(OH)CH₂CH₃ is:",
                "options": {
                    "A": "1-Butanol",
                    "B": "2-Butanol",
                    "C": "Butan-1-ol",
                    "D": "Butan-2-ol",
                },
                "correct": "D",
            },
            {
                "question": "Which of the following is an example of a nucleophilic substitution reaction?",
                "options": {
                    "A": "CH₃Br + OH⁻ → CH₃OH + Br⁻",
                    "B": "C₂H₄ + H₂ → C₂H₆",
                    "C": "CH₄ + Cl₂ → CH₃Cl + HCl",
                    "D": "C₆H₆ + Br₂ → C₆H₅Br + HBr",
                },
                "correct": "A",
            },
            {
                "question": "The oxidation state of chromium in K₂Cr₂O₇ is:",
                "options": {"A": "+3", "B": "+6", "C": "+2", "D": "+7"},
                "correct": "B",
            },
            {
                "question": "Which catalyst is used in the Haber process for ammonia synthesis?",
                "options": {
                    "A": "Platinum",
                    "B": "Nickel",
                    "C": "Iron",
                    "D": "Vanadium pentoxide",
                },
                "correct": "C",
            },
            {
                "question": "The pH of 0.01 M HCl solution is:",
                "options": {"A": "1", "B": "2", "C": "0.01", "D": "12"},
                "correct": "B",
            },
            {
                "question": "Which of the following is a Lewis acid?",
                "options": {"A": "NH₃", "B": "BF₃", "C": "H₂O", "D": "OH⁻"},
                "correct": "B",
            },
            {
                "question": "The unit of rate constant for a first-order reaction is:",
                "options": {
                    "A": "mol L⁻¹ s⁻¹",
                    "B": "s⁻¹",
                    "C": "mol⁻¹ L s⁻¹",
                    "D": "mol L⁻¹",
                },
                "correct": "B",
            },
            {
                "question": "A particle moves in a circle of radius R with constant angular velocity ω. Its centripetal acceleration is:",
                "options": {"A": "ωR", "B": "ω²R", "C": "ωR²", "D": "ω/R"},
                "correct": "B",
            },
            {
                "question": "The work done by a conservative force in a closed path is:",
                "options": {
                    "A": "Maximum",
                    "B": "Minimum",
                    "C": "Zero",
                    "D": "Infinity",
                },
                "correct": "C",
            },
            {
                "question": "Young's modulus is defined as the ratio of:",
                "options": {
                    "A": "Stress to strain",
                    "B": "Strain to stress",
                    "C": "Force to area",
                    "D": "Area to force",
                },
                "correct": "A",
            },
            {
                "question": "The frequency of oscillation of a simple pendulum is independent of:",
                "options": {
                    "A": "Length of the pendulum",
                    "B": "Mass of the bob",
                    "C": "Acceleration due to gravity",
                    "D": "Amplitude of oscillation",
                },
                "correct": "B",
            },
            {
                "question": "Which of the following waves cannot be polarized?",
                "options": {
                    "A": "Light waves",
                    "B": "Radio waves",
                    "C": "Sound waves",
                    "D": "X-rays",
                },
                "correct": "C",
            },
            {
                "question": "The electric field inside a conductor in electrostatic equilibrium is:",
                "options": {
                    "A": "Maximum",
                    "B": "Minimum",
                    "C": "Zero",
                    "D": "Variable",
                },
                "correct": "C",
            },
            {
                "question": "Lenz's law is a consequence of conservation of:",
                "options": {"A": "Energy", "B": "Momentum", "C": "Charge", "D": "Mass"},
                "correct": "A",
            },
            {
                "question": "The photoelectric effect was explained by:",
                "options": {
                    "A": "Wave theory of light",
                    "B": "Quantum theory of light",
                    "C": "Electromagnetic theory",
                    "D": "Classical mechanics",
                },
                "correct": "B",
            },
            {
                "question": "The binding energy per nucleon is maximum for:",
                "options": {
                    "A": "Light nuclei",
                    "B": "Heavy nuclei",
                    "C": "Medium nuclei",
                    "D": "All nuclei equally",
                },
                "correct": "C",
            },
            {
                "question": "The de Broglie wavelength of a particle is inversely proportional to its:",
                "options": {
                    "A": "Mass",
                    "B": "Velocity",
                    "C": "Momentum",
                    "D": "Energy",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct passive voice: 'The teacher teaches the students.'",
                "options": {
                    "A": "The students are taught by the teacher.",
                    "B": "The students were taught by the teacher.",
                    "C": "The students have been taught by the teacher.",
                    "D": "The students will be taught by the teacher.",
                },
                "correct": "A",
            },
            {
                "question": "Identify the type of clause: 'Because it was raining, we stayed inside.'",
                "options": {
                    "A": "Independent clause",
                    "B": "Dependent clause",
                    "C": "Complex sentence with dependent clause",
                    "D": "Simple sentence",
                },
                "correct": "C",
            },
            {
                "question": "Choose the correct form: 'If I ___ rich, I would buy a mansion.'",
                "options": {"A": "am", "B": "was", "C": "were", "D": "will be"},
                "correct": "C",
            },
            {
                "question": "Select the correctly punctuated sentence:",
                "options": {
                    "A": "The book, which I bought yesterday is interesting.",
                    "B": "The book which I bought yesterday, is interesting.",
                    "C": "The book, which I bought yesterday, is interesting.",
                    "D": "The book which I bought, yesterday is interesting.",
                },
                "correct": "C",
            },
            {
                "question": "Choose the synonym of 'Ephemeral':",
                "options": {
                    "A": "Permanent",
                    "B": "Temporary",
                    "C": "Eternal",
                    "D": "Lasting",
                },
                "correct": "B",
            },
            {
                "question": "Identify the figure of speech: 'The wind whispered through the trees.'",
                "options": {
                    "A": "Metaphor",
                    "B": "Simile",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "C",
            },
            {
                "question": "Choose the antonym of 'Meticulous':",
                "options": {
                    "A": "Careful",
                    "B": "Precise",
                    "C": "Careless",
                    "D": "Thorough",
                },
                "correct": "C",
            },
            {
                "question": "Select the correct article: '___ honest man is respected by all.'",
                "options": {"A": "A", "B": "An", "C": "The", "D": "No article"},
                "correct": "B",
            },
            {
                "question": "Identify the error: 'Each of the students have submitted their assignments.'",
                "options": {
                    "A": "Each of",
                    "B": "have submitted",
                    "C": "their assignments",
                    "D": "No error",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct reported speech: He said, 'I am going to Delhi.'",
                "options": {
                    "A": "He said that he was going to Delhi.",
                    "B": "He said that he is going to Delhi.",
                    "C": "He said that he will go to Delhi.",
                    "D": "He said that he had gone to Delhi.",
                },
                "correct": "A",
            },
            {
                "question": "Which data structure uses LIFO (Last In First Out) principle?",
                "options": {
                    "A": "Queue",
                    "B": "Stack",
                    "C": "Array",
                    "D": "Linked List",
                },
                "correct": "B",
            },
            {
                "question": "What is the time complexity of binary search algorithm?",
                "options": {
                    "A": "O(n)",
                    "B": "O(n²)",
                    "C": "O(log n)",
                    "D": "O(n log n)",
                },
                "correct": "C",
            },
            {
                "question": "Which of the following is not a programming paradigm?",
                "options": {
                    "A": "Object-oriented programming",
                    "B": "Functional programming",
                    "C": "Procedural programming",
                    "D": "Binary programming",
                },
                "correct": "D",
            },
            {
                "question": "In object-oriented programming, what is inheritance?",
                "options": {
                    "A": "Hiding internal details",
                    "B": "Creating objects from classes",
                    "C": "Acquiring properties from parent class",
                    "D": "Grouping related data and methods",
                },
                "correct": "C",
            },
            {
                "question": "What does SQL stand for?",
                "options": {
                    "A": "Structured Query Language",
                    "B": "Standard Query Language",
                    "C": "Simple Query Language",
                    "D": "Sequential Query Language",
                },
                "correct": "A",
            },
            {
                "question": "Which sorting algorithm has the best average-case time complexity?",
                "options": {
                    "A": "Bubble Sort",
                    "B": "Selection Sort",
                    "C": "Quick Sort",
                    "D": "Insertion Sort",
                },
                "correct": "C",
            },
            {
                "question": "What is the primary purpose of an operating system?",
                "options": {
                    "A": "To run applications",
                    "B": "To manage computer resources",
                    "C": "To provide internet access",
                    "D": "To create documents",
                },
                "correct": "B",
            },
            {
                "question": "Which protocol is used for secure web communication?",
                "options": {"A": "HTTP", "B": "FTP", "C": "HTTPS", "D": "SMTP"},
                "correct": "C",
            },
            {
                "question": "What is the base of the binary number system?",
                "options": {"A": "8", "B": "10", "C": "2", "D": "16"},
                "correct": "C",
            },
            {
                "question": "Which of the following is a non-volatile memory?",
                "options": {"A": "RAM", "B": "Cache", "C": "ROM", "D": "Register"},
                "correct": "C",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["COM005"] = com_exam_5

    apt_exam_1 = {
        "code": "APT001",
        "title": "General Entrance Exam 1",
        "duration": 50,
        "questions": [
            {
                "section": "Mathematics",
                "question": "If the function f(x) = x³ - 6x² + 11x - 6 has roots α, β, γ, then the value of α² + β² + γ² is:",
                "options": {"A": "14", "B": "16", "C": "18", "D": "20"},
                "correct": "A",
            },
            {
                "section": "Mathematics",
                "question": "The number of ways to select 4 cards from a standard deck of 52 cards such that all four suits are represented is:",
                "options": {"A": "685464", "B": "635376", "C": "715716", "D": "625536"},
                "correct": "A",
            },
            {
                "section": "Mathematics",
                "question": "If the equation of the tangent to the curve y = x³ - 3x + 2 at point (1, 0) is ax + by + c = 0, then a + b + c equals:",
                "options": {"A": "0", "B": "1", "C": "-1", "D": "2"},
                "correct": "A",
            },
            {
                "section": "Mathematics",
                "question": "The value of ∫₀^(π/2) sin²x cos²x dx is:",
                "options": {"A": "π/32", "B": "π/16", "C": "π/8", "D": "π/4"},
                "correct": "B",
            },
            {
                "section": "Mathematics",
                "question": "If |z|² = z·z̄ = 25 and arg(z) = π/3, then z equals:",
                "options": {
                    "A": "5(cos(π/3) + i sin(π/3))",
                    "B": "5(cos(π/6) + i sin(π/6))",
                    "C": "25(cos(π/3) + i sin(π/3))",
                    "D": "√25(cos(π/3) + i sin(π/3))",
                },
                "correct": "A",
            },
            {
                "section": "Mathematics",
                "question": "The coefficient of x⁷ in the expansion of (1 + x)¹⁰(1 + x²)⁵ is:",
                "options": {"A": "330", "B": "210", "C": "252", "D": "290"},
                "correct": "C",
            },
            {
                "section": "Mathematics",
                "question": "If the vertices of a triangle are A(1, 2), B(3, -1), and C(-1, 4), then the equation of the circumcircle is:",
                "options": {
                    "A": "x² + y² - 2x - 2y - 8 = 0",
                    "B": "x² + y² - 4x - 2y - 5 = 0",
                    "C": "x² + y² - 2x - 4y - 5 = 0",
                    "D": "x² + y² - 2x - 2y - 5 = 0",
                },
                "correct": "B",
            },
            {
                "section": "Mathematics",
                "question": "The number of solutions of the equation 2^x + 3^x = 5^x in the interval [0, 2] is:",
                "options": {"A": "0", "B": "1", "C": "2", "D": "3"},
                "correct": "C",
            },
            {
                "section": "Mathematics",
                "question": "If the matrix A = [2 1; 3 2] and A^n = [a b; c d], then a + d equals:",
                "options": {
                    "A": "2^n + 1",
                    "B": "2^(n+1)",
                    "C": "2^n + 2^(n-1)",
                    "D": "3^n - 1",
                },
                "correct": "B",
            },
            {
                "section": "Mathematics",
                "question": "The minimum value of the function f(x) = x²e^x on the interval [-2, 1] is:",
                "options": {"A": "0", "B": "4/e²", "C": "-4/e²", "D": "e"},
                "correct": "B",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "If CODING is written as DPEJOH, then FLOWER will be written as:",
                "options": {"A": "GMPXFS", "B": "GMPXFR", "C": "GMPWFS", "D": "GMPWFR"},
                "correct": "A",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "In a certain code, if MONKEY is 123456 and DONKEY is 723456, then what is the code for YOKE?",
                "options": {"A": "6245", "B": "6254", "C": "6425", "D": "4256"},
                "correct": "B",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "Find the missing number in the series: 2, 6, 12, 20, 30, ?",
                "options": {"A": "42", "B": "40", "C": "44", "D": "46"},
                "correct": "A",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "If the day before yesterday was Friday, what day will it be after tomorrow?",
                "options": {
                    "A": "Tuesday",
                    "B": "Wednesday",
                    "C": "Thursday",
                    "D": "Monday",
                },
                "correct": "A",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "In a row of 40 students, A is 16th from the left and B is 23rd from the right. How many students are there between A and B?",
                "options": {"A": "1", "B": "2", "C": "0", "D": "3"},
                "correct": "C",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "A clock shows 3:15. What is the angle between the hour and minute hands?",
                "options": {"A": "7.5°", "B": "15°", "C": "22.5°", "D": "30°"},
                "correct": "A",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "If '+' means '×', '×' means '-', '-' means '÷', and '÷' means '+', then 15 + 3 × 12 ÷ 4 - 2 = ?",
                "options": {"A": "41", "B": "43", "C": "45", "D": "47"},
                "correct": "B",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "Complete the analogy: Book : Author :: Painting : ?",
                "options": {"A": "Canvas", "B": "Brush", "C": "Artist", "D": "Color"},
                "correct": "C",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "If EARTH is coded as 12345 and HEART is coded as 51234, then HATER is coded as:",
                "options": {"A": "52314", "B": "52341", "C": "53241", "D": "54321"},
                "correct": "A",
            },
            {
                "section": "Aptitude/Reasoning",
                "question": "In a certain language, 'mi na to' means 'bring some water', 'to ru su' means 'water is pure', and 'mi pa su' means 'bring pure milk'. What does 'na' mean?",
                "options": {"A": "bring", "B": "some", "C": "water", "D": "pure"},
                "correct": "B",
            },
            {
                "section": "English",
                "question": "Choose the word that best completes the sentence: The politician's _____ speech failed to convince the skeptical audience.",
                "options": {
                    "A": "eloquent",
                    "B": "verbose",
                    "C": "terse",
                    "D": "laconic",
                },
                "correct": "B",
            },
            {
                "section": "English",
                "question": "Identify the correctly punctuated sentence:",
                "options": {
                    "A": "The CEO said, 'Our profits have increased by 20% this quarter'.",
                    "B": 'The CEO said, "Our profits have increased by 20% this quarter."',
                    "C": "The CEO said, 'Our profits have increased by 20% this quarter.'",
                    "D": 'The CEO said, "Our profits have increased by 20% this quarter".',
                },
                "correct": "B",
            },
            {
                "section": "English",
                "question": "Choose the sentence with correct subject-verb agreement:",
                "options": {
                    "A": "Neither the students nor the teacher were present.",
                    "B": "Neither the students nor the teacher was present.",
                    "C": "Neither the teacher nor the students was present.",
                    "D": "Neither the teacher nor the students were present.",
                },
                "correct": "D",
            },
            {
                "section": "English",
                "question": "Select the word that is closest in meaning to 'UBIQUITOUS':",
                "options": {
                    "A": "Rare",
                    "B": "Omnipresent",
                    "C": "Ancient",
                    "D": "Valuable",
                },
                "correct": "B",
            },
            {
                "section": "English",
                "question": "Choose the correct form of the verb: By next year, she _____ her degree.",
                "options": {
                    "A": "will complete",
                    "B": "will have completed",
                    "C": "completes",
                    "D": "has completed",
                },
                "correct": "B",
            },
            {
                "section": "English",
                "question": "Identify the type of sentence: 'Although it was raining heavily, they decided to go for a walk.'",
                "options": {
                    "A": "Simple sentence",
                    "B": "Compound sentence",
                    "C": "Complex sentence",
                    "D": "Compound-complex sentence",
                },
                "correct": "C",
            },
            {
                "section": "English",
                "question": "Choose the antonym of 'PRODIGAL':",
                "options": {
                    "A": "Wasteful",
                    "B": "Generous",
                    "C": "Frugal",
                    "D": "Lavish",
                },
                "correct": "C",
            },
            {
                "section": "English",
                "question": "Select the sentence that uses the passive voice correctly:",
                "options": {
                    "A": "The cake was being baked by the chef.",
                    "B": "The cake is being baked by the chef.",
                    "C": "The cake has been baked by the chef.",
                    "D": "All of the above",
                },
                "correct": "D",
            },
            {
                "section": "English",
                "question": "Choose the correct preposition: She is proficient _____ mathematics.",
                "options": {"A": "in", "B": "at", "C": "with", "D": "on"},
                "correct": "A",
            },
            {
                "section": "English",
                "question": "Identify the figure of speech: 'The classroom was a zoo during the break.'",
                "options": {
                    "A": "Simile",
                    "B": "Metaphor",
                    "C": "Personification",
                    "D": "Hyperbole",
                },
                "correct": "B",
            },
            {
                "section": "General Knowledge",
                "question": "Who is the current Secretary-General of the United Nations (as of 2025)?",
                "options": {
                    "A": "Ban Ki-moon",
                    "B": "António Guterres",
                    "C": "Kofi Annan",
                    "D": "Boutros Boutros-Ghali",
                },
                "correct": "B",
            },
            {
                "section": "General Knowledge",
                "question": "Which Indian city is known as the 'Silicon Valley of India'?",
                "options": {
                    "A": "Mumbai",
                    "B": "Pune",
                    "C": "Hyderabad",
                    "D": "Bengaluru",
                },
                "correct": "D",
            },
            {
                "section": "General Knowledge",
                "question": "The 2024 Summer Olympics were held in:",
                "options": {
                    "A": "Tokyo",
                    "B": "Paris",
                    "C": "Los Angeles",
                    "D": "London",
                },
                "correct": "B",
            },
            {
                "section": "General Knowledge",
                "question": "Who won the Nobel Prize in Literature in 2023?",
                "options": {
                    "A": "Jon Fosse",
                    "B": "Annie Ernaux",
                    "C": "Abdulrazak Gurnah",
                    "D": "Louise Glück",
                },
                "correct": "A",
            },
            {
                "section": "General Knowledge",
                "question": "The headquarters of the International Court of Justice is located in:",
                "options": {
                    "A": "Geneva",
                    "B": "New York",
                    "C": "The Hague",
                    "D": "Vienna",
                },
                "correct": "C",
            },
            {
                "section": "General Knowledge",
                "question": "Which country launched the James Webb Space Telescope?",
                "options": {
                    "A": "Russia",
                    "B": "China",
                    "C": "USA",
                    "D": "European Union",
                },
                "correct": "C",
            },
            {
                "section": "General Knowledge",
                "question": "The longest river in the world is:",
                "options": {
                    "A": "Amazon",
                    "B": "Nile",
                    "C": "Yangtze",
                    "D": "Mississippi",
                },
                "correct": "B",
            },
            {
                "section": "General Knowledge",
                "question": "Which Indian state has the highest literacy rate according to the 2011 census?",
                "options": {
                    "A": "Tamil Nadu",
                    "B": "Maharashtra",
                    "C": "Kerala",
                    "D": "Gujarat",
                },
                "correct": "C",
            },
            {
                "section": "General Knowledge",
                "question": "The G20 Summit 2023 was held in:",
                "options": {
                    "A": "Indonesia",
                    "B": "India",
                    "C": "Saudi Arabia",
                    "D": "Italy",
                },
                "correct": "B",
            },
            {
                "section": "General Knowledge",
                "question": "Who is known as the 'Father of the Indian Constitution'?",
                "options": {
                    "A": "Mahatma Gandhi",
                    "B": "Jawaharlal Nehru",
                    "C": "Dr. B.R. Ambedkar",
                    "D": "Sardar Vallabhbhai Patel",
                },
                "correct": "C",
            },
            {
                "section": "Physics",
                "question": "The dimensional formula for angular momentum is:",
                "options": {
                    "A": "[ML²T⁻¹]",
                    "B": "[MLT⁻¹]",
                    "C": "[ML²T⁻²]",
                    "D": "[MLT⁻²]",
                },
                "correct": "A",
            },
            {
                "section": "Physics",
                "question": "In Young's double-slit experiment, if the distance between slits is halved and the distance to the screen is doubled, the fringe width becomes:",
                "options": {"A": "Same", "B": "Double", "C": "Half", "D": "Four times"},
                "correct": "D",
            },
            {
                "section": "Physics",
                "question": "The ratio of the speeds of sound in hydrogen and oxygen at the same temperature is approximately:",
                "options": {"A": "1:4", "B": "4:1", "C": "1:2", "D": "2:1"},
                "correct": "B",
            },
            {
                "section": "Physics",
                "question": "A charged particle moves in a uniform magnetic field. The kinetic energy of the particle:",
                "options": {
                    "A": "Increases",
                    "B": "Decreases",
                    "C": "Remains constant",
                    "D": "First increases then decreases",
                },
                "correct": "C",
            },
            {
                "section": "Physics",
                "question": "The work function of a metal is 3.3 eV. The maximum kinetic energy of photoelectrons when light of wavelength 300 nm is incident on it is:",
                "options": {
                    "A": "0.84 eV",
                    "B": "1.14 eV",
                    "C": "4.14 eV",
                    "D": "7.44 eV",
                },
                "correct": "B",
            },
            {
                "section": "Physics",
                "question": "In a series LCR circuit at resonance, the impedance is:",
                "options": {
                    "A": "Maximum",
                    "B": "Minimum",
                    "C": "Zero",
                    "D": "Infinite",
                },
                "correct": "B",
            },
            {
                "section": "Physics",
                "question": "The half-life of a radioactive element is 10 days. What fraction of the original sample will remain after 30 days?",
                "options": {"A": "1/2", "B": "1/4", "C": "1/8", "D": "1/16"},
                "correct": "C",
            },
            {
                "section": "Physics",
                "question": "A ball is thrown horizontally from a height of 20 m with an initial velocity of 10 m/s. The time taken to reach the ground is:",
                "options": {"A": "2 s", "B": "2.02 s", "C": "4 s", "D": "4.04 s"},
                "correct": "B",
            },
            {
                "section": "Physics",
                "question": "The temperature coefficient of resistance of a semiconductor is:",
                "options": {
                    "A": "Positive",
                    "B": "Negative",
                    "C": "Zero",
                    "D": "Infinite",
                },
                "correct": "B",
            },
            {
                "section": "Physics",
                "question": "In an adiabatic process for an ideal gas, the relationship between pressure and volume is:",
                "options": {
                    "A": "PV = constant",
                    "B": "PVᵞ = constant",
                    "C": "P/V = constant",
                    "D": "P + V = constant",
                },
                "correct": "B",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["APT001"] = apt_exam_1

    apt_exam_2 = {
        "code": "APT002",
        "title": "General Entrance Exam 2",
        "duration": 50,
        "questions": [
            {
                "question": "If log₂(x-1) + log₂(x+1) = 3, then x equals:",
                "options": {"A": "3", "B": "±3", "C": "9", "D": "±9"},
                "correct": "A",
            },
            {
                "question": "The number of solutions of the equation sin²x + cos²x = 2 in [0, 2π] is:",
                "options": {"A": "0", "B": "1", "C": "2", "D": "Infinite"},
                "correct": "A",
            },
            {
                "question": "If the coefficient of x³ in the expansion of (1+x)ⁿ is 84, then n equals:",
                "options": {"A": "9", "B": "8", "C": "10", "D": "12"},
                "correct": "A",
            },
            {
                "question": "The area bounded by y = x², y = 0, and x = 2 is:",
                "options": {"A": "8/3", "B": "4/3", "C": "2", "D": "4"},
                "correct": "A",
            },
            {
                "question": "If A is a 3×3 matrix with det(A) = 5, then det(2A) equals:",
                "options": {"A": "10", "B": "40", "C": "25", "D": "125"},
                "correct": "B",
            },
            {
                "question": "The sum to infinity of the series 1 - 1/3 + 1/9 - 1/27 + ... is:",
                "options": {"A": "3/4", "B": "2/3", "C": "1/2", "D": "4/3"},
                "correct": "A",
            },
            {
                "question": "If z = 1 + i, then z²⁰ equals:",
                "options": {"A": "2¹⁰", "B": "-2¹⁰", "C": "2¹⁰i", "D": "-2¹⁰i"},
                "correct": "B",
            },
            {
                "question": "The equation of the tangent to the circle x² + y² = 25 at point (3, 4) is:",
                "options": {
                    "A": "3x + 4y = 25",
                    "B": "4x + 3y = 25",
                    "C": "3x - 4y = 25",
                    "D": "4x - 3y = 25",
                },
                "correct": "A",
            },
            {
                "question": "If f(x) = x³ - 6x² + 9x + 2, then f'(x) = 0 has roots:",
                "options": {
                    "A": "x = 1, 3",
                    "B": "x = 2, 4",
                    "C": "x = 0, 3",
                    "D": "x = 1, 2",
                },
                "correct": "A",
            },
            {
                "question": "The probability of getting at least one head in 3 tosses of a fair coin is:",
                "options": {"A": "1/8", "B": "3/8", "C": "7/8", "D": "1/2"},
                "correct": "C",
            },
            {
                "question": "In a sequence, if the 5th term is 15 and the 8th term is 24, what is the 12th term if it's an arithmetic progression?",
                "options": {"A": "36", "B": "39", "C": "42", "D": "45"},
                "correct": "B",
            },
            {
                "question": "If MONDAY is coded as 123456, then DYNAMO would be coded as:",
                "options": {"A": "453612", "B": "465312", "C": "456321", "D": "463521"},
                "correct": "A",
            },
            {
                "question": "Find the missing number in the series: 2, 6, 12, 20, 30, ?",
                "options": {"A": "40", "B": "42", "C": "44", "D": "48"},
                "correct": "B",
            },
            {
                "question": "If all roses are flowers and some flowers are red, which conclusion is definitely true?",
                "options": {
                    "A": "All roses are red",
                    "B": "Some roses are red",
                    "C": "No roses are red",
                    "D": "None of the above",
                },
                "correct": "D",
            },
            {
                "question": "A cube is painted on all faces and cut into 64 smaller cubes. How many cubes have exactly 2 faces painted?",
                "options": {"A": "12", "B": "16", "C": "20", "D": "24"},
                "correct": "D",
            },
            {
                "question": "If BAT = 23, CAT = 24, then DOG = ?",
                "options": {"A": "26", "B": "29", "C": "32", "D": "35"},
                "correct": "B",
            },
            {
                "question": "Water is to Fish as Air is to:",
                "options": {"A": "Bird", "B": "Lungs", "C": "Oxygen", "D": "Breathing"},
                "correct": "A",
            },
            {
                "question": "In a certain code, COMPUTER is written as RFUVQNPC. How is MEDICINE written in that code?",
                "options": {
                    "A": "MFEDJOJF",
                    "B": "EOJDJEFN",
                    "C": "NFEJDJOF",
                    "D": "FOJDJEFM",
                },
                "correct": "B",
            },
            {
                "question": "A clock shows 3:15. What is the angle between the hour and minute hands?",
                "options": {"A": "0°", "B": "7.5°", "C": "15°", "D": "22.5°"},
                "correct": "B",
            },
            {
                "question": "If today is Wednesday, what day will it be 100 days from now?",
                "options": {
                    "A": "Monday",
                    "B": "Tuesday",
                    "C": "Wednesday",
                    "D": "Thursday",
                },
                "correct": "D",
            },
            {
                "question": "Choose the word that is most nearly opposite to 'CANDID':",
                "options": {"A": "Frank", "B": "Blunt", "C": "Evasive", "D": "Honest"},
                "correct": "C",
            },
            {
                "question": "Select the correctly spelled word:",
                "options": {
                    "A": "Occassion",
                    "B": "Occasion",
                    "C": "Ocasion",
                    "D": "Occassion",
                },
                "correct": "B",
            },
            {
                "question": "Choose the best meaning of the idiom 'Break the ice':",
                "options": {
                    "A": "To start a conversation",
                    "B": "To break something",
                    "C": "To make cold",
                    "D": "To stop working",
                },
                "correct": "A",
            },
            {
                "question": "Fill in the blank: 'The committee was _____ about the new proposal.'",
                "options": {
                    "A": "Enthusiastic",
                    "B": "Enthusiasm",
                    "C": "Enthusiastically",
                    "D": "Enthusiast",
                },
                "correct": "A",
            },
            {
                "question": "Choose the correct sentence:",
                "options": {
                    "A": "Neither John nor his friends was present.",
                    "B": "Neither John nor his friends were present.",
                    "C": "Neither John nor his friends is present.",
                    "D": "Neither John nor his friends are present.",
                },
                "correct": "B",
            },
            {
                "question": "What is the meaning of 'Ubiquitous'?",
                "options": {
                    "A": "Rare",
                    "B": "Present everywhere",
                    "C": "Ancient",
                    "D": "Mysterious",
                },
                "correct": "B",
            },
            {
                "question": "Identify the part of speech of the underlined word: 'She runs *fast*.'",
                "options": {"A": "Adjective", "B": "Adverb", "C": "Noun", "D": "Verb"},
                "correct": "B",
            },
            {
                "question": "Choose the synonym of 'PRISTINE':",
                "options": {"A": "Dirty", "B": "Pure", "C": "Old", "D": "Damaged"},
                "correct": "B",
            },
            {
                "question": "Convert to indirect speech: She said, 'I will come tomorrow.'",
                "options": {
                    "A": "She said that she will come tomorrow.",
                    "B": "She said that she would come the next day.",
                    "C": "She said that she will come the next day.",
                    "D": "She said that she would come tomorrow.",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correct preposition: 'She is afraid _____ spiders.'",
                "options": {"A": "from", "B": "of", "C": "with", "D": "by"},
                "correct": "B",
            },
            {
                "question": "Who is the current President of India (as of 2024)?",
                "options": {
                    "A": "Ram Nath Kovind",
                    "B": "Draupadi Murmu",
                    "C": "Pranab Mukherjee",
                    "D": "A.P.J. Abdul Kalam",
                },
                "correct": "B",
            },
            {
                "question": "Which planet is known as the 'Red Planet'?",
                "options": {"A": "Venus", "B": "Jupiter", "C": "Mars", "D": "Saturn"},
                "correct": "C",
            },
            {
                "question": "The headquarters of UNESCO is located in:",
                "options": {
                    "A": "New York",
                    "B": "Geneva",
                    "C": "Paris",
                    "D": "Vienna",
                },
                "correct": "C",
            },
            {
                "question": "Which Indian state has the longest coastline?",
                "options": {
                    "A": "Tamil Nadu",
                    "B": "Gujarat",
                    "C": "Maharashtra",
                    "D": "Andhra Pradesh",
                },
                "correct": "B",
            },
            {
                "question": "The Nobel Prize in Literature 2023 was awarded to:",
                "options": {
                    "A": "Jon Fosse",
                    "B": "Annie Ernaux",
                    "C": "Abdulrazak Gurnah",
                    "D": "Louise Glück",
                },
                "correct": "A",
            },
            {
                "question": "Which gas is most abundant in Earth's atmosphere?",
                "options": {
                    "A": "Oxygen",
                    "B": "Carbon dioxide",
                    "C": "Nitrogen",
                    "D": "Argon",
                },
                "correct": "C",
            },
            {
                "question": "The Chipko movement was related to:",
                "options": {
                    "A": "Forest conservation",
                    "B": "Water conservation",
                    "C": "Women's rights",
                    "D": "Anti-corruption",
                },
                "correct": "A",
            },
            {
                "question": "Which country hosted the 2024 Olympics?",
                "options": {"A": "Japan", "B": "France", "C": "Brazil", "D": "China"},
                "correct": "B",
            },
            {
                "question": "The currency of South Korea is:",
                "options": {"A": "Yen", "B": "Won", "C": "Yuan", "D": "Rupiah"},
                "correct": "B",
            },
            {
                "question": "Which river is known as the 'Sorrow of Bengal'?",
                "options": {
                    "A": "Ganges",
                    "B": "Brahmaputra",
                    "C": "Damodar",
                    "D": "Hooghly",
                },
                "correct": "C",
            },
            {
                "question": "The atomic number of carbon is:",
                "options": {"A": "4", "B": "6", "C": "8", "D": "12"},
                "correct": "B",
            },
            {
                "question": "Which programming language is primarily used for Android app development?",
                "options": {
                    "A": "Python",
                    "B": "Java/Kotlin",
                    "C": "C++",
                    "D": "JavaScript",
                },
                "correct": "B",
            },
            {
                "question": "The process by which plants make their own food is called:",
                "options": {
                    "A": "Respiration",
                    "B": "Photosynthesis",
                    "C": "Transpiration",
                    "D": "Digestion",
                },
                "correct": "B",
            },
            {
                "question": "If momentum is conserved in a collision, the collision is called:",
                "options": {
                    "A": "Elastic",
                    "B": "Inelastic",
                    "C": "Both elastic and inelastic",
                    "D": "Neither elastic nor inelastic",
                },
                "correct": "C",
            },
            {
                "question": "The molecular formula of glucose is:",
                "options": {
                    "A": "C₆H₁₂O₆",
                    "B": "C₆H₁₀O₅",
                    "C": "C₁₂H₂₂O₁₁",
                    "D": "C₆H₆",
                },
                "correct": "A",
            },
            {
                "question": "In economics, what does GDP stand for?",
                "options": {
                    "A": "Gross Domestic Product",
                    "B": "General Development Program",
                    "C": "Government Development Policy",
                    "D": "Global Development Plan",
                },
                "correct": "A",
            },
            {
                "question": "The study of earthquakes is called:",
                "options": {
                    "A": "Seismology",
                    "B": "Geology",
                    "C": "Meteorology",
                    "D": "Astronomy",
                },
                "correct": "A",
            },
            {
                "question": "Which article of the Indian Constitution deals with the Right to Equality?",
                "options": {
                    "A": "Article 12",
                    "B": "Article 14",
                    "C": "Article 19",
                    "D": "Article 21",
                },
                "correct": "B",
            },
            {
                "question": "The largest ocean on Earth is:",
                "options": {
                    "A": "Atlantic Ocean",
                    "B": "Indian Ocean",
                    "C": "Arctic Ocean",
                    "D": "Pacific Ocean",
                },
                "correct": "D",
            },
            {
                "question": "Who wrote the famous novel '1984'?",
                "options": {
                    "A": "George Orwell",
                    "B": "Aldous Huxley",
                    "C": "Ray Bradbury",
                    "D": "H.G. Wells",
                },
                "correct": "A",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["APT002"] = apt_exam_2

    apt_exam_3 = {
        "code": "APT003",
        "title": "General Entrance Exam 3",
        "duration": 50,
        "questions": [
            {
                "question": "If the matrix A = [2 1; 3 4] and B = [1 2; 0 1], then (AB)^T equals:",
                "options": {
                    "A": "[2 6; 3 7]",
                    "B": "[2 3; 6 7]",
                    "C": "[6 2; 7 3]",
                    "D": "[3 2; 7 6]",
                },
                "correct": "B",
            },
            {
                "question": "In a sequence, if the first term is 5 and each subsequent term is obtained by adding 3 to the previous term, what is the 15th term?",
                "options": {"A": "47", "B": "50", "C": "44", "D": "41"},
                "correct": "A",
            },
            {
                "question": "Choose the word that best completes the analogy: Book : Author :: Painting : ?",
                "options": {"A": "Canvas", "B": "Artist", "C": "Museum", "D": "Frame"},
                "correct": "B",
            },
            {
                "question": "The limit of (sin x)/x as x approaches 0 is:",
                "options": {"A": "0", "B": "1", "C": "∞", "D": "Does not exist"},
                "correct": "B",
            },
            {
                "question": "Which of the following is the correct passive voice of 'She will complete the project tomorrow'?",
                "options": {
                    "A": "The project will be completed by her tomorrow.",
                    "B": "The project would be completed by her tomorrow.",
                    "C": "The project is completed by her tomorrow.",
                    "D": "The project has been completed by her tomorrow.",
                },
                "correct": "A",
            },
            {
                "question": "If log₂ 8 = x, then the value of x is:",
                "options": {"A": "2", "B": "3", "C": "4", "D": "8"},
                "correct": "B",
            },
            {
                "question": "In a coding system, if COMPUTER is coded as RFUVQNPC, how is SCIENCE coded?",
                "options": {
                    "A": "FPJFODF",
                    "B": "EQKSQPR",
                    "C": "UDJFODI",
                    "D": "FRJSORD",
                },
                "correct": "C",
            },
            {
                "question": "Who was the first President of India?",
                "options": {
                    "A": "Jawaharlal Nehru",
                    "B": "Dr. Rajendra Prasad",
                    "C": "Sardar Vallabhbhai Patel",
                    "D": "Dr. A.P.J. Abdul Kalam",
                },
                "correct": "B",
            },
            {
                "question": "The derivative of e^(2x) with respect to x is:",
                "options": {
                    "A": "e^(2x)",
                    "B": "2e^(2x)",
                    "C": "e^(2x)/2",
                    "D": "2x⋅e^(2x)",
                },
                "correct": "B",
            },
            {
                "question": "Choose the correctly spelled word:",
                "options": {
                    "A": "Accomodate",
                    "B": "Accommodate",
                    "C": "Acommodate",
                    "D": "Acomodate",
                },
                "correct": "B",
            },
            {
                "question": "If A can complete a work in 12 days and B can complete the same work in 18 days, how many days will they take to complete the work together?",
                "options": {
                    "A": "7.2 days",
                    "B": "6 days",
                    "C": "8 days",
                    "D": "15 days",
                },
                "correct": "A",
            },
            {
                "question": "Find the next number in the series: 2, 6, 12, 20, 30, ?",
                "options": {"A": "40", "B": "42", "C": "44", "D": "46"},
                "correct": "B",
            },
            {
                "question": "The largest planet in our solar system is:",
                "options": {
                    "A": "Saturn",
                    "B": "Earth",
                    "C": "Jupiter",
                    "D": "Neptune",
                },
                "correct": "C",
            },
            {
                "question": "The area of a circle with radius 7 cm is:",
                "options": {
                    "A": "154 cm²",
                    "B": "147 cm²",
                    "C": "49π cm²",
                    "D": "Both A and C",
                },
                "correct": "D",
            },
            {
                "question": "Choose the antonym of 'Verbose':",
                "options": {
                    "A": "Talkative",
                    "B": "Concise",
                    "C": "Elaborate",
                    "D": "Detailed",
                },
                "correct": "B",
            },
            {
                "question": "If 5x + 3y = 19 and 2x - y = 3, then the value of x is:",
                "options": {"A": "2", "B": "3", "C": "4", "D": "5"},
                "correct": "A",
            },
            {
                "question": "In a class of 40 students, if 60% are boys, how many girls are there?",
                "options": {"A": "16", "B": "20", "C": "24", "D": "14"},
                "correct": "A",
            },
            {
                "question": "The currency of Japan is:",
                "options": {"A": "Yuan", "B": "Won", "C": "Yen", "D": "Ringgit"},
                "correct": "C",
            },
            {
                "question": "The sum of the first n natural numbers is given by the formula:",
                "options": {"A": "n(n+1)", "B": "n(n+1)/2", "C": "n²", "D": "2n+1"},
                "correct": "B",
            },
            {
                "question": "Identify the figure of speech in: 'The classroom was a zoo during lunch break.'",
                "options": {
                    "A": "Simile",
                    "B": "Personification",
                    "C": "Metaphor",
                    "D": "Hyperbole",
                },
                "correct": "C",
            },
            {
                "question": "If sin θ = 3/5, then cos θ equals:",
                "options": {"A": "4/5", "B": "5/4", "C": "3/4", "D": "5/3"},
                "correct": "A",
            },
            {
                "question": "A train travels 360 km in 4 hours. What is its average speed?",
                "options": {
                    "A": "80 km/h",
                    "B": "90 km/h",
                    "C": "100 km/h",
                    "D": "85 km/h",
                },
                "correct": "B",
            },
            {
                "question": "The headquarters of UNESCO is located in:",
                "options": {
                    "A": "New York",
                    "B": "Geneva",
                    "C": "Paris",
                    "D": "Vienna",
                },
                "correct": "C",
            },
            {
                "question": "The coefficient of x² in the expansion of (2x + 3)³ is:",
                "options": {"A": "18", "B": "36", "C": "54", "D": "27"},
                "correct": "B",
            },
            {
                "question": "Choose the correct sentence:",
                "options": {
                    "A": "Neither of the boys were present.",
                    "B": "Neither of the boys was present.",
                    "C": "Neither of the boy were present.",
                    "D": "Neither of the boy was present.",
                },
                "correct": "B",
            },
            {
                "question": "The probability of getting a head when a fair coin is tossed is:",
                "options": {"A": "1/4", "B": "1/3", "C": "1/2", "D": "2/3"},
                "correct": "C",
            },
            {
                "question": "If the pattern is: Circle, Square, Triangle, Circle, Square, ?, what comes next?",
                "options": {
                    "A": "Circle",
                    "B": "Square",
                    "C": "Triangle",
                    "D": "Rectangle",
                },
                "correct": "C",
            },
            {
                "question": "The longest river in the world is:",
                "options": {
                    "A": "Amazon",
                    "B": "Nile",
                    "C": "Ganges",
                    "D": "Mississippi",
                },
                "correct": "B",
            },
            {
                "question": "If f(x) = x² + 2x + 1, then f(3) equals:",
                "options": {"A": "16", "B": "14", "C": "12", "D": "18"},
                "correct": "A",
            },
            {
                "question": "Select the word closest in meaning to 'Pristine':",
                "options": {"A": "Dirty", "B": "Old", "C": "Pure", "D": "Broken"},
                "correct": "C",
            },
            {
                "question": "The distance between two points (3, 4) and (7, 1) is:",
                "options": {"A": "3", "B": "4", "C": "5", "D": "6"},
                "correct": "C",
            },
            {
                "question": "If all roses are flowers and some flowers are red, which conclusion is valid?",
                "options": {
                    "A": "All roses are red",
                    "B": "Some roses are red",
                    "C": "No roses are red",
                    "D": "Cannot be determined",
                },
                "correct": "D",
            },
            {
                "question": "The Indian Constitution was adopted on:",
                "options": {
                    "A": "15th August 1947",
                    "B": "26th January 1950",
                    "C": "26th November 1949",
                    "D": "2nd October 1948",
                },
                "correct": "C",
            },
            {
                "question": "The integral of 1/x dx is:",
                "options": {
                    "A": "ln|x| + C",
                    "B": "x + C",
                    "C": "1/x² + C",
                    "D": "x² + C",
                },
                "correct": "A",
            },
            {
                "question": "Choose the correct preposition: 'She is allergic ___ cats.'",
                "options": {"A": "of", "B": "to", "C": "with", "D": "from"},
                "correct": "B",
            },
            {
                "question": "The square root of 169 is:",
                "options": {"A": "12", "B": "13", "C": "14", "D": "15"},
                "correct": "B",
            },
            {
                "question": "In a group of 20 people, if everyone shakes hands with everyone else exactly once, how many handshakes occur?",
                "options": {"A": "190", "B": "200", "C": "180", "D": "210"},
                "correct": "A",
            },
            {
                "question": "Mount Everest is located in:",
                "options": {
                    "A": "India",
                    "B": "Nepal",
                    "C": "Tibet",
                    "D": "Nepal-Tibet border",
                },
                "correct": "D",
            },
            {
                "question": "If 2^x = 32, then x equals:",
                "options": {"A": "4", "B": "5", "C": "6", "D": "16"},
                "correct": "B",
            },
            {
                "question": "Identify the error in: 'The team are playing very well today.'",
                "options": {
                    "A": "The team",
                    "B": "are playing",
                    "C": "very well",
                    "D": "No error",
                },
                "correct": "B",
            },
            {
                "question": "The mode of the data set {2, 3, 4, 4, 5, 5, 5, 6} is:",
                "options": {"A": "4", "B": "5", "C": "4.5", "D": "6"},
                "correct": "B",
            },
            {
                "question": "If Monday is the 1st day of a month, what day will be the 15th?",
                "options": {
                    "A": "Sunday",
                    "B": "Monday",
                    "C": "Tuesday",
                    "D": "Wednesday",
                },
                "correct": "B",
            },
            {
                "question": "The chemical symbol for gold is:",
                "options": {"A": "Go", "B": "Gd", "C": "Au", "D": "Ag"},
                "correct": "C",
            },
            {
                "question": "The value of sin 30° is:",
                "options": {"A": "1/2", "B": "√3/2", "C": "1", "D": "√2/2"},
                "correct": "A",
            },
            {
                "question": "Choose the correct form: 'I wish I ___ taller.'",
                "options": {"A": "am", "B": "was", "C": "were", "D": "will be"},
                "correct": "C",
            },
            {
                "question": "If the perimeter of a square is 40 cm, its area is:",
                "options": {
                    "A": "100 cm²",
                    "B": "80 cm²",
                    "C": "120 cm²",
                    "D": "160 cm²",
                },
                "correct": "A",
            },
            {
                "question": "Water : Thirst :: Food : ?",
                "options": {"A": "Eat", "B": "Hunger", "C": "Taste", "D": "Nutrition"},
                "correct": "B",
            },
            {
                "question": "The smallest country in the world is:",
                "options": {
                    "A": "Monaco",
                    "B": "Vatican City",
                    "C": "San Marino",
                    "D": "Liechtenstein",
                },
                "correct": "B",
            },
            {
                "question": "The number of sides in a hexagon is:",
                "options": {"A": "5", "B": "6", "C": "7", "D": "8"},
                "correct": "B",
            },
            {
                "question": "Select the correctly punctuated sentence:",
                "options": {
                    "A": "It's a beautiful day, isn't it?",
                    "B": "Its a beautiful day, isn't it?",
                    "C": "It's a beautiful day isn't it?",
                    "D": "Its a beautiful day isn't it?",
                },
                "correct": "A",
            },
        ],
        "created": datetime.now().isoformat(),
        "active": True,
    }
    exams["APT003"] = apt_exam_3

    # Save sample data
    if save_exams(exams):
        print("Sample exams created successfully!")
    else:
        print("Failed to create sample exams.")


if __name__ == "__main__":
    # Initialize sample data on first run
    initialize_sample_data()

    print(f"Data will be stored in: {os.path.abspath(DATA_DIR)}")
    print("Starting Flask application with disk storage...")

    app.run(debug=True, host="0.0.0.0", port=5000)
