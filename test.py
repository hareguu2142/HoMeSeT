import requests
import base64
import json

# 사용자 설정
TOKEN = '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'  # 생성한 GitHub 토큰을 여기에 입력하세요
REPO = 'hareguu2142/HoMe'      # 'username/repository' 형식으로 입력하세요
FILE_PATH = 'a.txt'              # 업로드할 파일의 경로
COMMIT_MESSAGE = 'Add a.txt via script'  # 커밋 메시지
BRANCH = 'master'                   # 브랜치 이름 (master로 변경)

# GitHub API URL
url = f'https://api.github.com/repos/{REPO}/contents/{FILE_PATH}'

# 파일 내용 읽기 및 Base64 인코딩
with open(FILE_PATH, 'rb') as file:
    content = file.read()
    encoded_content = base64.b64encode(content).decode()

# 파일이 이미 존재하는지 확인하여 SHA 값을 가져오기
headers = {
    'Authorization': f'token {TOKEN}',
    'Accept': 'application/vnd.github.v3+json'
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    # 파일이 존재하면 SHA 값을 사용하여 업데이트
    sha = response.json()['sha']
    data = {
        'message': COMMIT_MESSAGE,
        'content': encoded_content,
        'sha': sha,
        'branch': BRANCH
    }
elif response.status_code == 404:
    # 파일이 존재하지 않으면 새로 생성
    data = {
        'message': COMMIT_MESSAGE,
        'content': encoded_content,
        'branch': BRANCH
    }
else:
    print(f'파일 상태 확인 실패: {response.status_code}')
    print(response.json())
    exit()

# 파일 업로드 (생성 또는 업데이트)
put_response = requests.put(url, headers=headers, data=json.dumps(data))

if put_response.status_code in [200, 201]:
    print(f'파일이 성공적으로 {"업데이트" if response.status_code == 200 else "생성"}되었습니다.')
    file_url = put_response.json()['content']['html_url']
    print(f'파일 URL: {file_url}')
else:
    print(f'파일 업로드 실패: {put_response.status_code}')
    print(put_response.json())
