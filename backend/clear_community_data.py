#!/usr/bin/env python3
"""
Script to clear all community posts data from the database.
This will remove all posts from the community feed.
"""

import asyncio
import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.config.database import db


async def clear_community_posts():
    """Clear all community posts from the database."""
    try:
        # Count posts before deletion
        count_before = await db.community_posts.count_documents({})
        print(f"Found {count_before} community posts in the database.")

        if count_before == 0:
            print("No posts to delete.")
            return

        # Confirm deletion
        confirm = input(f"Are you sure you want to delete all {count_before} community posts? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Operation cancelled.")
            return

        # Delete all posts
        result = await db.community_posts.delete_many({})
        print(f"Successfully deleted {result.deleted_count} community posts.")

        # Also clear communities collection if needed
        community_count = await db.communities.count_documents({})
        if community_count > 0:
            confirm_communities = input(f"Also clear {community_count} communities? (yes/no): ")
            if confirm_communities.lower() == 'yes':
                result = await db.communities.delete_many({})
                print(f"Successfully deleted {result.deleted_count} communities.")

    except Exception as e:
        print(f"Error clearing community posts: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("Clearing community posts data...")
    asyncio.run(clear_community_posts())
    print("Done!")