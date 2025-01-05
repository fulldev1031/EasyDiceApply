from flask import Flask, render_template, request, jsonify
import socket
from threading import Thread
from waitress import serve
from werkzeug.utils import secure_filename
import os, json
import sys
import threading

# Add parent directory to path to import automation code
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from src.automation import DiceAutomation
from src.utils.webdriver_setup import setup_driver

# Determine the base directory dynamically
if getattr(sys, 'frozen', False):  # Running as a PyInstaller bundle
    BASE_DIR = sys._MEIPASS
    template_dir = os.path.join(BASE_DIR, 'ui/templates')
    static_dir = os.path.join(BASE_DIR, 'ui/static')

else:  # Running in a normal Python environment
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # Update template and static directories
    template_dir = os.path.join(BASE_DIR, 'templates')
    static_dir = os.path.join(BASE_DIR, 'static')

# Create Flask app
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.secret_key = 'your_secret_key'

# Configuration
UPLOAD_FOLDER = os.path.join(parent_dir, 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB limit
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create necessary directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(static_dir, 'js'), exist_ok=True)

# Store current automation status and resume path
automation_status = {
    "status": "idle",
    "message": "",
    "jobs_processed": 0,
    "applications_submitted": 0
}
current_resume_path = None
processed_jobs_file_path = "logs/processed_job_summary_list.json"

def get_gmail_name(email):
    if '@' in email:
        return "_" + email.split('@')[0]
    else:
        return ""

def allowed_file(filename):
    """Check if uploaded file has allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def status_callback(status):
    """Callback function to update automation status."""
    global automation_status
    automation_status.update(status)
    print(f"Status updated: {status}")  # Debug print

@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Render the dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/updateJobProcessedInfo', methods=['POST'])
def update_job_processed_info():
    data = request.get_json()
    job_summary = data.get("job_summary")
    job_summary['apply_status'] = True
    return json.dumps(update_processed_job(job_summary))

def update_processed_job(job_summary=None):
    if job_summary is None:
        return False
    
    processed_job_summary_list = get_job_processed_info()
    found_index = find_job_summary_in_list(job_summary, processed_job_summary_list)

    if found_index == -1:
        return False
    else:
        processed_job_summary_list[found_index]['apply_status'] = True

    with open(processed_jobs_file_path, "w") as file:
        json.dump(processed_job_summary_list, file, indent=4)

    return True

def find_job_summary_in_list(job_summary, job_list):
    for index, job in enumerate(job_list):
        if (
            job.get("card_title") == job_summary.get("card_title") and
            job.get("company_name") == job_summary.get("company_name") and
            job.get("location") == job_summary.get("location") and
            job.get("employment_type") == job_summary.get("employment_type") and
            job.get("card_summary") == job_summary.get("card_summary")
        ):
            return index
    return -1
    
@app.route('/api/getJobProcessedInfo', methods=['POST'])
def get_job_processed_info():
    os.makedirs(os.path.dirname(processed_jobs_file_path), exist_ok=True)

    if os.path.exists(processed_jobs_file_path):
        with open(processed_jobs_file_path, "r") as file:
            try:
                processed_job_summary_list = json.load(file)
            except json.JSONDecodeError:
                processed_job_summary_list = []
    else:
        processed_job_summary_list = []
    return processed_job_summary_list

profile_list_file_path = 'uploads/profile_list.json'
@app.route('/api/getProfileList', methods=['GET'])
def get_profile_list():
    os.makedirs(os.path.dirname(profile_list_file_path), exist_ok=True)

    if os.path.exists(profile_list_file_path):
        with open(profile_list_file_path, "r") as file:
            try:
                profile_list = json.load(file)
            except json.JSONDecodeError:
                profile_list = []
    else:
        profile_list = []
    return profile_list

@app.route('/status')
def status():
    """Render the status page."""
    return render_template('status.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle resume file uploads."""
    global current_resume_path

    if 'resume' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Save the file
            file.save(filepath)
            current_resume_path = filepath
            
            print(f"Resume saved at: {current_resume_path}")  # Debug print
            
            return jsonify({
                "message": "File uploaded successfully",
                "filename": filename,
                "path": filepath
            })
        except Exception as e:
            print(f"Error saving file: {str(e)}")  # Debug print
            return jsonify({"error": f"Failed to save file: {str(e)}"}), 500
    
    return jsonify({"error": "Invalid file type"}), 400

