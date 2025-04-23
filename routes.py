import os
import base64
import uuid
import traceback
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from app import app, db, DEMO_MODE
from models import Student, Question, ScanResult, Answer
from scanner import BubbleSheetScanner

# Initialize scanner
scanner = BubbleSheetScanner()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'pdf'}

@app.route('/')
def index():
    # Get recent scan results
    recent_scans = ScanResult.query.order_by(ScanResult.scan_date.desc()).limit(10).all()
    # Pass current year to the template for copyright notice
    return render_template('index.html', recent_scans=recent_scans, now=datetime.now())

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('index'))
    
    # Get selected template
    template_name = request.form.get('template', 'standard_20')
    
    try:
        if file and allowed_file(file.filename):
            # Create a unique filename
            original_filename = secure_filename(file.filename)
            extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{extension}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            
            # Make sure the directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            file.save(filepath)
            
            # Process the file based on type
            if extension == 'pdf':
                image_paths = scanner.convert_pdf_to_images(filepath)
                if not image_paths:
                    flash('Failed to convert PDF to images', 'danger')
                    return redirect(url_for('index'))
                
                # Process the first page for now with the selected template
                scanner.current_template = template_name
                result, error = scanner.process_sheet(image_paths[0])
            else:
                # Process image directly with the selected template
                scanner.current_template = template_name
                result, error = scanner.process_sheet(filepath)
            
            if error:
                flash(f'Error processing file: {error}', 'danger')
                return redirect(url_for('index'))
            
            # Save results to database
            student_info = result['student']
            
            # Create or get student
            student = Student.query.filter_by(name=student_info['name']).first()
            if not student:
                student = Student(name=student_info['name'], student_id=student_info.get('id'))
                db.session.add(student)
                db.session.commit()
            
            # Create scan result
            score_info = result['score']
            scan_result = ScanResult(
                student_id=student.id,
                template_used=result['template'],
                score=score_info['correct'],
                total_questions=score_info['total'],
                percentage=score_info['percentage'],
                image_path=filepath
            )
            db.session.add(scan_result)
            db.session.commit()
            
            # Add answers
            for q_num, answer in result['answers'].items():
                correct = result['correct_answers'].get(q_num)
                is_correct = answer == correct
                
                db_answer = Answer(
                    scan_result_id=scan_result.id,
                    question_number=int(q_num),
                    selected_answer=answer,
                    correct_answer=correct,
                    is_correct=is_correct
                )
                db.session.add(db_answer)
            
            db.session.commit()
            
            return redirect(url_for('view_result', scan_id=scan_result.id))
        
        flash('Invalid file type. Please upload PNG, JPG, JPEG, or PDF', 'danger')
        return redirect(url_for('index'))
    except Exception as e:
        print(f"Error in upload_file: {str(e)}")
        traceback.print_exc()
        flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/result/<int:scan_id>')
def view_result(scan_id):
    try:
        scan_result = ScanResult.query.get_or_404(scan_id)
        answers = Answer.query.filter_by(scan_result_id=scan_id).order_by(Answer.question_number).all()
        
        return render_template('results.html', scan=scan_result, answers=answers, now=datetime.now())
    except Exception as e:
        flash(f'Error retrieving result: {str(e)}', 'danger')
        return redirect(url_for('index'))

@app.route('/api/results')
def api_results():
    try:
        results = ScanResult.query.order_by(ScanResult.scan_date.desc()).limit(50).all()
        
        result_list = []
        for result in results:
            result_list.append({
                'id': result.id,
                'student_name': result.student.name,
                'student_id': result.student.student_id,
                'score': result.score,
                'total': result.total_questions,
                'percentage': result.percentage,
                'date': result.scan_date.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify(results=result_list)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/camera')
def camera():
    """Camera capture page"""
    return render_template('camera.html', now=datetime.now())

@app.route('/process_camera_image', methods=['POST'])
def process_camera_image():
    """Process an image captured from the camera"""
    try:
        # Get the base64 image data from request JSON
        # This avoids form size limitations
        if request.is_json:
            # Get from JSON payload
            request_data = request.get_json()
            image_data = request_data.get('image_data')
            template_name = request_data.get('template', 'standard_20')
        else:
            # Fallback to form data
            image_data = request.form.get('image_data')
            template_name = request.form.get('template', 'standard_20')
        
        if not image_data:
            flash('No image data received', 'danger')
            return redirect(url_for('camera'))
            
        # The image data is in format: data:image/png;base64,<actual_base64_data>
        # We need to extract the actual base64 data part
        if ',' in image_data:
            image_data = image_data.split(',')[1]
            
        # Decode the base64 image
        image_bytes = base64.b64decode(image_data)
        
        # Save the image to a file
        unique_filename = f"{uuid.uuid4().hex}.png"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Write the image to a file
        with open(filepath, 'wb') as f:
            f.write(image_bytes)
            
        # Process the image with the selected template
        scanner.current_template = template_name
        result, error = scanner.process_sheet(filepath)
        
        if error:
            if request.is_json:
                return jsonify({'error': error}), 400
            else:
                flash(f'Error processing image: {error}', 'danger')
                return redirect(url_for('camera'))
            
        # Save results to database (similar to upload_file route)
        student_info = result['student']
        
        # Create or get student
        student = Student.query.filter_by(name=student_info['name']).first()
        if not student:
            student = Student(name=student_info['name'], student_id=student_info.get('id'))
            db.session.add(student)
            db.session.commit()
        
        # Create scan result
        score_info = result['score']
        scan_result = ScanResult(
            student_id=student.id,
            template_used=result['template'],
            score=score_info['correct'],
            total_questions=score_info['total'],
            percentage=score_info['percentage'],
            image_path=filepath
        )
        db.session.add(scan_result)
        db.session.commit()
        
        # Add answers
        for q_num, answer in result['answers'].items():
            correct = result['correct_answers'].get(q_num)
            is_correct = answer == correct
            
            db_answer = Answer(
                scan_result_id=scan_result.id,
                question_number=int(q_num),
                selected_answer=answer,
                correct_answer=correct,
                is_correct=is_correct
            )
            db.session.add(db_answer)
        
        db.session.commit()
        
        # Return appropriate response based on request type
        if request.is_json:
            return jsonify({
                'success': True,
                'scan_id': scan_result.id,
                'message': 'Image processed successfully'
            })
        else:
            return redirect(url_for('view_result', scan_id=scan_result.id))
        
    except Exception as e:
        print(f"Error in process_camera_image: {str(e)}")
        traceback.print_exc()
        
        if request.is_json:
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'An error occurred while processing the image'
            }), 500
        else:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('camera'))

