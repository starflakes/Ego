"""
Instagram posting is intentionally not implemented here.

Instagram publishing goes through the Meta Graph API and requires:
  1. A Meta Developer app + your Instagram account converted to a
     Business or Creator account, linked to a Facebook Page
  2. App review for the instagram_content_publish permission if you want
     this to work for accounts other than the one you develop with
  3. Video must be hosted at a public URL for the Graph API to fetch it
     (unlike YouTube/TikTok's direct file upload)

Once you have an approved app, this is where you'd add the two-step
container-then-publish flow (POST /media, then POST /media_publish).
Same OAuth shape as ego/youtube.py otherwise.
"""
