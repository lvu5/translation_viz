import asyncio
import os
import sys

# Add the parent directory to sys.path to import server module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.db import get_submissions, save_submission

async def migrate():
    submissions = await get_submissions()
    print(f"Migrating {len(submissions)} submissions...")
    
    for s in submissions:
        if "reviewed_by" not in s:
            s["reviewed_by"] = None
            await save_submission(s)
            
    print("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