@app.route('/download_template/<template_type>')
def download_template(template_type):
    """Download a template based on the selected format"""
    try:
        template_file = None
        if template_type == 'standard_20':
            template_file = 'standard_20.pdf'
            template_name = 'Standard 20 Questions Template'
        elif template_type == 'extended_50':
            template_file = 'extended_50.pdf'
            template_name = 'Extended 50 Questions Template'
        elif template_type == 'comprehensive_100':
            template_file = 'comprehensive_100.pdf'
            template_name = 'Comprehensive 100 Questions Template'
        else:
            flash('Invalid template type requested', 'danger')
            return redirect(url_for('index'))
            
        # Get the full path to the template file
        template_path = os.path.join(app.static_folder, 'templates', template_file)
        
        # Make sure the file exists
        if not os.path.exists(template_path):
            flash(f'Template file not found: {template_file}', 'danger')
            return redirect(url_for('index'))
            
        # Read the file in binary mode
        with open(template_path, 'rb') as f:
            binary_pdf = f.read()
        
        # Create a response with the correct content type
        response = app.response_class(
            binary_pdf,
            mimetype='application/pdf',
            direct_passthrough=True
        )
        
        # Set Content-Disposition header to attachment to force download
        filename = f"MattChecker_{template_file}"
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Type'] = 'application/pdf'
        
        return response
    except Exception as e:
        flash(f'Error downloading template: {str(e)}', 'danger')
        print(f"Template download error: {str(e)}")
        traceback.print_exc()
        return redirect(url_for('index'))

@app.route('/setup')
def setup_db():
    """Setup route for initializing test data with student names from student_classes"""
    try:
        # Clear existing data
        Answer.query.delete()
        ScanResult.query.delete()
        Student.query.delete()
        Question.query.delete()
        db.session.commit()
        
        # Insert questions with correct answers (A, B, C, D, E in rotation)
        for i in range(1, 101):
            answer = chr(ord('A') + ((i-1) % 5))  # A, B, C, D, E in rotation
            question = Question(question_id=i, correct_answer=answer)
            db.session.add(question)
        
        # Insert students from the checker_db user_info table
        students_data = [
            ('ADALID, JOHN SIMON DIAZ', '20220003'),
            ('LEYNES, CHRISTOPHER FIESTA', '20220007'),
            ('DOMINGO, GABRIEL CUBALAN', '20220012'),
            ('VERGARA, JOVIN LEE', '20220026'),
            ('CASTRO, KURT LOUIE CASTRO', '20220027'),
            ('DAVAC, VINCENT AHRON MANTUHAC', '20220041'),
            ('CHAN, IAN MYRON LUNA', '20220060'),
            ('CRUZ, DANIKEN SANTOS', '20220078'),
            ('COLENDRES, SHERWIN BONIFACIO', '20220081'),
            ('BIAGTAS, ALTHEA NICOLE LAGUNA', '20220085'),
            ('VINLUAN, AILA RAMOS', '20220086'),
            ('BAENA, VINCE IVERSON CAMACHO', '20220111'),
            ('PUNO, LOURINE ASHANTI MATEL', '20220112'),
            ('URETA, JAN EDMAINE DELA TORRE', '20220129'),
            ('MANGALINDAN, JEROME TAMAYO', '20220152'),
            ('COMPETENTE, ANNENA CAMBI', '19110182'),
            ('DELOS REYES, AARON VINCENT MANLAPAZ', '20190994'),
            ('CUADERNO, NICOLE MAYA', '20201202'),
            ('BARCENA, DIVINE GRACE DAWAL', '20210004'),
            ('ANZA, AIRA JOYCE NAVARRO', '20211490')
        ]
        
        for name, student_id in students_data:
            student = Student(name=name, student_id=student_id)
            db.session.add(student)
        
        db.session.commit()
        
        flash('Database initialized with student data from checker_db', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error setting up database: {str(e)}', 'danger')
        print(f"Database setup error: {str(e)}")
        traceback.print_exc()
        return redirect(url_for('index'))
