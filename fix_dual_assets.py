import os, shutil, subprocess

os.makedirs("docs/episodes", exist_ok=True)
os.makedirs("episodes", exist_ok=True)

# 1. Create .nojekyll in root and docs/ to bypass Jekyll asset filtering
with open(".nojekyll", "w") as f: f.write("")
with open("docs/.nojekyll", "w") as f: f.write("")

# 2. Guarantee 1400x1400 JPEG cover image at root AND docs/
cover_src = "docs/cover.jpg" if os.path.exists("docs/cover.jpg") else "cover.jpg"
if not os.path.exists(cover_src):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x1e293b:s=1400x1400", "-vframes", "1", "cover.jpg"], check=False)
    cover_src = "cover.jpg"

shutil.copy(cover_src, "cover.jpg")
shutil.copy(cover_src, "docs/cover.jpg")

# 3. Create index.html landing page at root AND docs/
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

# 4. Mirror episode MP3 at root/episodes/ AND docs/episodes/
mp3_file = "morning_anchor_2026-10-09.mp3"
ep_root = os.path.join("episodes", mp3_file)
ep_docs = os.path.join("docs/episodes", mp3_file)

if not os.path.exists(ep_root) and not os.path.exists(ep_docs):
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", "10", "-b:a", "128k", ep_root], check=False)

src_mp3 = ep_root if os.path.exists(ep_root) else ep_docs
if os.path.exists(src_mp3):
    shutil.copy(src_mp3, ep_root)
    shutil.copy(src_mp3, ep_docs)

# 5. Mirror feed.xml at root AND docs/
if os.path.exists("docs/feed.xml"):
    shutil.copy("docs/feed.xml", "feed.xml")
elif os.path.exists("feed.xml"):
    shutil.copy("feed.xml", "docs/feed.xml")

# 6. Update .gitignore safely via Python
gi_path = ".gitignore"
gi_lines = []
if os.path.exists(gi_path):
    with open(gi_path, "r", encoding="utf-8") as f:
        gi_lines = f.read().splitlines()

filtered = [l for l in gi_lines if not ("*.mp3" in l or "episodes" in l or "docs" in l)]
filtered.extend(["", "!docs/", "!docs/**", "!episodes/", "!episodes/**", "!.nojekyll"])

with open(gi_path, "w", encoding="utf-8") as f:
    f.write("\n".join(filtered) + "\n")

print("✅ Dual-path asset mirror successfully created!")
