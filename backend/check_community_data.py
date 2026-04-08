#!/usr/bin/env python3
"""
Check community data in the database.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config.database import db


async def check_data():
    """Check community data."""
    try:
        posts_count = await db.community_posts.count_documents({})
        communities_count = await db.communities.count_documents({})

        print(f"Community posts: {posts_count}")
        print(f"Communities: {communities_count}")

        if communities_count > 0:
            communities = await db.communities.find({}).to_list(length=10)
            print("Communities found:")
            for comm in communities:
                name = comm.get('name', 'unnamed')
                members = len(comm.get('members', []))
                print(f"  - {name} ({members} members)")

    except Exception as e:
        print(f"Error checking data: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(check_data())