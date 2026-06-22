import os

def main():
    src_path = r"C:\Users\harri\AppData\Local\Programs\Python\Python313\Lib\site-packages\vertexai\_genai\client.py"
    dest_path = r"c:\Users\harri\OneDrive\Documents\Day 4\ambient-expense-agent\scratch\client_src.py"
    
    if os.path.exists(src_path):
        print(f"Reading from {src_path}...")
        with open(src_path, "r", encoding="utf-8") as f:
            content = f.read()
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("Copied successfully.")
    else:
        print(f"File not found: {src_path}")

if __name__ == "__main__":
    main()
