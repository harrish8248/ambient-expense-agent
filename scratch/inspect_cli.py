import os

def main():
    base = r"C:\Users\harri\AppData\Local\Programs\Python\Python313\Lib\site-packages\google\agents\cli"
    if os.path.exists(base):
        print(f"Listing {base}:")
        for root, dirs, files in os.walk(base):
            for file in files:
                rel = os.path.relpath(os.path.join(root, file), base)
                print(f"  {rel}")
    else:
        print(f"Base not found: {base}")

if __name__ == "__main__":
    main()
