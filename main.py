from flask import Flask, request, jsonify, render_template, send_from_directory
import json
import os
import random
import string
from datetime import datetime

app = Flask(__name__)

# In-memory storage (in production, use a proper database)
exams = {}
results = []

# Default admin credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"

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
    
    return jsonify({
        "success": True, 
        "message": "Exam created successfully",
        "examCode": exam_code
    })

@app.route('/admin/exams', methods=['GET'])
def get_exams():
    """Get all exams for admin"""
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
    # Sort results by submission date (newest first)
    sorted_results = sorted(results, key=lambda x: x['submitted'], reverse=True)
    return jsonify(sorted_results)

@app.route('/student/join', methods=['POST'])
def student_join():
    """Allow student to join an exam using exam code"""
    data = request.get_json()
    exam_code = data.get('examCode', '').upper()
    student_name = data.get('name', '').strip()
    
    if not exam_code or not student_name:
        return jsonify({"success": False, "message": "Missing exam code or name"}), 400
    
    if exam_code not in exams:
        return jsonify({"success": False, "message": "Invalid exam code"}), 404
    
    exam = exams[exam_code]
    if not exam['active']:
        return jsonify({"success": False, "message": "Exam is not active"}), 400
    
    # Return exam data without correct answers
    exam_data = {
        'code': exam_code,
        'title': exam['title'],
        'duration': exam['duration'],
        'questions': []
    }
    
    # Remove correct answers from questions for student
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
    answers = data.get('answers', {})
    
    if not exam_code or not student_name or not answers:
        return jsonify({"success": False, "message": "Missing required data"}), 400
    
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
    
    # Store result
    result = {
        'examCode': exam_code,
        'examTitle': exam['title'],
        'studentName': student_name,
        'score': score,
        'total': total_questions,
        'answers': answers,
        'submitted': datetime.now().isoformat()
    }
    
    results.append(result)
    
    return jsonify({
        "success": True,
        "message": "Exam submitted successfully",
        "score": score,
        "total": total_questions
    })

@app.route('/admin/delete-exam/<exam_code>', methods=['DELETE'])
def delete_exam(exam_code):
    """Delete an exam (admin only)"""
    exam_code = exam_code.upper()
    
    if exam_code not in exams:
        return jsonify({"success": False, "message": "Exam not found"}), 404
    
    del exams[exam_code]
    return jsonify({"success": True, "message": "Exam deleted successfully"})

@app.route('/admin/toggle-exam/<exam_code>', methods=['POST'])
def toggle_exam(exam_code):
    """Toggle exam active status (admin only)"""
    exam_code = exam_code.upper()
    
    if exam_code not in exams:
        return jsonify({"success": False, "message": "Exam not found"}), 404
    
    exams[exam_code]['active'] = not exams[exam_code]['active']
    status = "activated" if exams[exam_code]['active'] else "deactivated"
    
    return jsonify({
        "success": True, 
        "message": f"Exam {status} successfully",
        "active": exams[exam_code]['active']
    })

@app.route('/admin/exam-details/<exam_code>', methods=['GET'])
def get_exam_details(exam_code):
    """Get detailed exam information including results (admin only)"""
    exam_code = exam_code.upper()
    
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
    else:
        avg_score = 0
        max_score = 0
        min_score = 0
        pass_rate = 0
    
    return jsonify({
        "exam": exam,
        "results": exam_results,
        "statistics": {
            "totalAttempts": len(exam_results),
            "averageScore": round(avg_score, 2),
            "maxScore": max_score,
            "minScore": min_score,
            "passRate": round(pass_rate, 2)
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "exams_count": len(exams),
        "results_count": len(results)
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"success": False, "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"success": False, "message": "Internal server error"}), 500

if __name__ == '__main__':
    # Create some sample data for testing
    sample_exam_code = generate_exam_code()
    sample_exam = {
        'code': sample_exam_code,
        'title': 'Sample Computer Science Quiz',
        'duration': 30,
        'questions': [
            {
                'question': 'What does CPU stand for?',
                'options': {
                    'A': 'Central Processing Unit',
                    'B': 'Computer Personal Unit',
                    'C': 'Central Program Unit',
                    'D': 'Computer Processing Unit'
                },
                'correct': 'A'
            },
            {
                'question': 'Which programming language is known as the "mother of all languages"?',
                'options': {
                    'A': 'Python',
                    'B': 'Java',
                    'C': 'C',
                    'D': 'Assembly'
                },
                'correct': 'C'
            },
            {
                'question': 'What is the time complexity of binary search?',
                'options': {
                    'A': 'O(n)',
                    'B': 'O(log n)',
                    'C': 'O(n²)',
                    'D': 'O(1)'
                },
                'correct': 'B'
            }
        ],
        'created': datetime.now().isoformat(),
        'active': True
    }
    
    exams[sample_exam_code] = sample_exam
    
    print("=" * 50)
    print("🎓 JOYAT - Joy University Exam Portal")
    print("=" * 50)
    print(f"🔐 Admin Login:")
    print(f"   Username: {ADMIN_USERNAME}")
    print(f"   Password: {ADMIN_PASSWORD}")
    print(f"")
    print(f"📝 Sample Exam Created:")
    print(f"   Title: {sample_exam['title']}")
    print(f"   Code: {sample_exam_code}")
    print(f"   Duration: {sample_exam['duration']} minutes")
    print(f"   Questions: {len(sample_exam['questions'])}")
    print("=" * 50)
    print("🚀 Server starting...")
    print("📱 Open http://localhost:8080 in your browser")
    print("=" * 50)
   
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
