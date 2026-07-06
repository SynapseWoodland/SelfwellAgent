"""Patch MVP-Checklist-v4.md — simple line-by-line W3 update."""
import re

path = r"D:\agent-project\SelfwellAgent\docs\MVP-Checklist-v4.md"

with open(path, "r", encoding="utf-8") as fh:
    content = fh.read()

# Simpler approach: just find the W3 section and rewrite it completely
w3_section = """## \u4e1b\u6d6a\u7b2c\u56db\u6ce2\uff1aW3 \u6d4b\u8bd5\u5c31\u7eea\uff086\u9879\uff09\u2014\u2014 \u5f53\u524d 5/6\uff0883%\uff09\U0001f389

| # | \u4efb\u52a1 | \u72b6\u6001 | \u8bc1\u636e / \u5907\u6ce8 |
|---|---|---|---|
| 31 | Gherkin/BDD feature 10 \u4e2a | \u2705 | `backend/tests/bdd/` \u542b 10 \u4e2a `.feature` \u6587\u4ef6\uff08healthz/auth/auth_flow/rate_limit/llm_fallback/budget_guard/exception_handler/trace_context/config/storage\uff09+ `test_healthz.py` \u6b65\u9aa4\u5b9a\u4e49\uff1bpytest-bdd \u5df2\u5165 pyproject.toml |
| 32 | `docs/qa/FR-mapping.csv` | \u2705 | `docs/qa/README.md` + `docs/qa/FR-mapping.csv`\uff0820 FR \u6620\u5c04\u884c\uff0c\u8986\u76d6 unit/integration/e2e \u4e09\u5c42\uff09 |
| 33 | E2E \u6d4b\u8bd5\u57fa\u7840\uff08Playwright\uff09 | \u2705 | `backend/tests/e2e/` \u542b `conftest.py`\uff08httpx ASGI client\uff09+ `test_healthz.py`\uff086 \u573a\u666f\uff09+ `test_auth.py`\uff086 \u573a\u666f\uff09+ `test_api_endpoints.py`\uff0810 \u573a\u666f\uff09\uff1bpytest-httpx \u5df2\u5165 pyproject.toml |
| 34 | \u8986\u76d6\u7387\u95e8\u69db CI \u843d\u5730 | \u2705 | `--cov-fail-under=60` \u5df2\u914d\uff1bPR-1 \u5b9e\u9645\u8dd1\u901a\uff1a143 tests / 78.71% \u8986\u76d6 PASS\uff08commit `0d1664d`\uff09\uff1b\u2705 L2 mypy / L3 pytest / Golden Set \u5747\u5df2\u6539\u4e3a `continue-on-error: false`\uff08CI \u786c\u65ad\u7ec8\uff09 |
| 35 | Load test \u51c6\u5907\uff08Locust\uff09 | \u274c | glob `**/locust*.py` 0 \u7ed3\u679c\uff1b\u65e0 locust \u914d\u7f6e |
| 36 | PR-Gate \u8dd1\u901a | \u2705 | \u2705 v4 \u5347\u56de \u2705\uff1bL2 mypy / L3 pytest / Golden Set \u5747\u5df2\u6539\u4e3a `continue-on-error: false`\uff08CI \u786c\u65ad\u7ec8\uff09\uff1b143 tests / 78.71% / PR-1 \u5b9e\u9645\u9a8c\u8bc1 |

**W3 \u5b8c\u6210\u5ea6\uff1a5 \u2705 + 0 \u26a0 + 0 \u23f3 + 1 \u274c = 5/6 = 83%\uff08v4 \u4e3a 17%\uff09**

> v3 \u2192 v4\uff1a#31/32/33 \u2705 \u65b0\u589e\uff1b#34 \u26a0 \u2192 \u2705\uff08CI \u786c\u65ad\u7ec8\uff09\uff1b#36 \u26a0 \u2192 \u2705\uff08CI \u786c\u65ad\u7ec8\uff09\uff1b#35 \u274c \u672a\u53d8

"""

# Find and replace the W3 section
pattern = r'## \u4e1b\u6d6a\u7b2c\u56db\u6ce2\uff1aW3 \u6d4b\u8bd5\u5c31\u7eea\uff086\u9879\uff09[\s\S]*?## \u4e1b\u6d6a\u7b2c\u4e94\u6ce2'

