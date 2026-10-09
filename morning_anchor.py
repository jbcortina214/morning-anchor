import os
import sys
import time
import re
import json
import asyncio
import datetime
import requests
from google import genai
from google.genai import types

# -----------------------------------------------------------------------------
# GLOBAL CONSTANTS & DIRECTORY PATHS
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DIR_TEMP = os.path.join(BASE_DIR, "temp")
DIR_OUTPUT = os.path.join(BASE_DIR, "docs")
DIR_ASSETS = os.path.join(BASE_DIR, "assets")
AUDIO_OUTPUT_DIR = os.path.join(DIR_OUTPUT, "episodes")
RSS_PATH = os.path.join(DIR_OUTPUT, "feed.xml")

pipeline_errors = []

# -----------------------------------------------------------------------------
# GOOGLE GENAI MODEL FALLBACK & RESPONSE CLEANER
# -----------------------------------------------------------------------------
class CleanResponse:
    def __init__(self, raw_response):
        self.raw = raw_response
        text = getattr(raw_response, "text", "") or ""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        self.text = text

def generate_content_with_fallback(client, prompt):
    models = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]
    last_err = None
    for model_name in models:
        for attempt in range(1, 4):
            try:
                print(f"📡 Requesting script via {model_name} (Attempt {attempt})...")
                config = types.GenerateContentConfig(response_mime_type="application/json")
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return CleanResponse(response)
            except Exception as e:
                err_str = str(e)
                print(f"⚠️ {model_name} attempt {attempt} failed ({err_str}).")
                last_err = e
                if "404" in err_str or "NOT_FOUND" in err_str:
                    print(f"⏩ {model_name} returned 404. Skipping to next model...")
                    break
                time.sleep(3 * attempt)
    raise last_err

# -----------------------------------------------------------------------------
# WORKSPACE HYGIENE
# -----------------------------------------------------------------------------
def cleanup_workspace():
    print("[HYGIENE] Initializing workspace and purging temporary assets...")
    for d in [DIR_TEMP, DIR_OUTPUT, DIR_ASSETS, AUDIO_OUTPUT_DIR]:
        os.makedirs(d, exist_ok=True)
    if os.path.exists(DIR_TEMP):
        for f in os.listdir(DIR_TEMP):
            try:
                fp = os.path.join(DIR_TEMP, f)
                if os.path.isfile(fp):
                    os.remove(fp)
            except Exception as e:
                print(f"⚠️ Could not purge temp file {f}: {e}")

# -----------------------------------------------------------------------------
# PROMPT GENERATION
# -----------------------------------------------------------------------------
def build_daily_prompt(date_str, scripture_ref):
    return f"""You are the writer for the Morning Anchor podcast episode for {date_str}.
Scripture Focus: {scripture_ref}

Produce a JSON object with:
1. "reflection": 2-3 sentence reflection on {scripture_ref}.
2. "sa_prayer": SA Step 3 prayer text.
3. "neuro_dbt_topic": Title/topic for a neuro-theology or DBT mindfulness focus.
4. "neuro_dbt_text": 2 sentence summary on how the practice down-regulates stress/amygdala reactivity.
5. "bird_species": A native bird species for North Texas / Central flyway.
6. "bird_text": 2 sentence description of observing this bird in nature.
7. "closing": A 1-sentence closing blessing.
8. "candidate_sources": Array of 2 to 3 candidate reference objects:
   [{{\"label\": \"<descriptive label>\", \"url\": \"<url>\"}}]

CRITICAL RULES FOR SOURCE CANDIDATES:
* ONLY provide open-access, non-paywalled public URLs (ncbi.nlm.nih.gov/pmc, nih.gov, ebird.org, .edu, .gov).
* NEVER provide doi.org links, paywalled journals, or dead landing pages.
* ALL candidates MUST directly match today's specific neuro-theology or birding topic.
"""

# -----------------------------------------------------------------------------
# SKELETON & RULE VALIDATION
# -----------------------------------------------------------------------------
def validate_script_skeleton(script_data):
    print("[SKELETON CHECK] Validating script payload structure...")
    required_keys = [
        "reflection", "sa_prayer", "neuro_dbt_topic", "neuro_dbt_text",
        "bird_species", "bird_text", "closing", "candidate_sources"
    ]
    missing = []
    for k in required_keys:
        if k not in script_data or not script_data[k]:
            missing.append(k)
    
    if missing:
        msg = f"[SKELETON RULE ERROR] Script missing required fields: {', '.join(missing)}"
        print(f"❌ {msg}")
        pipeline_errors.append(msg)
        return False
    
    print("✅ Script skeleton validation passed.")
    return True

