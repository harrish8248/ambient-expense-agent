import os

path = r"C:\Users\harri\AppData\Local\Programs\Python\Python313\Lib\site-packages\google\agents\cli\eval"
if os.path.exists(path):
    print("Files:")
    for root, dirs, files in os.walk(path):
        for file in files:
            print("  ", os.path.join(root, file))
else:
    print("Path does not exist:", path)
