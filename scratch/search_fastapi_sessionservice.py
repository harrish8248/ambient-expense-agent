import re

path = r'C:\Users\harri\OneDrive\Documents\Day 4\ambient-expense-agent\.venv\Lib\site-packages\google\adk\cli\fast_api.py'

with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Let's find occurrences of session_service
matches = [m.start() for m in re.finditer("session_service", content)]
for m in matches:
    start_line = content.count("\n", 0, m) + 1
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        print(f"--- Occurrence near line {start_line} ---")
        for i in range(max(0, start_line - 3), min(len(lines), start_line + 5)):
            print(f"{i+1}: {lines[i].rstrip()}")
