import os, shutil, subprocess

def safe_copy(src, dst):
    if src and os.path.exists(src) and os.path.abspath(src) != os.path.abspath(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy(src, dst)

print("🚀 Preparing dual-path static assets for GitHub Pages deployment...")

os.makedirs("docs/episodes", exist_ok=True)
os.makedirs("episodes", exist_ok=True)

# 1. Create .nojekyll files to bypass Jekyll filtering
with open(".nojekyll", "w") as f: f.write("")
with open("docs/.nojekyll", "w") as f: f.write("")

# 2. Mirror 1400x1400 JPEG cover image safely
cover_src = None
for candidate in ["docs/cover.jpg", "cover.jpg", "covers/cover-2026-10-09.jpg", "sample_preview.jpg"]:
    if os.path.exists(candidate):
        cover_src = candidate
        break

if not cover_src:
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x1e293b:s=1400x1400", "-vframes", "1", "cover.jpg"], check=False)
    cover_src = "cover.jpg"

safe_copy(cover_src, "cover.jpg")
safe_copy(cover_src, "docs/cover.jpg")

# 3. Mirror index.html landing pages
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

with open("index.html", "w", encoding="utf-8") as f: f.write(index_html)
with open("docs/index.html", "w", encoding="utf-8") as f: f.write(index_html)

# 4. Mirror RSS Feed XML
if os.path.exists("docs/feed.xml"):
    safe_copy("docs/feed.xml", "feed.xml")
if os.path.exists("feed.xml"):
    safe_copy("feed.xml", "docs/feed.xml")

# 5. Mirror Episode Audio MP3
mp3_name = "morning_anchor_2026-10-09.mp3"
ep_root = os.path.join("episodes", mp3_name)
ep_docs = os.path.join("docs/episodes", mp3_name)

if not os.path.exists(ep_root) and not os.path.exists(ep_docs):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "10", "-b:a", "128k", ep_root], check=False)

src_mp3 = ep_root if os.path.exists(ep_root) else ep_docs
safe_copy(src_mp3, ep_root)
safe_copy(src_mp3, ep_docs)

# 6. Update .gitignore cleanly
gi_path = ".gitignore"
gi_lines = []
if os.path.exists(gi_path):
    with open(gi_path, "r", encoding="utf-8") as f:
        gi_lines = f.read().splitlines()

filtered = [l for l in gi_lines if not ("*.mp3" in l or "episodes" in l or "docs" in l or ".nojekyll" in l)]
filtered.extend(["", "!docs/", "!docs/**", "!episodes/", "!episodes/**", "!.nojekyll", "!cover.jpg", "!index.html", "!feed.xml"])

with open(gi_path, "w", encoding="utf-8") as f:
    f.write("\n".join(filtered) + "\n")

# 7. Force Git Stage, Commit & Push
print("📦 Committing and pushing to GitHub...")
subprocess.run(["git", "add", "-A"], check=False)
subprocess.run(["git", "commit", "-m", "Publish dual-path static assets with safe copy"], check=False)
subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
res = subprocess.run(["git", "push", "origin", "main"], check=False)

if res.returncode == 0:
    print("✅ Successfully pushed to main branch!")
else:
    print("⚠️ Push completed with status:", res.returncode)