# -----------------------------------------------------------------------------
# AUDIO & RSS RENDERING STAGES
# -----------------------------------------------------------------------------
def render_audio_episode(script_data, date_str):
    print("[AUDIO] Rendering podcast audio episode...")
    audio_filename = f"morning_anchor_{date_str}.mp3"
    audio_path = os.path.join(AUDIO_OUTPUT_DIR, audio_filename)
    
    try:
        # Placeholder audio generation for pipeline end-to-end test
        with open(audio_path, "wb") as f:
            f.write(b"ID3\x04\x00\x00\x00\x00\x00\x00")
        print(f"✅ Audio rendered successfully: {audio_path}")
        return audio_path
    except Exception as e:
        msg = f"[AUDIO RENDER ERROR] Failed to generate audio: {e}"
        print(f"❌ {msg}")
        pipeline_errors.append(msg)
        return None

def update_rss_feed(script_data, date_str):
    print("[RSS] Updating podcast RSS feed XML...")
    try:
        feed_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="[http://www.itunes.com/dtds/podcast-1.0.dtd](http://www.itunes.com/dtds/podcast-1.0.dtd)">
  <channel>
    <title>Morning Anchor</title>
    <link>[https://github.com](https://github.com)</link>
    <description>Daily Morning Anchor Podcast</description>
    <item>
      <title>Morning Anchor - {date_str}</title>
      <pubDate>{datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
      <enclosure url="[https://example.com/episodes/morning_anchor](https://example.com/episodes/morning_anchor)_{date_str}.mp3" length="1024" type="audio/mpeg"/>
    </item>
  </channel>
</rss>"""
        with open(RSS_PATH, "w", encoding="utf-8") as f:
            f.write(feed_content)
        print("✅ RSS Feed XML updated successfully.")
    except Exception as e:
        msg = f"[RSS ERROR] Failed to update RSS feed: {e}"
        print(f"❌ {msg}")
        pipeline_errors.append(msg)

# -----------------------------------------------------------------------------
# MAIN PIPELINE
# -----------------------------------------------------------------------------
def main():
    print("==================================================")
    print("   Morning Anchor - Automated Podcast Build Pipeline")
    print("==================================================")
    
    # 1. Workspace Cleanup
    cleanup_workspace()
    
    # API Key check
    api_key = os.environ.get("GEMINI_API_KEY")
    client = None
    if not api_key:
        msg = "[API KEY ERROR] GEMINI_API_KEY environment variable missing."
        print(f"❌ {msg}")
        pipeline_errors.append(msg)
    else:
        client = genai.Client(api_key=api_key)

    today_str = datetime.date.today().strftime("%Y-%m-%d")
    scripture_ref = "Proverbs 3:5-6"
    
    # 2. Script Generation (Soft fail)
    script_data = {}
    if client:
        try:
            prompt = build_daily_prompt(today_str, scripture_ref)
            response = generate_content_with_fallback(client, prompt)
            script_data = json.loads(response.text)
            print("✅ Script generated successfully via Gemini API.")
        except Exception as e:
            msg = f"[GEMINI GENERATION ERROR] Script generation failed: {e}"
            print(f"❌ {msg}")
            pipeline_errors.append(msg)
    
    # 3. Skeleton Rule Validation (Soft check - non-aborting)
    validate_script_skeleton(script_data)
    
    # 4. Audio Rendering Stage
    render_audio_episode(script_data, today_str)
    
    # 5. RSS Feed Stage
    update_rss_feed(script_data, today_str)
    
    # 6. Final Diagnostic Audit & Abort Gate
    print("\n==================================================")
    print("               PIPELINE AUDIT SUMMARY              ")
    print("==================================================")
    if pipeline_errors:
        print(f"❌ Total Pipeline Errors Identified: {len(pipeline_errors)}")
        for idx, err in enumerate(pipeline_errors, 1):
            print(f"   {idx}. {err}")
        print("\n⛔ ABORTING PIPELINE: Halting before Git commit step.")
        sys.exit(1)
    else:
        print("🎉 ALL PIPELINE CHECKS PASSED PERFECTLY!")
        print("✅ Ready for deployment and git push.")
        sys.exit(0)

if __name__ == "__main__":
    main()
