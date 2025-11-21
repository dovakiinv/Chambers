import asyncio
import logging
import sys
from pathlib import Path
import traceback

# Ensure path is correct for imports
sys.path.append(str(Path(__file__).parent.parent))

# Setup verbose logging to stdout
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

from chambers.config import config
from chambers.models.claude import ClaudeClient
from chambers.models.gemini import GeminiClient
from chambers.models.grok import GrokClient

async def test_client(name, client_cls):
    print(f"\n--- Testing {name} ---")
    try:
        client = client_cls()
        print(f"Client initialized. Model: {client.model}")
        
        if hasattr(client, 'api_key'):
            masked = client.api_key[:8] + "..." if client.api_key else "None"
            print(f"API Key: {masked}")
        
        print("Attempting health check...")
        healthy = await client.health_check()
        
        if healthy:
            print(f"✅ {name}: HEALTHY")
        else:
            print(f"❌ {name}: UNHEALTHY (False returned)")
            
    except Exception as e:
        print(f"❌ {name}: CRASHED")
        print(f"Error: {e}")
        traceback.print_exc()

async def main():
    print("🔍 DEBUG: AI Client Health Checks")
    print(f"Config loaded from: {Path('.env').absolute()}")
    
    await test_client("Claude", ClaudeClient)
    await test_client("Gemini", GeminiClient)
    await test_client("Grok", GrokClient)

if __name__ == "__main__":
    asyncio.run(main())
