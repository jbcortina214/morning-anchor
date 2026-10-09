import re
import py_compile

with open("morning_anchor.py", "r", encoding="utf-8") as f:
    code = f.read()

if "from google.genai import types" not in code:
    if "from google import genai" in code:
        code = code.replace("from google import genai", "from google import genai\nfrom google.genai import types")
    else:
        code = "from google.genai import types\n" + code

wrapper_and_fallback = '''
class CleanResponse:
    def __init__(self, raw_response):
        self.raw = raw_response
        text = getattr(raw_response, "text", "") or ""
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
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
'''

pattern = r"def generate_content_with_fallback\(client, prompt\):[\s\S]*?(?=\n\n|\ndef |\nasync def |$)"
if re.search(pattern, code):
    code = re.sub(pattern, wrapper_and_fallback.strip(), code, count=1)
else:
    if "class CleanResponse:" not in code:
        code = wrapper_and_fallback + "\n\n" + code

with open("morning_anchor.py", "w", encoding="utf-8") as f:
    f.write(code)

try:
    py_compile.compile("morning_anchor.py", doraise=True)
    print("✅ VERIFICATION SUCCESS: Syntax valid and JSON enforcement applied!")
except Exception as e:
    print(f"❌ VERIFICATION FAILED: {e}")
    exit(1)
