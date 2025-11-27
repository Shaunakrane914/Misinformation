"""Test script to verify Apify integration"""
import os
from dotenv import load_dotenv
from backend.agents.trending_agent import TrendingAgent

# Load environment variables
load_dotenv()

# Check token
token = os.getenv("APIFY_TOKEN")
print(f"APIFY_TOKEN: {token[:20]}..." if token else "NOT FOUND")

# Create agent
agent = TrendingAgent()
print(f"Agent client: {agent.client}")

# Test scan
print("\n=== Running scan test ===")
result = agent.scan(
    asset_name="Deepika Padukone",
    identifiers={"instagram_url": "https://www.instagram.com/viralbhayani/"}
)

print(f"\npaparazzi count: {result['counts']['paparazzi']}")
print(f"News count: {result['counts']['news']}")

if result['sources']['paparazzi']:
    print(f"\nFirst paparazzi item: {result['sources']['paparazzi'][0]}")
else:
    print("\nNo paparazzi items fetched!")

if result['sources']['news']:
    print(f"\nFirst news item: {result['sources']['news'][0]}")
