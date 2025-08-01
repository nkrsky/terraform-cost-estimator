import os
import subprocess
import json
import requests
from pathlib import Path

# 🔐 Provide your API key securely here
HARDCODED_API_KEY = "test_dummy_api_key_123456789"

def set_infracost_api_key(api_key: str):
    result = subprocess.run(
        ["infracost", "configure", "set", "api_key", api_key],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("❌ Failed to set Infracost API key:", result.stderr)
        exit(1)

def get_infracost_api_key():
    result = subprocess.run(
        ["infracost", "configure", "get", "api_key"],
        capture_output=True,
        text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

# Set the API key
set_infracost_api_key(HARDCODED_API_KEY)

# Get it from config to confirm
INFRACOST_API_KEY = get_infracost_api_key()
if not INFRACOST_API_KEY:
    print("❌ Infracost API key not set.")
    exit(1)

# Export for subprocess CLI calls
os.environ["INFRACOST_API_KEY"] = INFRACOST_API_KEY

GITHUB_TOKEN = os.getenv("INFRACOST_GITHUB_TOKEN")
REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("GITHUB_REF").split('/')[-2]

print(f"[DEBUG] INFRACOST_API_KEY set to: {INFRACOST_API_KEY}")  # Optional debug

def run_infracost(plan_file):
    result = subprocess.run([
        "infracost", "breakdown",
        "--path", plan_file,
        "--format", "json",
        "--log-level", "error"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Infracost failed on {plan_file}: {result.stderr}")
        return None
    return json.loads(result.stdout)

def summarize_costs(infracost_json):
    resources = infracost_json.get("projects", [])[0].get("breakdown", {}).get("resources", [])
    total_monthly_cost = infracost_json.get("projects", [])[0].get("pastTotalMonthlyCost", 0.0)
    summary_lines = []
    for r in resources:
        name = r.get("name")
        cost = r.get("monthlyCost", 0.0)
        summary_lines.append(f"- `{name}` → **${cost:.2f}/mo**")
    summary = "\n".join(summary_lines)
    return f"""
### 💰 Infracost Estimate Summary

**Total Monthly Cost Estimate**: **${total_monthly_cost:.2f}**

**Resources to be created/changed:**
{summary}
"""

def post_comment(body):
    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    response = requests.post(url, json={"body": body}, headers=headers)
    if response.status_code != 201:
        print("❌ Failed to post comment:", response.text)
    else:
        print("✅ Infracost comment posted successfully.")

# Main logic
summaries = []
for tf_json in Path(".").rglob("tfplan.json"):
    print(f"🔍 Analyzing: {tf_json}")
    infracost_output = run_infracost(str(tf_json))
    if infracost_output:
        summaries.append(summarize_costs(infracost_output))

if summaries:
    post_comment("\n---\n".join(summaries))
else:
    print("⚠️ No tfplan.json files found or Infracost failed.")
