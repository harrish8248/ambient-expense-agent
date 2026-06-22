path = r"C:\Users\AppData\.. \Python\Python313\Lib\site-packages\google\agents\cli\eval\_inference_runner.py"
# Let's search for the file path if it exists
import os
possible_paths = [
    r"C:\Users\harri\AppData\Local\Programs\Python\Python313\Lib\site-packages\google\agents\cli\eval\_inference_runner.py"
]

for p in possible_paths:
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            print(f.read())
