import os
from dotenv import load_dotenv

print("Checking env setup...")
try:
    with open(".env", "r") as f:
        print(f"Found .env file. Content preview: {f.read(50)}")
except FileNotFoundError:
    print(".env file NOT found in current directory")

load_dotenv()
key = os.getenv("GROQ_API_KEY")
if key:
    print(f"GROQ_API_KEY found: {key[:5]}...")
else:
    print("GROQ_API_KEY NOT found in environment")
