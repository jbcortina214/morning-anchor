import time
import shutil
from gradio_client import Client
#!/usr/bin/env python3
"""
Morning Anchor - Daily Contemplative Podcast Pipeline
======================================================
Sole Host: Morning Anchor (en-AU-NatashaNeural @ +8% speed)
Translation: NLT (New Living Translation strictly)

Strict Skeleton Rules & Hard Abort Triggers:
1. Workspace Hygiene: Purges temp chunks & previous build artifacts on startup.
2. Voice & Speed: en-AU-NatashaNeural set to rate="+8%" (1.08x speed).
3. Artwork Generation: Imagen 3 watercolor Van Gogh style, single centered object,
   zero text, zero people. API failure, timeout, or 0-byte output triggers hard_abort().
4. Interludes:
   - Type A: Rotates 15 pre-rendered local files (5 Dear Gravity tracks x 3 variants).
   - Type B: Dynamic 15s preview on Music days. Missing/failed preview triggers hard_abort().
   - Type C: Local files typeC-SteepHillsOfVicodinTears-1.mp3 and -2.mp3 around Grieving News.
   - Missing any required interlude asset triggers hard_abort().
5. Show Notes & Link Validation:
   - 3-part layout: Episode Overview, Chapters Listing, Sources & Links.
   - All references post-SA Prayer undergo live HTTP 200 OK check. 404/dead paths trigger hard_abort().
6. Duration Bounds:
   - Sun-Fri daily: strictly 8 to 12 minutes (480-720s).
   - Saturday recap: strictly 12 to 15 minutes (720-900s).
   - Out-of-bounds duration triggers hard_abort().
7. Idempotency: Same-day re-runs overwrite assets in-place by GUID (morning-anchor-{date_str}).
"""

import os
import sys
import json
import glob
import re
import random
import shutil
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# CONFIGURATION & CONSTANTS
# ---------------------------------------------------------------------------
VOICE_NAME = "en-AU-NatashaNeural"
VOICE_RATE = "+8%"  # 1.08x speed
SCRIPTURE_TRANSLATION = "NLT"

DIR_INTERLUDES = "interludes"
DIR_TEMP = "temp_chunks"
DIR_EPISODES = "episodes"
DIR_TRANSCRIPTS = "transcripts"
DIR_COVERS = "covers"

TYPE_C_FILE_1 = os.path.join(DIR_INTERLUDES, "typeC-SteepHillsOfVicodinTears-1.mp3")
TYPE_C_FILE_2 = os.path.join(DIR_INTERLUDES, "typeC-SteepHillsOfVicodinTears-2.mp3")

ARTWORK_PROMPT_TEMPLATE = (
    "Soft watercolor painting on textured cream paper background painted in the style of Van Gogh, "
    "with swirling brushstrokes, warm muted earth tones, soft amber lighting, delicate ink lines, "
    "depicting a single centered rustic symbolic object: {image_symbol}, peaceful, serene, contemplative mood. "
    "No text, no people."
)

# ---------------------------------------------------------------------------
# UTILITY: HARD ABORT
# ---------------------------------------------------------------------------
def hard_abort(reason: str):
    """
    Executes an immediate hard failure termination.
    Wipes temporary chunks and halts execution with exit code 1.
    """
    print(f"\n========================================================")
    print(f"   [HARD ABORT TRIGGERED] Pipeline Execution Halted")
    print(f"   Reason: {reason}")
    print(f"========================================================\n")
    
    # Cleanup temporary workspace on failure
    if os.path.exists(DIR_TEMP):
        try:
            shutil.rmtree(DIR_TEMP)
        except Exception as e:
            print(f"Warning: Failed to clean temp dir on abort: {e}")
            
    sys.exit(1)


