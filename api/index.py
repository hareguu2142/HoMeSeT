from flask import Flask, request, redirect, url_for, render_template, flash, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bs4 import BeautifulSoup
from datetime import datetime
from github import Github, GithubException
import os
import base64
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# .env 파일 로드
load_dotenv()

# 환경 변수에서 값을 가져옴
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
MONGO_URI = os.getenv('MONGO_URI')

# Flask 애플리케이션 설정
app = Flask(__name__, template_folder='../templates')
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'fallback_secret_key')  # 환경 변수에서 비밀 키 가져오기

# 업로드 설정
ALLOWED_EXTENSIONS_HTML = {'html', 'htm'}
ALLOWED_EXTENSIONS_IMAGES = {'png', 'jpg', 'jpeg', 'gif', 'svg'}

# MongoDB 클라이언트 설정
client = MongoClient(MONGO_URI)
db = client.pages
collection = db.HoMe

# GitHub 설정
g = Github(GITHUB_TOKEN)
try:
    repo = g.get_repo(GITHUB_REPO)
except GithubException as e:
    print(f"GitHub 리포지토리 접근 중 오류 발생: {e}")
    repo = None

def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def upload_to_github_binary(path, content, commit_message, is_binary=False):
    try:
        encoded_content = base64.b64encode(content).decode('utf-8') if is_binary else content
        try:
            existing_file = repo.get_contents(path)
            repo.update_file(path, commit_message, encoded_content, existing_file.sha, branch="main")
        except GithubException as e:
            if e.status == 404:
                repo.create_file(path, commit_message, encoded_content, branch="main")
            else:
                raise e
    except GithubException as e:
        print(f"GitHub 업로드 중 오류 발생: {e}")
        raise

@app.route('/')
def index():
    # 최근 5개의 게시물만 가져오도록 수정
    posts = collection.find().sort('date', -1).limit(5)
    return render_template('index.html', posts=posts)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        if 'html_file' not in request.files:
            return handle_error('HTML 파일이 없습니다.')
        
        html_file = request.files['html_file']
        if html_file.filename == '':
            return handle_error('선택된 HTML 파일이 없습니다.')
        
        if html_file and allowed_file(html_file.filename, ALLOWED_EXTENSIONS_HTML):
            return process_upload(html_file)
        else:
            return handle_error('허용되지 않은 파일 형식입니다.')
    
    return render_template('upload.html')

def handle_error(message):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': message}), 400
    flash(message)
    return redirect(request.url)

def process_upload(html_file):
    html_filename = secure_filename(html_file.filename)
    html_content = html_file.read().decode('utf-8')

    # HTML 파일 내 이미지 경로 수정
    soup = BeautifulSoup(html_content, 'html.parser')
    images = soup.find_all('img')
    for img in images:
        src = img.get('src')
        if src:
            image_filename = os.path.basename(src)
            new_src = f"/images/{image_filename}"
            img['src'] = new_src

    modified_html = str(soup)

    # GitHub에 HTML 파일 업로드
    html_path = f"public/pages/{html_filename}"
    try:
        upload_to_github_binary(html_path, modified_html, f"Add/update HTML file: {html_filename}", False)
    except GithubException as e:
        return handle_error(f"GitHub 업로드 중 오류 발생: {e.data.get('message', '알 수 없는 오류')}")

    # 이미지 파일 업로드 처리
    image_files = request.files.getlist('image_files')
    uploaded_images = []
    for image in image_files:
        if image and allowed_file(image.filename, ALLOWED_EXTENSIONS_IMAGES):
            image_filename = secure_filename(image.filename)
            image_content = image.read()
            image_path = f"public/images/{image_filename}"
            try:
                upload_to_github_binary(image_path, image_content, f"Add/update image file: {image_filename}", True)
                uploaded_images.append(image_filename)
            except GithubException as e:
                flash(f"{image.filename} 업로드 중 오류 발생: {e.data.get('message', '알 수 없는 오류')}")
        else:
            flash(f"{image.filename}은(는) 허용되지 않는 파일 형식입니다.")

    # 비밀번호 처리
    password = request.form.get('password')
    if not password:
        return handle_error('비밀번호는 필수 입력 사항입니다.')
    hashed_password = generate_password_hash(password)

    # MongoDB에 데이터 저장 또는 업데이트
    name = os.path.splitext(html_filename)[0]
    document = {
        'name': name,
        'title': request.form.get('title'),
        'content': request.form.get('content'),
        'date': parse_date(request.form.get('date')),
        'filename': html_filename,
        'images': uploaded_images,
        'password': hashed_password  # 해싱된 비밀번호 추가
    }

    existing_doc = collection.find_one({'name': name})
    if existing_doc:
        collection.update_one({'_id': existing_doc['_id']}, {'$set': document})
        success_message = '파일 업로드 및 데이터베이스 업데이트 완료'
    else:
        collection.insert_one(document)
        success_message = '파일 업로드 및 데이터베이스 저장 완료'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': True, 'message': success_message}), 200
    flash(success_message)
    return redirect(url_for('index'))

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return datetime.now()

@app.route('/check_existing', methods=['POST'])
def check_existing():
    filename = request.json.get('filename')
    name = os.path.splitext(filename)[0]
    existing_doc = collection.find_one({'name': name})
    if existing_doc:
        return jsonify({
            'exists': True,
            'name': existing_doc.get('name', ''),
            'title': existing_doc.get('title', ''),
            'content': existing_doc.get('content', ''),
            'date': existing_doc.get('date').strftime('%Y-%m-%d') if existing_doc.get('date') else ''
        })
    return jsonify({'exists': False})

@app.template_filter('format_date')
def format_date(value):
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return value

if __name__ == '__main__':
    if repo is None:
        print("GitHub 리포지토리에 접근할 수 없습니다. 환경 변수를 확인하세요.")
    else:
        app.run(debug=True)