@app.route('/api/start', methods=['POST'])
def start_automation():
    """Start the automation process."""
    global current_resume_path, processed_jobs_file_path
    data = request.json
    print(f"Received data: {data}")  # Debug print

    # Validate input
    required_fields = ['username', 'password', 'keyword', 'location', 'max_applications']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        # Extract filters from request data
        filters = {
            'posted_date': data.get('filters', {}).get('posted_date', 'Any Date'),
            'third_party': data.get('filters', {}).get('third_party', False),
            'replace_resume': data.get('filters', {}).get('replace_resume', False),
            'remote': data.get('location', "Remote").strip().lower() == 'remote'
        }
        
        print(f"Current resume path: {current_resume_path}")  # Debug print
        print(f"Extracted filters: {filters}")  # Debug print

        if not current_resume_path or not os.path.exists(current_resume_path):
            return jsonify({"error": "Please upload a resume first"}), 400
        
        proxy_url = data.get('proxy', '')
        # Initialize proxy and proxy_auth
        proxy = None
        proxy_auth = None

        if proxy_url:
            import re

            # Regular expression to parse proxy URL
            proxy_regex = r'^(?:([\w.-]+):([\w.-]+)@)?([\w.-]+|\d{1,3}(?:\.\d{1,3}){3}):(\d{1,5})$'

            match = re.match(proxy_regex, proxy_url)

            if match:
                username, password, ip, port = match.groups()
                proxy = f"{ip}:{port}"
                if username and password:
                    proxy_auth = (username, password)
            else:
                raise ValueError(f"Invalid proxy URL format: {proxy_url}")
        
        # Setup WebDriver
        driver, wait = setup_driver(proxy, proxy_auth)

        # Create a DiceAutomation instance with filters
        new_processed_jobs_file_path = processed_jobs_file_path.split('.json')[0] + get_gmail_name(data['username']) + '.json'

        processed_jobs_file_path = new_processed_jobs_file_path
    
        automation = DiceAutomation(
            driver=driver,
            wait=wait,
            username=data['username'],
            password=data['password'],
            keyword=data['keyword'],
            location=data['location'],
            max_applications=int(data['max_applications']),
            filters=filters,
            status_callback=status_callback,
            processed_jobs_file_path=new_processed_jobs_file_path
        )

        # Update config with current resume path
        from config import RESUME_SETTINGS
        RESUME_SETTINGS['path'] = current_resume_path
        print(f"Updated resume path in config: {RESUME_SETTINGS['path']}")  # Debug print
        # Validate login
        if not automation.login():
            driver.quit()
            return jsonify({"error": "Invalid credentials. Please check your username and password."}), 401

        # Start the automation in a separate thread
        def run_automation():
            try:
                print("Starting automation with filters:", filters)
                print("Using resume path:", current_resume_path)
                result = automation.run()
                # Debug print
                print("=" * 30)
                print("Automation Result:")
                print("=" * 30)
                print(json.dumps(result, indent=4))
                print("=" * 30)
            except Exception as e:
                print(f"Error in automation thread: {e}")  # Debug print
            finally:
                driver.quit()

        automation_thread = threading.Thread(target=run_automation)
        automation_thread.daemon = True
        automation_thread.start()

        return jsonify({
            "message": "Login successful. Automation started!",
            "filters_applied": filters,
            "resume_path": current_resume_path
        }), 200

    except Exception as e:
        if 'driver' in locals():
            driver.quit()
        print(f"Error starting automation: {e}")  # Debug print
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def get_status():
    """Return the current automation status."""
    return jsonify(automation_status)

def is_port_in_use(port):
    """Check if a port is in use on any local interface."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Check 127.0.0.1 (localhost)
        if s.connect_ex(('127.0.0.1', port)) == 0:
            return True
        # Check 0.0.0.0 (all interfaces)
        if s.connect_ex(('0.0.0.0', port)) == 0:
            return True
    return False

def start_server(app, host, port):
    """Start the server in a separate thread."""
    server_thread = Thread(target=serve, args=(app,), kwargs={'host': host, 'port': port})
    server_thread.daemon = True  # Allow the thread to exit when the main program exits
    server_thread.start()
    return server_thread

def start_app():

    # print(f"Template directory: {template_dir}")
    # print(f"Static directory: {static_dir}")
    # print(f"Upload directory: {UPLOAD_FOLDER}")
    
    # List of ports to try
    port_range = range(5001, 5020)

    for port in port_range:
        if is_port_in_use(port):
            print(f"Port {port} is already in use. Trying next port...")
            continue

        try:
            print(f"Attempting to start server on port {port}...")
            server_thread = start_server(app, host='0.0.0.0', port=port)
            print(f"Server started successfully on port {port}.\n")
            print("*"*53)
            print("*"+" "*51+"*")
            print(f"*  Visit the application at: http://127.0.0.1:{port}  *")
            print("*"+" "*51+"*")
            print("*"*53 + "\n")
            server_thread.join()  # Keep the main thread alive
            break
        except Exception as e:
            print(f"Failed to start on port {port} due to an error: {e}. Trying next port...")
    else:
        # If the loop exhausts all ports, raise an error
        print("Failed to start on any port in the range 5001-5009. Please specify a different port.")
        raise RuntimeError("All ports are in use.")
