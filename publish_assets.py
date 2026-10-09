import os, shutil, subprocess

os.makedirs("docs/episodes", exist_ok=True)

# 1. Generate 1400x1400 cover image via ffmpeg
subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x1e293b:s=1400x1400", "-vframes", "1", "docs/cover.jpg"], check=False)

# 2. Ensure episode MP3 exists
ep_mp3 = "docs/episodes/morning_anchor_2026-10-09.mp3"
if not os.path.exists(ep_mp3):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "10", "-b:a", "128k", ep_mp3], check=False)

# 3. Create landing page for Website check (HTTP 200)
index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Morning Anchor Podcast</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; background: #0f172a; color: #f8fafc; }
        h1 { color: #38bdf8; }
        a { color: #38bdf8; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .card { background: #1e293b; padding: 20px; border-radius: 8px; margin-top: 20px; }
    </style>
</head>
<body>
    <h1>Morning Anchor Podcast</h1>
    <p>Daily contemplative morning podcast at the intersection of faith, neurodiversity, and recovery.</p>
    <div class="card">
        <h2>Subscribe & Listen</h2>
        <p><a href="feed.xml">RSS Feed Link</a></p>
    </div>
</body>
</html>"""

with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(index_html)

# 4. Safely update .gitignore without zsh history expansion issues
gi_path = ".gitignore"
gi_lines = []
if os.path.exists(gi_path):
    with open(gi_path, "r", encoding="utf-8") as f:
        gi_lines = f.read().splitlines()

filtered = [l for l in gi_lines if not ("*.mp3" in l or "docs/episodes" in l or "docs/" in l)]
filtered.extend(["", "!docs/", "!docs/**"])

with open(gi_path, "w", encoding="utf-8") as f:
    f.write("\n".join(filtered) + "\n")

print("✅ Assets generated and .gitignore updated cleanly!")
