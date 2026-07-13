import os
import asyncio
import urllib.parse

from last_translation_benchmark.db import get_users, get_submissions, _open_db
from last_translation_benchmark.utils import send_email
os.environ["HOST_PUBLIC"] = "https://last-translation-benchmark.vilda.net"

SUBJECT = "Last Translation Benchmark - Action Required: Returned Submissions"
BODY_TEMPLATE = """Dear {name},

We noticed that you have made submissions to the Last Translation Benchmark project, but currently all of them have been returned for revisions. 
Please review the feedback left by our reviewers, update your submissions, and submit them again!

You can login and review your returned submissions using the following link:

{login_link}

Let us know if you have any questions.
Best, the LTB team
"""



async def has_sent_subject(email: str, subject: str) -> bool:
    async with _open_db() as db:
        async with db.execute(
            "SELECT 1 FROM sent_emails WHERE to_email = ? AND subject = ?",
            (email, subject)
        ) as cur:
            return await cur.fetchone() is not None

async def main():
    print("Fetching users and submissions...")
    users = await get_users()
    submissions = await get_submissions()
    
    # Group submissions by user_id
    user_submissions = {}
    for sub in submissions:
        uid = sub.get("user_id")
        if uid not in user_submissions:
            user_submissions[uid] = []
        user_submissions[uid].append(sub)
    
    for user in users:
        uid = user.get("id")
        email = user.get("email")
        name = user.get("name")
        username = user.get("username")
        login_link = f"https://last-translation-benchmark.vilda.net/?user={urllib.parse.quote(str(username))}&token={user.get('magic_token')}"
        
        # User must have an email
        if not email:
            continue
            
        subs = user_submissions.get(uid, [])
        # They must have at least one submission
        if not subs:
            continue
            
        # ALL their submissions must be returned
        all_returned = all(s.get("status") == "return" for s in subs)
        if not all_returned:
            continue
            
        # Check notification consent
        if not user.get("notification_consent", True):
            continue
            
        # Check if email already sent
        already_sent = await has_sent_subject(email, SUBJECT)
        if already_sent:
            continue

        while True:
            ans = input(f"\nSend to {name} <{email}> ({len(subs)} submissions)? (y/n): ").strip().lower()
            if ans in ('y', 'n'):
                break
            
        if ans == 'y':
            body = BODY_TEMPLATE.format(name=name, login_link=login_link)
            # send_email automatically adds to the sent_emails database
            success = await send_email(email, SUBJECT, body, user_obj=user)
            if success:
                print("Email sent successfully.")
            else:
                print("Failed to send email.")
        else:
            print("Skipped.")

if __name__ == "__main__":
    asyncio.run(main())
