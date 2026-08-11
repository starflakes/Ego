"""
TikTok posting is intentionally not implemented here.

TikTok's Content Posting API requires:
  1. Registering an app at developers.tiktok.com
  2. Submitting for Content Posting API review (typically 2-6 weeks),
     including a demo video and a live privacy policy URL
  3. Public posting stays restricted to private/self-only until approved

Once you have an approved app + client key/secret, this is where you'd add
an OAuth flow (same shape as ego/youtube.py) and a chunked upload call to
TikTok's /v2/post/publish/video/init/ endpoint. Not worth stubbing out API
calls against endpoints you can't reach yet — start the app review first,
then come back and fill this in.
"""
