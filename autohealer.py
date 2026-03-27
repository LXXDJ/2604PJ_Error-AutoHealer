import os
import subprocess
import requests
from openai import OpenAI

# 설정
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = "LXXDJ/2604PJ_Error-AutoHealer"
TARGET_FILE = "buggy_code.py"

client = OpenAI(api_key=OPENAI_API_KEY)

# 1. 에러 감지
print("=== 1. 에러 감지 ===")
result = subprocess.run(
    ["python3", TARGET_FILE],
    capture_output=True, text=True
)
error_log = result.stderr
code = open(TARGET_FILE).read()
print(error_log)

if not error_log:
    print("에러 없음! 종료합니다.")
    exit()

# 2. LLM 코드 수정
print("=== 2. LLM 코드 수정 중... ===")
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {
            "role": "system",
            "content": "코드의 버그를 수정해서 전체 코드만 출력하세요. 설명 없이 코드만."
        },
        {
            "role": "user",
            "content": f"에러:\n{error_log}\n\n코드:\n{code}"
        }
    ]
)
fixed_code = response.choices[0].message.content
fixed_code = fixed_code.replace("```python", "").replace("```", "").strip()
print(fixed_code)

# 3. GitHub PR 자동 생성
print("=== 3. GitHub PR 생성 중... ===")
headers = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# 현재 main 브랜치 SHA 가져오기
ref_res = requests.get(
    f"https://api.github.com/repos/{GITHUB_REPO}/git/ref/heads/main",
    headers=headers
)
sha = ref_res.json()["object"]["sha"]

# 새 브랜치 생성
branch_name = "autofix/buggy-code"
requests.post(
    f"https://api.github.com/repos/{GITHUB_REPO}/git/refs",
    headers=headers,
    json={"ref": f"refs/heads/{branch_name}", "sha": sha}
)

# 파일 내용 가져오기 (SHA 필요)
file_res = requests.get(
    f"https://api.github.com/repos/{GITHUB_REPO}/contents/{TARGET_FILE}",
    headers=headers
)
file_sha = file_res.json()["sha"]

# 수정된 파일 push
import base64
requests.put(
    f"https://api.github.com/repos/{GITHUB_REPO}/contents/{TARGET_FILE}",
    headers=headers,
    json={
        "message": "fix: LLM이 자동으로 버그 수정",
        "content": base64.b64encode(fixed_code.encode()).decode(),
        "sha": file_sha,
        "branch": branch_name
    }
)

# PR 생성
pr_res = requests.post(
    f"https://api.github.com/repos/{GITHUB_REPO}/pulls",
    headers=headers,
    json={
        "title": "🤖 자동 버그 수정 PR",
        "body": f"## 감지된 에러\n```\n{error_log}\n```\n## LLM 수정 내용\n```python\n{fixed_code}\n```",
        "head": branch_name,
        "base": "main"
    }
)
pr_url = pr_res.json().get("html_url", "PR 생성 실패")
print(f"✅ PR 생성 완료: {pr_url}")
