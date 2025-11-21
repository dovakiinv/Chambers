import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from chambers.chambers.coordinator import TurnCoordinator

async def main():
    print("🤖 Initializing Council...")
    coord = TurnCoordinator()
    
    print("\n🏥 Running Health Checks...")
    results = await coord.health_check_all()
    
    for ai, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {ai.capitalize()}")

    print("\n🔄 Testing Rotation...")
    for i in range(4):
        speaker = coord.get_next_speaker()
        print(f"Turn {i+1}: {speaker}")

if __name__ == "__main__":
    asyncio.run(main())

