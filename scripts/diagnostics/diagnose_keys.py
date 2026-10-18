"""Offline presence checks only. Never spends quota or prints credential values."""
import os
from dotenv import load_dotenv


def main():
    load_dotenv()
    print("=== Offline credential presence (not validity/connectivity) ===")
    for name in ("GEMINI_API_KEY", "GEMINI_API_KEY_1", "GEMINI_API_KEY_2",
                 "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        print(f"{name}: {'present' if os.getenv(name) else 'missing'}")
    print("Generation requests: 0. No provider or database request performed.")


if __name__ == "__main__":
    main()
