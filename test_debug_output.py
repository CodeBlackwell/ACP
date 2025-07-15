#!/usr/bin/env python3
"""
Debug the coder output to understand the format
"""

import re

# Sample output from the coder (from the error message)
sample_output = """✅ PROJECT CREATED: app_session_exec_20250715_165741_60840be1
📁 Location: /Users/lechristopherblackwell/Desktop/Ground_up/rebuild/generated/app_session_exec_20250715_165741_60840be1
🔗 Session ID: exec_20250715_165741_60840be1
📄 Files created: 5
🕐 Generated: 2025-07-15 16:57:48

Files:
  - app.py
  - requirements.txt
  - README.md
  - .gitignore
  - test_app.py

--- IMPLEMENTATION DETAILS ---


FILENAME: app.py
```python
def main():
    print("Hello from the test!")

if __name__ == "__main__":
    main()
```"""

print("Sample output:")
print(sample_output)
print("\n" + "="*60 + "\n")

# Test different regex patterns
patterns = [
    r'📁 Location: ([^\n]+)',
    r'Location: ([^\n]+)',
    r'📁 Location: (.+?)(?:\n|$)',
    r'Location: (.+?)(?:\n|$)',
    r'📁\s*Location:\s*([^\n]+)',
]

for pattern in patterns:
    print(f"Testing pattern: {pattern}")
    match = re.search(pattern, sample_output)
    if match:
        print(f"  ✅ Match found: '{match.group(1)}'")
    else:
        print(f"  ❌ No match")
    print()