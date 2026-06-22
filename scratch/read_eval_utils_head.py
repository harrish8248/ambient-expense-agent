path = r"C:\Users\harri\AppData\Local\Programs\Python\Python313\Lib\site-packages\google\agents\cli\eval\eval_utils.py"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
    for idx, line in enumerate(lines[:100]):
        print(f"{idx+1}: {line.rstrip()}")
