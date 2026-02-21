import os
import sys
from dotenv import load_dotenv
from groq import Groq, AuthenticationError, APIConnectionError

def test_groq_connection():
    print("--- Groq API Connection Test ---\n")

    # 1. Load environment variables
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    print(f"Loading environment from: {env_path}")
    
    if not os.path.exists(env_path):
        print("ERROR: .env file not found!")
        return

    load_dotenv(env_path)

    # 2. Check for API Key
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("ERROR: GROQ_API_KEY not found in environment variables.")
        return

    # Mask key for display
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "****"
    print(f"API Key loaded: {masked_key}")

    if not api_key.startswith("gsk_"):
        print("WARNING: Key does not start with 'gsk_'. It might be invalid.")

    # 3. Initialize Client
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        print(f"ERROR: Failed to initialize Groq client: {e}")
        return

    # 4. Attempt API Call
    model_name = "llama-3.3-70b-versatile"
    print(f"\nAttempting to call Groq API (model: {model_name})...")
    
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": "Hello! Are you working?",
                }
            ],
            model=model_name,
        )
        
        print("\nSUCCESS! Connection established.")
        print("-" * 30)
        print(f"Response: {chat_completion.choices[0].message.content}")
        print("-" * 30)

    except AuthenticationError as e:
        print("\nFAILED: Authentication Error (401)")
        print(f"Details: {e}")
        print("\nTroubleshooting:")
        print("1. Check if the API key in .env matches your Groq Console key exactly.")
        print("2. Ensure there are no extra spaces or quotes in the .env file.")
        print("   Correct: GROQ_API_KEY=gsk_xyz...")
        print("   Incorrect: GROQ_API_KEY=\"gsk_xyz...\" (sometimes quotes cause issues if not parsed right)")
        print("3. Verify the key is active in console.groq.com.")

    except APIConnectionError as e:
        print("\nFAILED: Connection Error")
        print(f"Details: {e}")
        print("Check your internet connection or firewall settings.")

    except Exception as e:
        print(f"\nFAILED: An unexpected error occurred: {e}")

if __name__ == "__main__":
    test_groq_connection()
