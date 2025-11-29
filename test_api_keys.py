"""
API Key Testing Script
======================
Tests all API keys (Gemini, Yahoo Finance, Apify) and tries different Gemini models.
"""

import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai
import requests
from apify_client import ApifyClient

# Load environment variables
load_dotenv()

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print a formatted header."""
    print(f"\n{BLUE}{'=' * 80}{RESET}")
    print(f"{BLUE}{text.center(80)}{RESET}")
    print(f"{BLUE}{'=' * 80}{RESET}\n")

def print_success(text):
    """Print success message."""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    """Print error message."""
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    """Print warning message."""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    """Print info message."""
    print(f"{BLUE}ℹ️  {text}{RESET}")


# ============================================================================
# GEMINI API KEY TESTS
# ============================================================================

def test_gemini_keys():
    """Test all Gemini API keys with different models."""
    print_header("TESTING GEMINI API KEYS")
    
    # Load all Gemini keys
    keys = {
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "GEMINI_API_KEY_1": os.getenv("GEMINI_API_KEY_1"),
        "GEMINI_API_KEY_2": os.getenv("GEMINI_API_KEY_2"),
    }
    
    # Models to test
    models_to_test = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-lite",  # Added for testing
    ]
    
    results = {}
    
    for key_name, api_key in keys.items():
        if not api_key:
            print_warning(f"{key_name}: Not found in .env")
            continue
            
        print_info(f"Testing {key_name}: {api_key[:15]}...")
        results[key_name] = {}
        
        for model_name in models_to_test:
            try:
                # Configure API key
                genai.configure(api_key=api_key)
                
                # Try to create model and generate content
                model = genai.GenerativeModel(model_name)
                response = model.generate_content("Say 'Hello' in one word")
                
                # Check if we got a response
                if response and response.text:
                    print_success(f"  {model_name}: Working! Response: {response.text.strip()[:50]}")
                    results[key_name][model_name] = "✅ Working"
                else:
                    print_error(f"  {model_name}: No response")
                    results[key_name][model_name] = "❌ No response"
                    
            except Exception as e:
                error_msg = str(e)
                if "404" in error_msg or "not found" in error_msg.lower():
                    print_error(f"  {model_name}: Model not found (404)")
                    results[key_name][model_name] = "❌ Model not found"
                elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                    print_error(f"  {model_name}: Quota/Rate limit exceeded")
                    results[key_name][model_name] = "❌ Quota exceeded"
                elif "invalid" in error_msg.lower() or "api key" in error_msg.lower():
                    print_error(f"  {model_name}: Invalid API key")
                    results[key_name][model_name] = "❌ Invalid key"
                else:
                    print_error(f"  {model_name}: {error_msg[:60]}")
                    results[key_name][model_name] = f"❌ {error_msg[:30]}"
    
    return results


# ============================================================================
# YAHOO FINANCE API KEY TEST
# ============================================================================

def test_yahoo_finance_key():
    """Test Yahoo Finance API key."""
    print_header("TESTING YAHOO FINANCE API KEY")
    
    api_key = os.getenv("YF_API_KEY")
    
    if not api_key:
        print_warning("YF_API_KEY: Not found in .env")
        return {"status": "Not configured"}
    
    print_info(f"Testing YF_API_KEY: {api_key[:15]}...")
    
    try:
        # Test with a simple stock query
        url = "https://yfapi.net/v8/finance/chart/AAPL"
        headers = {
            'X-API-KEY': api_key,
            'accept': 'application/json'
        }
        params = {
            'range': '1d',
            'interval': '1d'
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('chart', {}).get('result'):
                print_success("Yahoo Finance API: Working!")
                return {"status": "✅ Working"}
            else:
                print_error("Yahoo Finance API: No data in response")
                return {"status": "❌ No data"}
        elif response.status_code == 401:
            print_error("Yahoo Finance API: Invalid API key (401)")
            return {"status": "❌ Invalid key"}
        elif response.status_code == 429:
            print_error("Yahoo Finance API: Rate limit exceeded (429)")
            return {"status": "❌ Rate limit"}
        else:
            print_error(f"Yahoo Finance API: HTTP {response.status_code}")
            return {"status": f"❌ HTTP {response.status_code}"}
            
    except Exception as e:
        print_error(f"Yahoo Finance API: {str(e)[:60]}")
        return {"status": f"❌ {str(e)[:30]}"}


# ============================================================================
# APIFY API KEY TEST
# ============================================================================

def test_apify_key():
    """Test Apify API key."""
    print_header("TESTING APIFY API KEY")
    
    api_key = os.getenv("APIFY_TOKEN")
    
    if not api_key:
        print_warning("APIFY_TOKEN: Not found in .env")
        return {"status": "Not configured"}
    
    print_info(f"Testing APIFY_TOKEN: {api_key[:15]}...")
    
    try:
        # Initialize client
        client = ApifyClient(api_key)
        
        # Try to list actors (simple API call)
        # This doesn't run anything, just checks if the key is valid
        response = requests.get(
            "https://api.apify.com/v2/acts",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"limit": 1},
            timeout=10
        )
        
        if response.status_code == 200:
            print_success("Apify API: Working!")
            
            # Check account info
            account_response = requests.get(
                "https://api.apify.com/v2/users/me",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10
            )
            
            if account_response.status_code == 200:
                account_data = account_response.json()
                plan = account_data.get('data', {}).get('plan', 'Unknown')
                print_info(f"  Account Plan: {plan}")
                
            return {"status": "✅ Working", "plan": plan}
        elif response.status_code == 401:
            print_error("Apify API: Invalid API key (401)")
            return {"status": "❌ Invalid key"}
        else:
            print_error(f"Apify API: HTTP {response.status_code}")
            return {"status": f"❌ HTTP {response.status_code}"}
            
    except Exception as e:
        print_error(f"Apify API: {str(e)[:60]}")
        return {"status": f"❌ {str(e)[:30]}"}


# ============================================================================
# SUMMARY REPORT
# ============================================================================

def print_summary(gemini_results, yf_result, apify_result):
    """Print a summary report of all tests."""
    print_header("TEST SUMMARY")
    
    print(f"\n{BLUE}Gemini API Keys:{RESET}")
    for key_name, models in gemini_results.items():
        print(f"\n  {key_name}:")
        for model_name, status in models.items():
            print(f"    {model_name}: {status}")
    
    print(f"\n{BLUE}Yahoo Finance API:{RESET}")
    print(f"  Status: {yf_result.get('status', 'Unknown')}")
    
    print(f"\n{BLUE}Apify API:{RESET}")
    print(f"  Status: {apify_result.get('status', 'Unknown')}")
    if 'plan' in apify_result:
        print(f"  Plan: {apify_result['plan']}")
    
    print(f"\n{BLUE}{'=' * 80}{RESET}\n")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print_header("API KEY TESTING SUITE")
    print_info("Testing all API keys and Gemini models...")
    
    # Run tests
    gemini_results = test_gemini_keys()
    yf_result = test_yahoo_finance_key()
    apify_result = test_apify_key()
    
    # Print summary
    print_summary(gemini_results, yf_result, apify_result)
    
    print_success("Testing complete!")
