import os
import base64
from flask import Flask, request, redirect, url_for, render_template, flash, jsonify
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bs4 import BeautifulSoup
from datetime import datetime
from github import Github, GithubException
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 환경 변수에서 값을 가져옴
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO')
MONGO_URI = os.getenv('MONGO_URI')


# Flask 애플리케이션 설정
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 실제 배포 시 안전한 비밀 키 사용

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
    """
    GitHub에 파일을 업로드합니다.
    
    :param path: GitHub 리포지토리 내 파일 경로
    :param content: 파일 내용 (텍스트 또는 바이너리 데이터)
    :param commit_message: 커밋 메시지
    :param is_binary: 파일이 바이너리인지 여부
    """
    try:
        if is_binary:
            # 바이너리 파일의 경우 Base64로 인코딩
            encoded_content = base64.b64encode(content).decode('utf-8')
        else:
            # 텍스트 파일의 경우 원시 문자열
            encoded_content = content

        existing_file = repo.get_contents(path)
        repo.update_file(
            path=path,
            message=commit_message,
            content=encoded_content,
            sha=existing_file.sha,
            branch="master"  # 리포지토리의 기본 브랜치 이름으로 수정
        )
    except GithubException as e:
        if e.status == 404:
            # 파일이 없으면 새로 생성
            repo.create_file(
                path=path,
                message=commit_message,
                content=encoded_content,
                branch="master"  # 리포지토리의 기본 브랜치 이름으로 수정
            )
        else:
            raise e

@app.route('/')
def index():
    posts = collection.find().sort('date', -1)
    return render_template('index.html', posts=posts)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # HTML 파일 업로드 처리
        if 'html_file' not in request.files:
            message = 'HTML 파일이 없습니다.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': message}), 400
            flash(message)
            return redirect(request.url)
        
        html_file = request.files['html_file']
        if html_file.filename == '':
            message = '선택된 HTML 파일이 없습니다.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': message}), 400
            flash(message)
            return redirect(request.url)
        
        if html_file and allowed_file(html_file.filename, ALLOWED_EXTENSIONS_HTML):
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

            # GitHub에 HTML 파일 업로드 (텍스트 파일로 처리)
            html_path = f"public/pages/{html_filename}"
            try:
                # 기존 파일인지 확인하여 커밋 메시지 설정
                try:
                    existing_file = repo.get_contents(html_path)
                    commit_message = f"Update HTML file: {html_filename}"
                except GithubException as e:
                    if e.status == 404:
                        commit_message = f"Add HTML file: {html_filename}"
                    else:
                        raise e

                upload_to_github_binary(
                    path=html_path, 
                    content=modified_html, 
                    commit_message=commit_message,
                    is_binary=False  # 텍스트 파일로 처리
                )
            except GithubException as e:
                flash(f"GitHub 업로드 중 오류 발생: {e.data.get('message', '알 수 없는 오류')}")
                return redirect(request.url)

            # 이미지 파일 업로드 처리
            image_files = request.files.getlist('image_files')
            uploaded_images = []
            for image in image_files:
                if image and allowed_file(image.filename, ALLOWED_EXTENSIONS_IMAGES):
                    image_filename = secure_filename(image.filename)
                    image_content = image.read()
                    image_path = f"public/images/{image_filename}"
                    try:
                        upload_to_github_binary(
                            path=image_path, 
                            content=image_content, 
                            commit_message=f"Add/update image file: {image_filename}",
                            is_binary=True  # 바이너리 파일로 처리
                        )
                        uploaded_images.append(image_filename)
                    except GithubException as e:
                        flash(f"{image.filename} 업로드 중 오류 발생: {e.data.get('message', '알 수 없는 오류')}")
                        # 계속해서 다음 이미지를 업로드하려면 continue 사용
                        continue
                else:
                    flash(f"{image.filename}은(는) 허용되지 않는 파일 형식입니다.")

            # MongoDB에 데이터 저장 또는 업데이트
            name = os.path.splitext(html_filename)[0]  # 확장자 제거
            title = request.form.get('title')
            content = request.form.get('content')
            date_str = request.form.get('date')
            try:
                date = datetime.strptime(date_str, '%Y-%m-%d')
            except (ValueError, TypeError):
                date = datetime.now()

            document = {
                'name': name,
                'title': title,
                'content': content,
                'date': date,
                'filename': html_filename,
                'images': uploaded_images
            }

            # 동일한 name이 있는지 확인
            existing_doc = collection.find_one({'name': name})
            if existing_doc:
                # 업데이트
                collection.update_one({'_id': existing_doc['_id']}, {'$set': document})
                success_message = '파일 업로드 및 데이터베이스 업데이트 완료'
            else:
                # 새로 삽입
                collection.insert_one(document)
                success_message = '파일 업로드 및 데이터베이스 저장 완료'

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': success_message}), 200
            flash(success_message)
            return redirect(url_for('index'))
        else:
            message = '허용되지 않은 파일 형식입니다.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': message}), 400
            flash(message)
            return redirect(request.url)
    return render_template('upload.html')

@app.route('/check_existing', methods=['POST'])
def check_existing():
    filename = request.json.get('filename')
    name = os.path.splitext(filename)[0]  # 확장자 제거
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
        parsed_date = datetime.strptime(value, '%Y-%m-%d')
        return parsed_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError):
        return value  # 파싱 실패 시 원래 값을 반환

if __name__ == '__main__':
    if repo is None:
        print("GitHub 리포지토리에 접근할 수 없습니다. 환경 변수를 확인하세요.")
    else:
        app.run(debug=True)
