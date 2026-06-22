import os
import sys

site_packages = [p for p in sys.path if "site-packages" in p]

found = []
for sp in site_packages:
    for root, dirs, files in os.walk(sp):
        if "google" in root and "eval" in root:
            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            if "traces" in content or "trace" in content:
                                found.append(path)
                    except Exception:
                        pass

print("Eval-related CLI files:")
for f in set(found):
    print(f)