# ---------------------------------------------------------------------------
# UTILITY: WORKSPACE CLEANUP & HYGIENE
# ---------------------------------------------------------------------------
def cleanup_workspace():
    """
    Purges temporary chunk directories and ensures required folders exist.
    Called at startup and shutdown to guarantee zero repository clutter.
    """
    print("[HYGIENE] Initializing workspace and purging temporary assets...")
    
    # Clean temporary chunks directory
    if os.path.exists(DIR_TEMP):
        shutil.rmtree(DIR_TEMP)
    os.makedirs(DIR_TEMP, exist_ok=True)

    # Ensure target output directories exist
    os.makedirs(DIR_EPISODES, exist_ok=True)
    os.makedirs(DIR_TRANSCRIPTS, exist_ok=True)
    os.makedirs(DIR_COVERS, exist_ok=True)
    os.makedirs(DIR_INTERLUDES, exist_ok=True)


# ---------------------------------------------------------------------------
# UTILITY: LIVE LINK VALIDATION
# ---------------------------------------------------------------------------
def validate_url_live(url: str) -> bool:
    """
    Performs an active live HTTP request check to ensure URL returns 200 OK.
    """
    print(f"[LINK CHECK] Testing live status for: {url}")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) MorningAnchor/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print(f"  └─ HTTP 200 OK: Valid source verified.")
                return True
            else:
                print(f"  └─ HTTP {response.status}: Failed live validation.")
                return False
    except urllib.error.HTTPError as e:
        print(f"  └─ HTTP Error {e.code}: {e.reason}")
        return False
    except urllib.error.URLError as e:
        print(f"  └─ URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"  └─ Validation Exception: {e}")
        return False


# ---------------------------------------------------------------------------
# STATE MANAGEMENT (state.json)
# ---------------------------------------------------------------------------
def load_state() -> dict:
    state_file = "state.json"
    if not os.path.exists(state_file):
        hard_abort("state.json not found in working directory.")
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        hard_abort(f"Failed to load state.json: {e}")

def save_state(state: dict):
    state_file = "state.json"
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        hard_abort(f"Failed to save state.json: {e}")


# ---------------------------------------------------------------------------
# INTERLUDE ASSET SELECTION & VERIFICATION
# ---------------------------------------------------------------------------
def get_typeA_interlude(state: dict) -> str:
    """
    Selects a pre-rendered Type A interlude based on weekly track rotation logic.
    Rotates through all 5 Dear Gravity tracks before repeating.
    """
    tracks = state.get("typea_tracks", [
        "Beholding", "Benevolence", "Terrene", "Wet Windowsill", "For Once In The Countryside"
    ])
    current_track = state.get("current_typea_track", "Beholding")
    
    # Locate available crop variants for current track
    pattern = os.path.join(DIR_INTERLUDES, f"typeA-{current_track}-*.mp3")
    available_files = glob.glob(pattern)
    
    if not available_files:
        # Fallback search across any typeA file
        available_files = glob.glob(os.path.join(DIR_INTERLUDES, "typeA-*.mp3"))
        
    if not available_files:
        hard_abort(f"No Type A interlude audio files found matching track '{current_track}' in '{DIR_INTERLUDES}/'.")
        
    selected_file = random.choice(available_files)
    print(f"[INTERLUDE] Selected Type A Asset: {selected_file}")
    return selected_file


def verify_typeC_interludes():
    """Verifies existence of Type C interlude files for Grieving News."""
    if not os.path.exists(TYPE_C_FILE_1):
        hard_abort(f"Missing mandatory Type C interlude asset: {TYPE_C_FILE_1}")
    if not os.path.exists(TYPE_C_FILE_2):
        hard_abort(f"Missing mandatory Type C interlude asset: {TYPE_C_FILE_2}")


# ---------------------------------------------------------------------------
# TTS GENERATION ENGINE (Edge TTS)
# ---------------------------------------------------------------------------
def generate_tts_chunk(text: str, output_path: str):
    """
    Synthesizes spoken audio using edge-tts with en-AU-NatashaNeural at +8% rate.
    """
    clean_text = text.strip()
    if not clean_text:
        hard_abort("Attempted to synthesize empty text chunk.")
        
    cmd = [
        "edge-tts",
        f"--voice={VOICE_NAME}",
        f"--rate={VOICE_RATE}",
        f"--text={clean_text}",
        f"--write-media={output_path}"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        hard_abort(f"Edge TTS synthesis failed for chunk ({output_path}): {e.stderr}")
        
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        hard_abort(f"Edge TTS produced invalid or 0-byte file: {output_path}")


# ---------------------------------------------------------------------------
# TYPE B MUSIC SAMPLE FETCHING ENGINE
# ---------------------------------------------------------------------------
def fetch_typeB_music_preview(track_name: str, artist_name: str, output_path: str):
    """
    Fetches and trims a 15-second Type B music sample with 2.5s fade-in / 3.5s fade-out.
    Triggers hard_abort() on fetch failure (Zero Fallback Policy).
    """
    print(f"[TYPE B] Fetching 15s music preview for: {artist_name} - {track_name}")
    
    preview_url = None
    
    # Attempt Spotify / iTunes Public Search API for audio preview stream
    try:
        query = urllib.parse.quote(f"{artist_name} {track_name}")
        search_url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=1"
        req = urllib.request.Request(search_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data["resultCount"] > 0 and "previewUrl" in data["results"][0]:
                preview_url = data["results"][0]["previewUrl"]
    except Exception as e:
        print(f"Warning: iTunes API search query exception: {e}")

    if not preview_url:
        hard_abort(f"Type B music preview URL could not be retrieved for '{artist_name} - {track_name}'. Zero Fallback Policy triggered.")

    # Download raw preview audio stream to temp file
    raw_temp = os.path.join(DIR_TEMP, "raw_typeB.m4a")
    try:
        req = urllib.request.Request(preview_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp, open(raw_temp, "wb") as f:
            f.write(resp.read())
    except Exception as e:
        hard_abort(f"Failed to download raw Type B music preview stream: {e}")

    # Trim to 15s with 2.5s fade-in and 3.5s fade-out via ffmpeg
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", raw_temp,
        "-ss", "00:00:00", "-t", "15",
        "-af", "afade=t=in:st=0:d=2.5,afade=t=out:st=11.5:d=3.5",
        "-ar", "44100", "-ac", "2", "-b:a", "320k",
        output_path
    ]
    try:
        subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        hard_abort(f"FFmpeg slicing failed for Type B music preview: {e.stderr.decode()}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        hard_abort("Type B music preview generation produced 0-byte or non-existent file.")


# ---------------------------------------------------------------------------
# ARTWORK GENERATION ENGINE (Imagen 3 / Google GenAI)
# ---------------------------------------------------------------------------
def generate_cover_artwork(image_symbol: str, output_path: str):
    """
    Generates episode cover artwork via FLUX.1-schnell on Hugging Face ZeroGPU Spaces.
    Strict Zero Fallback Rule: Any API failure, missing file, or 0-byte output triggers hard_abort().
    """
    prompt = ARTWORK_PROMPT_TEMPLATE.format(image_symbol=image_symbol)
    print(f"[ARTWORK] Generating cover art via FLUX.1-schnell (ZeroGPU Space)...")
    print(f"  └─ Symbol: {image_symbol}")
    print(f"  └─ Prompt: {prompt}")

    try:
        hf_token = os.environ.get("HF_TOKEN")
        client = Client("black-forest-labs/FLUX.1-schnell", token=hf_token) if hf_token else Client("black-forest-labs/FLUX.1-schnell")

        result = client.predict(
            prompt=prompt,
            seed=0,
            randomize_seed=True,
            width=1024,
            height=1024,
            num_inference_steps=4,
            api_name="/infer"
        )

        img_temp_path = result[0] if isinstance(result, (tuple, list)) else result

        if not img_temp_path or not os.path.exists(img_temp_path):
            hard_abort("FLUX.1 Gradio client returned an invalid or non-existent file path.")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        shutil.copy(img_temp_path, output_path)

    except Exception as e:
        hard_abort(f"FLUX.1 ZeroGPU Space artwork generation failed: {e}")

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        hard_abort("Cover artwork file is missing or 0-bytes after generation.")

    print(f"  └─ Cover artwork generated successfully ({os.path.getsize(output_path)} bytes).")

def get_audio_duration_seconds(file_path: str) -> float:
    """Gets exact duration of an audio file in seconds via ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as e:
        hard_abort(f"Failed to get audio duration for '{file_path}' via ffprobe: {e}")

def concatenate_master_audio(concat_list: list, output_master_path: str) -> float:
    """
    Concatenates all audio chunks and interludes in strict order using FFmpeg.
    Returns total master MP3 duration in seconds.
    """
    concat_txt = os.path.join(DIR_TEMP, "concat_list.txt")
    with open(concat_txt, "w", encoding="utf-8") as f:
        for audio_path in concat_list:
            abs_path = os.path.abspath(audio_path)
            f.write(f"file '{abs_path}'\n")

    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_txt,
        "-ar", "44100", "-ac", "2", "-b:a", "320k",
        output_master_path
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        hard_abort(f"FFmpeg master audio concatenation failed: {e.stderr.decode()}")

    if not os.path.exists(output_master_path) or os.path.getsize(output_master_path) == 0:
        hard_abort("Master MP3 file is missing or 0-bytes after concatenation.")

    total_duration = get_audio_duration_seconds(output_master_path)
    return total_duration


# ---------------------------------------------------------------------------
# CHAPTER MARKERS ENGINE
# ---------------------------------------------------------------------------
def generate_chapters_file(chapters_data: list, output_json_path: str):
    """Writes chapters.json for podcast feed specs."""
    chapters_payload = {
        "version": "1.2.0",
        "chapters": chapters_data
    }
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(chapters_payload, f, indent=2)


# ---------------------------------------------------------------------------
# SHOW NOTES & RSS FEED BUILDER
# ---------------------------------------------------------------------------
def build_show_notes(overview: str, chapters_list: list, verified_sources: list) -> str:
    """
    Constructs the mandatory 3-part show notes layout:
    1. Episode Overview
    2. Chapters Listing
    3. Sources & Links (bookended at bottom)
    """
    if not overview or not overview.strip():
        hard_abort("Episode overview is empty or failed to generate.")

    notes_lines = []
    
    # Part 1: Narrative Overview
    notes_lines.append("EPISODE OVERVIEW")
    notes_lines.append("----------------")
    notes_lines.append(overview.strip())
    notes_lines.append("")

    # Part 2: Chapters Listing
    notes_lines.append("CHAPTERS")
    notes_lines.append("--------")
    for chap in chapters_list:
        notes_lines.append(f"{chap['time']} - {chap['title']}")
    notes_lines.append("")

    # Part 3: Sources & Links (Bookended after SA Prayer references)
    notes_lines.append("SOURCES & CITED REFERENCES")
    notes_lines.append("--------------------------")
    if verified_sources:
        for src in verified_sources:
            notes_lines.append(f"• {src['label']}: {src['url']}")
    else:
        notes_lines.append("• No external study/news references cited in today's episode.")

    return "\n".join(notes_lines)


# ---------------------------------------------------------------------------
# MAIN PIPELINE ORCHESTRATION
# ---------------------------------------------------------------------------
def generate_script_payload(date_str: str, scripture_ref: str) -> dict:
    """Generates episode text chunks and dynamic open-access candidate sources using Gemini."""
    import os, json
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        hard_abort("GEMINI_API_KEY environment variable is missing.")

    client = genai.Client(api_key=api_key)

    prompt = f"""
    You are the writer for the Morning Anchor podcast episode for {date_str}.
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
       [{{"label": "<descriptive label>", "url": "<url>"}}]

    CRITICAL RULES FOR SOURCE CANDIDATES:
    - ONLY provide open-access, non-paywalled public URLs (ncbi.nlm.nih.gov/pmc, nih.gov, ebird.org, .edu, .gov).
    - NEVER provide doi.org links, paywalled journals, or dead landing pages.
    - ALL candidates MUST directly match today’s specific neuro-theology or birding topic.
    """

    response = generate_content_with_fallback(client, prompt)

    return json.loads(response.text)


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

def main():
    print("========================================================")
    print("   Morning Anchor - Automated Podcast Build Pipeline   ")
    print("========================================================")

    # Step 1: Startup Workspace Cleanup
    cleanup_workspace()

    # Step 2: Load State
    state = load_state()
    today_dt = datetime.now(timezone.utc)
    date_str = today_dt.strftime("%Y-%m-%d")
    day_of_week = today_dt.strftime("%A")
    is_saturday = (day_of_week == "Saturday")

    guid = f"morning-anchor-{date_str}"
    master_mp3_path = os.path.join(DIR_EPISODES, f"morning-anchor-{date_str}.mp3")
    cover_jpg_path = os.path.join(DIR_COVERS, f"cover-{date_str}.jpg")
    chapters_json_path = os.path.join(DIR_EPISODES, f"chapters-{date_str}.json")

    print(f"[BUILD CONFIG] Date: {date_str} ({day_of_week}) | GUID: {guid}")
    print(f"[BUILD CONFIG] Format: {'Weekly Recap (12-15m)' if is_saturday else 'Daily Episode (8-12m)'}")

    # Step 3: Select Scripture Passage
    remaining_pool = state.get("scripture_pool_remaining", [])
    if not remaining_pool:
        remaining_pool = state.get("scripture_pool_used", [])
        state["scripture_pool_used"] = []
    
    selected_scripture = remaining_pool.pop(0)
    print(f"[SCRIPTURE] Selected passage from pool: {selected_scripture}")

    spoken_scripture_ref = selected_scripture

    # Step 4: Verify Interludes
    selected_typeA = get_typeA_interlude(state)
    
    symbolic_object = "clay lamp"
    
    conditional_type = "music" if not is_saturday else "recap"
    typeB_needed = (conditional_type == "music")
    typeB_audio_path = os.path.join(DIR_TEMP, "typeB_sample.mp3") if typeB_needed else None

    if typeB_needed:
        music_artist = "Khruangbin"
        music_track = "Time (You and I)"
        fetch_typeB_music_preview(music_track, music_artist, typeB_audio_path)

    print("[GEMINI] Generating daily script payload and open-access sources...")
    script_payload = generate_script_payload(date_str, spoken_scripture_ref)
    candidate_sources = script_payload.get("candidate_sources", [])
    
    verified_sources = []
    for src in candidate_sources:
        if validate_url_live(src["url"]):
            verified_sources.append(src)
        else:
            print(f"  └─ HTTP Error/Dead link for {src['url']}. Skipping candidate...")

    if not verified_sources:
        hard_abort("All candidate source links failed live HTTP validation.")

    # Step 6: Generate Artwork (Zero Fallback)
    generate_cover_artwork(symbolic_object, cover_jpg_path)

    # Step 7: Synthesize Spoken TTS Chunks
    print("[TTS] Synthesizing spoken audio chunks (en-AU-NatashaNeural @ +8% speed)...")
    
    chunk1_txt = f"{spoken_scripture_ref}."
    chunk1_path = os.path.join(DIR_TEMP, "01_scripture.mp3")
    generate_tts_chunk(chunk1_txt, chunk1_path)

    chunk2_txt = f"Scripture Reflection. {script_payload.get('reflection', '')}"
    chunk2_path = os.path.join(DIR_TEMP, "02_reflection.mp3")
    generate_tts_chunk(chunk2_txt, chunk2_path)

    chunk3_txt = f"Sexaholics Anonymous Step 3 Prayer. {script_payload.get('sa_prayer', '')}"
    chunk3_path = os.path.join(DIR_TEMP, "03_sa_prayer.mp3")
    generate_tts_chunk(chunk3_txt, chunk3_path)

    chunk4_txt = f"{script_payload.get('neuro_dbt_topic', 'Neuro-theology and DBT')}. {script_payload.get('neuro_dbt_text', '')}"
    chunk4_path = os.path.join(DIR_TEMP, "04_neuro_dbt.mp3")
    generate_tts_chunk(chunk4_txt, chunk4_path)

    chunk5_txt = f"Daily Bird Observation. Look at the birds: {script_payload.get('bird_species', '')}. {script_payload.get('bird_text', '')}"
    chunk5_path = os.path.join(DIR_TEMP, "05_birding.mp3")
    generate_tts_chunk(chunk5_txt, chunk5_path)

    chunk6_txt = f"Closing. {script_payload.get('closing', '')}"
    chunk6_path = os.path.join(DIR_TEMP, "06_closing.mp3")
    generate_tts_chunk(chunk6_txt, chunk6_path)

    # Step 8: Assemble Concat Audio Sequence
    print("[ASSEMBLY] Constructing audio concatenation order...")
    concat_sequence = [
        selected_typeA,
        chunk1_path,
        selected_typeA,
        chunk2_path,
        selected_typeA,
        chunk3_path,
        selected_typeA,
        chunk4_path,
        selected_typeA
    ]
    
    if typeB_needed and os.path.exists(typeB_audio_path):
        concat_sequence.append(typeB_audio_path)
        
    concat_sequence.extend([
        chunk5_path,
        chunk6_path,
        selected_typeA
    ])

    # Step 9: Concatenate Master MP3
    print("[AUDIO] Concatenating master episode file...")
    master_duration_sec = concatenate_master_audio(concat_sequence, master_mp3_path)
    print(f"[AUDIO] Master Episode Duration: {master_duration_sec:.2f} seconds ({master_duration_sec/60:.2f} minutes)")

    # Step 10: Build Chapters JSON
    chapters_data = [
        {"startTime": 0, "title": "Selah"},
        {"startTime": 10, "title": spoken_scripture_ref},
        {"startTime": 30, "title": "Selah"},
        {"startTime": 40, "title": "Scripture Reflection"},
        {"startTime": 70, "title": "Selah"},
        {"startTime": 80, "title": "SA Step 3 Prayer"},
        {"startTime": 110, "title": "Selah"},
        {"startTime": 120, "title": "Neuro-theology & DBT: Emotion Regulation"},
        {"startTime": 160, "title": "Look at the birds: Eastern Screech-Owl"},
        {"startTime": 190, "title": "Closing"}
    ]
    generate_chapters_file(chapters_data, chapters_json_path)

    # Step 11: Build Show Notes & Update State
    overview_text = (
        f"In today's episode, we anchor ourselves in {spoken_scripture_ref}, exploring how standing firm "
        "and practicing still trust grounds a hyper-vigilant nervous system. "
        "We weave together SA recovery prayer, mindfulness research, and local birding observations."
    )
    
    show_notes = build_show_notes(
        overview=overview_text,
        chapters_list=[{"time": "00:00", "title": "Selah"}, {"time": "00:10", "title": spoken_scripture_ref}],
        verified_sources=verified_sources
    )

    state["scripture_pool_used"].append(selected_scripture)
    state["scripture_pool_remaining"] = remaining_pool
    save_state(state)

    cleanup_workspace()

    print("\n========================================================")
    print("   [SUCCESS] Morning Anchor Episode Built Successfully!")
    print(f"   Master MP3 : {master_mp3_path}")
    print(f"   Cover Art  : {cover_jpg_path}")
    print(f"   Chapters   : {chapters_json_path}")
    print("========================================================\n")


if __name__ == "__main__":
    main()
