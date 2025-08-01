import os
import sys
import subprocess
import json
import requests
from pathlib import Path

if len(sys.argv) < 3:
    print("❌ Missing required arguments: INFRACOST_API_KEY and GITHUB_TOKEN")
    exit(1)

INFRACOST_API_KEY = sys.argv[1]
GITHUB_TOKEN = sys.argv[2]

# Export for subprocess
os.environ["INFRACOST_API_KEY"] = INFRACOST_API_KEY

REPO = os.getenv("GITHUB_REPOSITORY")
PR_NUMBER = os.getenv("GITHUB_REF").split('/')[-2]

# Debug output — remove in production
print(f"[DEBUG] Retrieved INFRACOST_API_KEY: {INFRACOST_API_KEY}")

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