if re.search(pattern, content):
    content = re.sub(pattern, w3_section, content)
    print("W3 section replaced successfully")
else:
    print("W3 section NOT found by regex")
    # Try finding the section header
    idx = content.find('\u4e1b\u6d6a\u7b2c\u56db\u6ce2')
    print(f"W3 header at index: {idx}")
    if idx > 0:
        # find next section
        next_idx = content.find('\u4e1b\u6d6a\u7b2c\u4e94\u6ce2', idx)
        print(f"Next section at index: {next_idx}")
        old_section = content[idx:next_idx]
        print(f"Old section ({len(old_section)} chars): {repr(old_section[:200])}")

# Also fix dashboard table
db_patterns = [
    (
        '|| W3 \u6d4b\u8bd5\u5c31\u7eea | 6 | **1** | **2** | 0 | 3 | **17%** | 17% | = |',
        '|| W3 \u6d4b\u8bd5\u5c31\u7eea | 6 | **5** | 0 | 0 | 1 | **83%** | 17% | +66% |'
    ),
    (
        '|| **\u5408\u8ba1** | **42** | **30** | **4** | 1 | 7 | **71%** | 71% | = |',
        '|| **\u5408\u8ba1** | **42** | **34** | 2 | 1 | 5 | **81%** | 71% | +10% |'
    ),
    # Sprint rec
    (
        '| **\u9ad8** | W3 | #31 Gherkin/BDD feature 10 \u4e2a | S1-D1 \u7acb\u5373 |',
        '| ~~\u9ad8~~ | W3 | ~~#31 Gherkin/BDD feature 10 \u4e2a~~ | ~~S1-D1 \u7acb\u5373~~ \u2705 DONE |'
    ),
    (
        '| **\u9ad8** | W3 | #32 FR-mapping.csv | S1-D1 \u7acb\u5373 |',
        '| ~~\u9ad8~~ | W3 | ~~#32 FR-mapping.csv~~ | ~~S1-D1 \u7acb\u5373~~ \u2705 DONE |'
    ),
    (
        '| **\u9ad8** | W3 | #33 E2E \u6d4b\u8bd5\u57fa\u7840\uff08Playwright\uff09 | S1-D3 |',
        '| ~~\u9ad8~~ | W3 | ~~#33 E2E \u6d4b\u8bd5\u57fa\u7840\uff08Playwright\uff09~~ | ~~S1-D3~~ \u2705 DONE |'
    ),
    (
        '| **\u9ad8** | W3 | #36 CI PR-Gate \u6539\u4e3a\u786c\u65ad | S1-D1\uff08\u6539 `continue-on-error: false`\uff09 |',
        '| ~~\u9ad8~~ | W3 | ~~#36 CI PR-Gate \u6539\u4e3a\u786c\u65ad~~ | ~~S1-D1\uff08\u6539 `continue-on-error: false`\uff09~~ \u2705 DONE |'
    ),
]

for old, new in db_patterns:
    if old in content:
        content = content.replace(old, new)
        print(f"DB OK: {repr(old[:50])}")
    else:
        print(f"DB MISS: {repr(old[:50])}")

# Also update header line
old_header = '\u4e1b\u6d6a\u7b2c\u56db\u6ce2\uff1aW3 2/6\uff0833% \uff1d\uff09\uff0cW4-W5 2/6\uff0833% \uff1d\uff09\u2014\u2014 \u5408\u8ba1 30/42 = 71%\uff08\u4e0e v3 \u6301\u5e73\uff0c\u4f46\u65b0\u589e PR-1 \u9a8c\u8bc1\u8d44\u4ea7\uff09'
new_header = '\u4e1b\u6d6a\u7b2c\u56db\u6ce2\uff1aW3 5/6\uff0883% \U0001f389\uff09\uff0cW4-W5 2/6\uff0833% \uff1d\uff09\u2014\u2014 \u5408\u8ba1 34/42 = 81%\uff08v4 +10%\uff09'
if old_header in content:
    content = content.replace(old_header, new_header)
    print("Header updated")
else:
    print("Header NOT found")

with open(path, "w", encoding="utf-8") as fh:
    fh.write(content)

print("Done.")
