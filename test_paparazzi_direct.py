"""Direct test of fetch_paparazzi method"""
import logging
import os
from dotenv import load_dotenv

# Set up logging to see all messages
logging.basicConfig(level=logging.INFO, format='%(name)s - %(levelname)s - %(message)s')

load_dotenv()

from backend.agents.trending_agent import TrendingAgent

agent = TrendingAgent()

print("=" * 60)
print("Testing fetch_paparazzi directly")
print("=" * 60)

result = agent.fetch_paparazzi("https://www.instagram.com/viralbhayani/")

print(f"\nResult: {len(result)} items")
if result:
    print("\nFirst item:")
    print(result[0])
else:
    print("\nNo items returned - check logs above for errors")
