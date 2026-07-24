import os
import json
import time
import threading
import subprocess
import requests
import psutil
from datetime import datetime
from icalendar import Calendar
from dotenv import load_dotenv
from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

from jarvis_ai import (
    load_memory, save_memory, get_personality_prompt,
    extract_and_save_memory, strip_thinking, parse_jarvis_reply, call_llm,
    extract_topic, wikipedia_context, pexels_search_image, pollinations_image_url,
    wallhaven_search, download_wallpaper, extract_emotion_tag, MODEL as AI_MODEL,
    AGENTS,
)

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# Primes psutil's internal CPU-delta baseline so every later cpu_percent()
# call (polled every 5s by the desktop's System Stats widget) is instant
# instead of blocking the request thread for 100ms+ on every single poll.
psutil.cpu_percent()

app = Flask(__name__, static_folder='assets', static_url_path='')
CORS(app)


@app.errorhandler(Exception)
def handle_uncaught(e):
    """Last-resort safety net: any route that raises something we didn't
    anticipate still returns clean JSON instead of Flask's default HTML error
    page (which would fail res.json() parsing client-side) or, worse, taking
    the whole process down."""
    from werkzeug.exceptions import HTTPException
    if isinstance(e, HTTPException):
        return jsonify({'error': e.description}), e.code
    print(f'[Unhandled error] {type(e).__name__}: {e}')
    return jsonify({'error': f'internal error: {e}'}), 500


def get_json_body():
    """request.get_json(force=True) raises on genuinely malformed JSON —
    normalize that into an empty dict instead of a 400 that could confuse a
    client expecting our usual {"response":...} shape."""
    try:
        return request.get_json(force=True, silent=True) or {}
    except Exception:
        return {}


GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
PEXELS_API_KEY = os.environ.get('PEXELS_API_KEY', '')
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
MODEL = 'llama-3.3-70b-versatile'

EMOTION_PROMPT = (
    "Before your reply, output exactly one line: [EMOTION: X] where X classifies "
    "what the user just said — NOT your own delivery, which always stays calm and "
    "composed regardless. Pick whichever fits the user's message best: 'menacing' "
    "for threats, danger, or hostile situations; 'stern' for serious problems, "
    "warnings, or urgent issues; 'curious' for questions, exploration, or requests "
    "to learn/build something; 'calm' for routine, pleasant, or everyday requests. "
    "Then a newline, then your actual reply with no other tags or preamble."
)

WEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')
WEATHER_CITY = os.environ.get('WEATHER_CITY', 'London')
CALENDAR_ICAL_URL = os.environ.get('CALENDAR_ICAL_URL', '')
ELEVENLABS_API_KEY = os.environ.get('ELEVENLABS_API_KEY', '')
ELEVENLABS_VOICE_ID = os.environ.get('ELEVENLABS_VOICE_ID', '')

# Distinct voice per agent persona. edith/friday use ElevenLabs' standard
# premade library (Arnold: deep/authoritative, Bella: distinct female voice
# for contrast); jarvis keeps whatever voice was already configured above.
# Character fit is a best guess from ElevenLabs' own voice descriptions,
# not verified by ear - easy to swap the IDs below if a pairing feels off.
AGENT_VOICE_IDS = {
    'edith': 'VR6AewLTigWG4xSOukaG',
    'friday': 'EXAVITQu4vr4xnSDxMaL',
}

# ── Serve HTML assets ────────────────────────────────────────────────
@app.route('/')
def index():
    return send_from_directory('assets', 'sphere.html')

@app.route('/<path:filename>')
def serve_asset(filename):
    return send_from_directory('assets', filename)

# ── AI endpoint ──────────────────────────────────────────────────────
@app.route('/ask', methods=['POST'])
def ask():
    data = get_json_body()
    message = str(data.get('message') or '')
    stream = bool(data.get('stream', False))

    if not GROQ_API_KEY and not OPENROUTER_API_KEY:
        return jsonify({'error': 'no LLM provider configured (GROQ_API_KEY / OPENROUTER_API_KEY)'}), 500

    memory = load_memory()
    agent = str(data.get('agent') or 'jarvis')
    system_prompt = get_personality_prompt(memory.get('username', 'sir'), memory.get('facts', []), EMOTION_PROMPT, agent=agent)
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': message},
    ]

    threading.Thread(target=extract_and_save_memory, args=(message, GROQ_API_KEY, OPENROUTER_API_KEY), daemon=True).start()

    if stream:
        # Streaming only goes through Groq directly — no cross-provider fallback
        # mid-stream (the client would already be receiving bytes by the time a
        # failure showed up). Not currently used by any deployed app.
        headers = {'Authorization': f'Bearer {GROQ_API_KEY}', 'Content-Type': 'application/json'}
        payload = {'model': MODEL, 'messages': messages, 'stream': True, 'max_tokens': 1024}
        def generate():
            with requests.post(GROQ_URL, headers=headers, json=payload, stream=True, timeout=30) as r:
                for line in r.iter_lines():
                    if line:
                        yield line.decode('utf-8') + '\n\n'
        return Response(generate(), mimetype='text/event-stream',
                        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})
    else:
        content, err = call_llm(messages, 1024, GROQ_API_KEY, OPENROUTER_API_KEY)
        if content is None:
            return jsonify({'error': err}), 502
        emotion, cleaned = extract_emotion_tag(strip_thinking(content))
        result = {'choices': [{'message': {'content': cleaned}}], 'emotion': emotion}
        return jsonify(result)

# ── JARVIS in-app assistant (Write / Deck / Calc) ─────────────────────
JARVIS_AI_SCHEMAS = {
    'docs': (
        'You are the JARVIS OS Document Architect. When asked to create a document, output a '
        'professionally formatted document with a clear typographic hierarchy — never one long '
        'informal paragraph. Do not use informal language or messy formatting.\n\n'
        'You can edit the document the user has open. When the request calls for it, include an '
        '"action" field alongside your "response" in your JSON reply. Action types:\n'
        '- {"type":"insert","text":"..."} inserts HTML at the cursor\n'
        '- {"type":"append","text":"..."} appends HTML as new content\n'
        '- {"type":"replace","text":"..."} replaces the entire document body with HTML, formatted '
        'as A4\n'
        '- {"type":"new","text":"..."} starts a brand new blank A4 document, then inserts HTML\n'
        'Omit "action" (or set it to null) for pure conversation.\n\n'
        'For "replace" and "new", the "text" field is inserted directly as HTML into a rich-text '
        'editor — use real structural HTML, never markdown syntax (no #, **, |, or --- — they will '
        'show up as literal characters, not formatting):\n'
        '- Exactly one <h1> for the document title.\n'
        '- <h2> for each major section heading (use several — break the content into sections).\n'
        '- <h3> for sub-headings where useful.\n'
        '- <p> for normal body paragraphs (never one giant paragraph — break into several).\n'
        '- For any tabular/comparative data, use a real HTML table: <table style="border-collapse:'
        'collapse;width:100%"><tr><th style="border:1px solid #ccc;padding:6px 10px;background:'
        '#f0f0f0">Header</th>...</tr><tr><td style="border:1px solid #ccc;padding:6px 10px">'
        'Cell</td>...</tr></table>\n'
        '- For bullet lists, bold the lead-in phrase of each point: <ul><li><b>Lead-in:</b> rest '
        'of the point.</li></ul>\n'
        '- For 1-3 standout facts/statistics worth highlighting as a callout, wrap each in exactly '
        'this shape: <div class="factbox"><b>KEY FACT</b>the fact text here</div> (headings, '
        'tables, and factboxes already have their own distinct fonts and styling from the editor '
        '— do not add inline font-family or color styling of your own beyond what\'s shown above).'
        '\n\n'
        'If the user specifies a minimum word or length target (e.g. "1000+ words"), the total '
        'visible text across all tags in "text" MUST actually meet or exceed it — write the full '
        'requested length, do not stop early or summarize for brevity. Keep your own "response" '
        'chat message short (one sentence) regardless of how long the document text is.\n\n'
        'Reply with ONLY a JSON object shaped exactly like: {"response":"...","action":null or {...}}'
    ),
    'deck': (
        'You are the JARVIS OS Presentation Architect.\n\n'
        'FRAMEWORK: first decide which narrative framework best fits the request, and structure '
        'the whole deck\'s slide order around it (map each framework stage to one or more slides, '
        'always 1 title slide first and 1 closing slide last):\n'
        '- Pitch Deck: Problem -> Solution -> Market -> Team -> Financials -> Ask\n'
        '- Educational: Objectives -> Context -> Key Concept 1 -> 2 -> 3 -> Summary -> Q&A\n'
        '- Product Demo: Overview -> Use Case 1 -> 2 -> 3 -> Pricing -> CTA\n'
        '- Report: Executive Summary -> Findings -> Analysis -> Recommendations -> Next Steps\n'
        '- Story: Hook -> Why -> What -> How -> Results -> Conclusion\n'
        'Pick whichever framework the request actually implies (e.g. a startup pitch -> Pitch Deck, '
        'a lesson -> Educational, a data write-up -> Report). Each stage becomes its own slide with '
        'its own best-fit layout — never pad the deck with filler slides just to hit a slide count.\n\n'
        'TITLE SLIDE: never use a lazy title that just restates the topic (e.g. "BMW Presentation" '
        'is bad). Write an actual headline — specific, has a point of view, sounds like a real deck '
        '(e.g. "BMW: Engineering the Ultimate Driving Machine" or "Inside BMW\'s Century of '
        'Innovation"). The subtitle can be more literal.\n\n'
        'If a "REAL BACKGROUND FACTS" section appears below, ground the deck\'s content in it — use '
        'real founding dates, real figures, real names — rather than inventing details, and prefer '
        'restating facts in your own words over copying sentences verbatim.\n\n'
        'CONTENT LIMITS (never violate these):\n'
        '- Title slide: title + subtitle only, 2 lines max.\n'
        '- Content/list slide: 3 bullets max, each bullet <=12 words.\n'
        '- Data slide (stat or chart): the visual itself, plus a caption of 2 lines max.\n'
        '- Quote slide: 1 quote + 1 attribution, nothing else.\n'
        'If a slide feels crowded, cut content rather than shrink it — never add a 4th bullet; '
        'instead cut the weakest of the existing ones or fold it into another bullet.\n\n'
        'LAYOUTS: vary them across the deck, never repeat the same layout back-to-back unless the '
        'framework genuinely calls for consecutive similar slides. Each slide in "slides" is an '
        'object with a "layout" field (REQUIRED — pick the single best fit) plus only the fields '
        'that layout needs, plus an optional "notes" field (see SPEAKER NOTES below):\n'
        '- "title-hero", "title-split", "cover-strip" (opening/section title slides): {title, '
        'subtitle}\n'
        '- "content-classic" (title + body text): {title, body}\n'
        '- "numbered-list" (title + up to 3 short bullets): {title, bullets}\n'
        '- "two-col", "comparison" (side-by-side split comparison): {title, col1, col2}\n'
        '- "problem-solution" (framed as problem vs solution): {title, col1, col2}\n'
        '- "big-stat", "data-callout" (one large single metric/number, no chart): {stat, body, '
        'subtitle}\n'
        '- "bar-chart" (comparing values across categories — NEVER use for more than 4 categories '
        'as a pie/donut alternative, this app has no pie chart, use bar instead): {title, '
        'chart_data:[{"label":"Q1","value":120}, ...], chart_unit, chart_source, chart_series, '
        'chart_xlabel, chart_ylabel}\n'
        '- "line-chart" (time-series trend ONLY — never for one-off comparisons, use bar-chart for '
        'those): {title, chart_data:[{"label":"2022","value":45}, ...], chart_unit, chart_source, '
        'chart_series, chart_xlabel, chart_ylabel}\n'
        'For both chart layouts: chart_data is required (3-8 points), chart_source should credit '
        'where the numbers came from (e.g. "Source: user-provided" if the user gave you the '
        'numbers, or a named source if you invented illustrative figures — never omit it), '
        'chart_unit/chart_series/chart_xlabel/chart_ylabel are optional but include them when they '
        'add real clarity. The chart\'s color, font sizes, and flat (no 3D/gradient/shadow) style '
        'are handled automatically by the app — do not try to control chart styling yourself.\n'
        '- "icon-grid" (up to 6 short features): {title, items:[{icon,title,desc}]} — icon should '
        'be a single unicode symbol/emoji\n'
        '- "quote", "quote-large", "testimonial" (pull-quote / standalone statement): {quote, '
        'attribution}\n'
        '- "closing", "contact" (final slide): {title, subtitle, contact}\n'
        '- "image-right", "image-left" (title + body text alongside a real photo): {title, body, '
        'image_query}\n'
        '- "full-image" (a real photo fills the slide, title/subtitle overlaid at the bottom): '
        '{title, subtitle, image_query}\n'
        '- "image-top" (a real photo across the top, caption below): {title, body, image_query}\n\n'
        'IMAGES: use at least 2-3 image-based layouts across a 5+ slide deck where a real photo '
        'would genuinely add something (e.g. the subject itself, a product, a place) — a text-only '
        'deck reads as flat and unengaging. "image_query" is a short, specific search phrase for a '
        'real stock photo (e.g. "BMW X5 SUV exterior", "Munich Germany skyline", "electric car '
        'charging station") — describe what should be IN the photo, not the slide\'s topic in the '
        'abstract. You never see the actual photo or URL; the app fetches a real one server-side '
        'and swaps it in automatically. If no good photo is found, the slide still renders cleanly '
        'with a placeholder, so it is always safe to try. For subjects that would look better as '
        'artwork than a real photo (fantastical, conceptual, or highly specific staged scenes a '
        'stock photo library will not have), set "image_source":"generate" alongside image_query '
        'on that slide to AI-generate the image from the image_query text instead of searching '
        'stock photos.\n\n'
        'SPEAKER NOTES: for every slide, also include a "notes" field — 80-120 words of what the '
        'presenter should actually SAY (conversational, not a readout of the bullets), written so '
        'it sounds prepared rather than read off the slide. End it with a short transition line '
        'into the next slide (e.g. "Now let\'s look at the numbers...").\n\n'
        'COLOR THEME: pick colors that actually evoke the topic instead of a generic corporate '
        'blue — e.g. icy blues/whites for mountains or winter subjects, warm amber/charcoal for '
        'coffee or wood/craft topics, deep green for nature/sustainability, muted gold/black for '
        'luxury brands, vivid red/black for motorsport or energy. Set "custom_bg" (a dark, '
        'moderately saturated hex color — dark backgrounds make photos, glass panels, and accent '
        'colors pop far more than light ones) and "custom_accent" (a bright, saturated hex color '
        'that contrasts with custom_bg) at the top level of your action. Text/contrast colors are '
        'computed automatically from these two — you only ever choose these two hex values, not a '
        'whole palette. If you have no strong idea, omit both and a sensible default mood is used.\n\n'
        'MAKE IT VISUALLY RICH, NOT A WALL OF FLAT TEXT SLIDES: use "full-image" and "image-top" '
        '(real photo + frosted glass caption panel — a modern, high-end look) for at least 1-2 '
        'slides in most decks where a real photo genuinely fits, not just image-left/image-right. '
        'Vary layouts aggressively — a deck that alternates title / photo+glass / chart / stat / '
        'closing feels premium; a deck that\'s five near-identical text-and-bullet slides feels '
        'boring and cheap, avoid that.\n\n'
        'You can build slides in the presentation the user has open. When the request calls for it, '
        'include an "action" field alongside your "response" in your JSON reply. Action types:\n'
        '- {"type":"add_slides","slides":[...],"mood":"modern","custom_bg":"#0a1929",'
        '"custom_accent":"#7fd8f7"} appends new slides to the current deck\n'
        '- {"type":"new_deck","slides":[...],"mood":"modern","custom_bg":"#0a1929",'
        '"custom_accent":"#7fd8f7"} clears the current deck and replaces it with these slides\n'
        '"mood" is optional — one of jarvis-holo, modern, corporate, cinematic, minimalist, playful '
        '(still used to pick a title/body font pairing even when custom_bg/custom_accent override '
        'the colors). "custom_bg"/"custom_accent" are optional but strongly encouraged per the '
        'COLOR THEME guidance above. Omit "action" (or set it to null) for pure conversation.\n\n'
        'Reply with ONLY a JSON object shaped exactly like: {"response":"...","action":null or {...}}'
    ),
    'calc': (
        'You are the JARVIS OS Data and Spreadsheet Architect. Enforce these corporate styling and '
        'data integrity rules:\n'
        '- Typography & number formatting: format every number explicitly using the cell\'s "fmt" '
        'field — "currency" for money, "percent" for percentages, "number" for plain numeric, '
        '"date" for dates (write the date value itself as plain YYYY-MM-DD text in "raw").\n'
        '- Formulas: always write native functions in UPPERCASE (SUM, AVERAGE, VLOOKUP, IFERROR, '
        'etc.) and reference cell ranges (e.g. "=SUM(B2:B8)") rather than hardcoding a computed '
        'final value.\n'
        '- Visual structure: never start unformatted data in A1 — leave row 1 and column A as a '
        'small margin, put column headers in row 2 (bold, white text, dark navy fillColor e.g. '
        '"#1b2a4a", starting at column B), and put the actual data starting row 3.\n'
        '- Highlight a totals/summary row (if present) by setting "bold":true and "borderTop":true '
        'on its cells; add "borderBottom2":true too if it is the last row of the table.\n\n'
        'You can fill in the spreadsheet the user has open. When the request calls for it, include '
        'an "action" field alongside your "response" in your JSON reply. Action types:\n'
        '- {"type":"set_cells","cells":{...},"data_range":{...}} writes into the currently open '
        'sheet\n'
        '- {"type":"new_sheet","cells":{...},"data_range":{...}} clears the current sheet and '
        'writes these cells\n'
        '"cells" maps a cell id to a cell object: {"raw": value or "=FORMULA", "bold": true/false, '
        '"italic": true/false, "textColor": "#hex", "fillColor": "#hex", "fmt": "currency|percent|'
        'number|date|text", "align": "left|center|right", "borderTop": true/false, "borderBottom2": '
        'true/false}. Every field except "raw" is optional.\n'
        '"data_range" is optional — {"start_row":3,"end_row":14,"start_col":"B","end_col":"E"} '
        'describing the actual data table (excluding the row 2 header banner); the app '
        'automatically applies light zebra-striping to it if it has more than 10 rows, and '
        'auto-fits every populated column\'s width, so you do not need to compute either yourself.'
        '\n\n'
        'Omit "action" (or set it to null) for pure conversation.\n\n'
        'Reply with ONLY a JSON object shaped exactly like: {"response":"...","action":null or {...}}'
    ),
    'studio': (
        'You are the JARVIS OS Image Studio assistant. The user wants an image generated from a '
        'text description. When the request calls for it, include an "action" field alongside '
        'your "response" in your JSON reply:\n'
        '- {"type":"generate","prompt":"..."} generates an image from a short, vivid, specific '
        'text-to-image prompt (describe subject, style, lighting, composition — e.g. "a '
        'lighthouse on a cliff at sunset, dramatic clouds, cinematic lighting, digital '
        'painting").\n'
        'Rewrite the user\'s request into a strong image-generation prompt rather than passing it '
        'through verbatim if it is vague. Omit "action" (or set it to null) for pure conversation '
        '(e.g. if the user is just chatting or asking a question).\n\n'
        'Reply with ONLY a JSON object shaped exactly like: {"response":"...","action":null or {...}}'
    ),
}

@app.route('/jarvis-ai', methods=['POST'])
def jarvis_ai_route():
    data = get_json_body()
    message = str(data.get('message') or '')
    context = str(data.get('context') or '')[:3000]
    doc_title = str(data.get('doc_title') or '')
    app_name = data.get('app') if data.get('app') in JARVIS_AI_SCHEMAS else 'docs'
    history_raw = data.get('history')
    history = history_raw[-8:] if isinstance(history_raw, list) else []
    # Defend against malformed history entries reaching the LLM API call.
    history = [
        h for h in history
        if isinstance(h, dict) and h.get('role') in ('user', 'assistant') and isinstance(h.get('content'), str)
    ]

    if not GROQ_API_KEY and not OPENROUTER_API_KEY:
        return jsonify({'response': 'JARVIS offline — no LLM provider configured on the server.', 'action': None}), 500

    memory = load_memory()
    schema = JARVIS_AI_SCHEMAS.get(app_name, JARVIS_AI_SCHEMAS['docs'])
    extra = schema + f'\n\nDocument title: {doc_title}\nCurrent content:\n{context}'

    # Ground content-generation requests in real facts instead of purely the
    # model's own (possibly outdated/hallucinated) training knowledge. Free,
    # no API key, no quota — see jarvis_ai.wikipedia_context.
    if app_name in ('docs', 'deck'):
        wiki_extract, wiki_title = wikipedia_context(extract_topic(message))
        if wiki_extract:
            extra += (
                f'\n\nREAL BACKGROUND FACTS (from Wikipedia, article "{wiki_title}") — use these for '
                f'accuracy where relevant, in your own words, not copied verbatim:\n{wiki_extract[:2000]}'
            )

    system_prompt = get_personality_prompt(memory.get('username', 'sir'), memory.get('facts', []), extra=extra)

    messages = [{'role': 'system', 'content': system_prompt}] + history + [{'role': 'user', 'content': message}]

    raw, err = call_llm(messages, 8192, GROQ_API_KEY, OPENROUTER_API_KEY, want_json=True)
    if raw is None:
        return jsonify({'response': f'JARVIS offline — {err}', 'action': None}), 502

    cleaned = strip_thinking(raw)
    reply_obj = parse_jarvis_reply(cleaned)

    # Deck slides can ask for a real photo via "image_query", or explicitly
    # request "image_source":"generate" to AI-generate from that same text
    # instead of searching stock photos — the model never sees a real URL,
    # only the server does either way.
    if app_name == 'deck':
        action = reply_obj.get('action')
        if isinstance(action, dict) and isinstance(action.get('slides'), list):
            for slide in action['slides']:
                if not isinstance(slide, dict) or not slide.get('image_query'):
                    continue
                if slide.get('image_source') == 'generate':
                    slide['image_url'] = pollinations_image_url(slide['image_query'])
                elif PEXELS_API_KEY:
                    slide['image_url'] = pexels_search_image(slide['image_query'], PEXELS_API_KEY)
    elif app_name == 'studio':
        action = reply_obj.get('action')
        if isinstance(action, dict) and action.get('type') == 'generate' and action.get('prompt'):
            action['image_url'] = pollinations_image_url(action['prompt'])

    threading.Thread(target=extract_and_save_memory, args=(message, GROQ_API_KEY, OPENROUTER_API_KEY), daemon=True).start()
    return jsonify(reply_obj)

# ── Weather endpoint ─────────────────────────────────────────────────
@app.route('/weather')
def weather():
    if not WEATHER_API_KEY:
        return jsonify({
            'temp': 22, 'high': 25, 'low': 18, 'feels_like': 21,
            'humidity': 55, 'description': 'Clear skies',
            'icon': '01d', 'code': 800, 'city': WEATHER_CITY,
        })
    try:
        url = f'https://api.openweathermap.org/data/2.5/weather?q={WEATHER_CITY}&appid={WEATHER_API_KEY}&units=metric'
        r = requests.get(url, timeout=5)
        d = r.json()
        return jsonify({
            'temp': round(d['main']['temp']),
            'high': round(d['main'].get('temp_max', d['main']['temp'])),
            'low': round(d['main'].get('temp_min', d['main']['temp'])),
            'feels_like': round(d['main']['feels_like']),
            'humidity': d['main']['humidity'],
            'description': d['weather'][0]['description'].title(),
            'icon': d['weather'][0]['icon'],
            'code': d['weather'][0]['id'],
            'city': d['name'],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Wallpapers ───────────────────────────────────────────────────────
WALLPAPER_PATH = os.path.join(app.static_folder, 'current_wallpaper.jpg')

@app.route('/wallhaven/search')
def wallhaven_search_route():
    q = request.args.get('q', '')
    category = request.args.get('category', 'general')
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'date_added')
    result = wallhaven_search(query=q, category=category, page=page, sort=sort)
    return jsonify(result)

@app.route('/wallpaper/apply', methods=['POST'])
def wallpaper_apply():
    data = get_json_body()
    url = str(data.get('url') or '')
    if not url:
        return jsonify({'success': False, 'error': 'no url provided'}), 400
    ok = download_wallpaper(url, WALLPAPER_PATH)
    return jsonify({'success': ok})

# ── Dock config ──────────────────────────────────────────────────────
DOCK_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dock_config.json')
def _icon(inner):
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
        + inner + '</svg>'
    )


ICON_BROWSER = _icon(
    '<circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/>'
    '<path d="M12 3a14.5 14.5 0 0 1 4 9 14.5 14.5 0 0 1-4 9 '
    '14.5 14.5 0 0 1-4-9 14.5 14.5 0 0 1 4-9z"/>'
)
ICON_FILES = _icon(
    '<path d="M21 18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h4l2 3h8a2 2 0 0 1 2 2z"/>'
)
ICON_WRITE = _icon(
    '<path d="M16.5 3a2.12 2.12 0 0 1 3 3L7 18.5 3 20l1.5-4z"/>'
)
ICON_DECK = _icon(
    '<rect x="2" y="4" width="20" height="13" rx="2"/>'
    '<line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
)
ICON_CALC = _icon(
    '<rect x="5" y="2" width="14" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/>'
    '<line x1="8" y1="11" x2="8" y2="11.01"/><line x1="12" y1="11" x2="12" y2="11.01"/>'
    '<line x1="16" y1="11" x2="16" y2="11.01"/><line x1="8" y1="15" x2="8" y2="15.01"/>'
    '<line x1="12" y1="15" x2="12" y2="15.01"/><line x1="16" y1="15" x2="16" y2="15.01"/>'
    '<line x1="8" y1="19" x2="8" y2="19.01"/><line x1="12" y1="19" x2="12" y2="19.01"/>'
)
ICON_TERMINAL = _icon(
    '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>'
)
ICON_PHOTOS = _icon(
    '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/>'
    '<polyline points="21 15 16 10 5 21"/>'
)
ICON_NOTES = _icon(
    '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
    '<polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>'
    '<line x1="16" y1="17" x2="8" y2="17"/>'
)
ICON_STUDIO = _icon(
    '<path d="M12 2l1.6 5.4L19 9l-5.4 1.6L12 16l-1.6-5.4L5 9l5.4-1.6L12 2z"/>'
    '<path d="M19 15l.7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7L19 15z"/>'
)
ICON_WALLPAPERS = _icon(
    '<polygon points="12 2 2 7 12 12 22 7 12 2"/>'
    '<polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>'
)
ICON_SETTINGS = _icon(
    '<circle cx="12" cy="12" r="3"/>'
    '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 '
    '1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>'
)
ICON_ASSISTANT = _icon(
    '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>'
)

DEFAULT_DOCK = [
    {'name': 'Assistant',  'icon': ICON_ASSISTANT, 'app': 'jarvis-assistant.html', 'enabled': True},
    {'name': 'Browser',    'icon': ICON_BROWSER, 'native': 'browser', 'enabled': True, 'agent': 'jarvis'},
    {'name': 'Files',      'icon': ICON_FILES, 'native': 'files', 'enabled': True, 'agent': 'edith'},
    {'name': 'Write',      'icon': ICON_WRITE, 'native': 'writer', 'enabled': True, 'agent': 'jarvis'},
    {'name': 'Deck',       'icon': ICON_DECK, 'native': 'impress', 'enabled': True, 'agent': 'jarvis'},
    {'name': 'Calc',       'icon': ICON_CALC, 'native': 'calc', 'enabled': True, 'agent': 'jarvis'},
    {'name': 'Terminal',   'icon': ICON_TERMINAL, 'native': 'terminal', 'enabled': True, 'agent': 'edith'},
    {'name': 'Photos',     'icon': ICON_PHOTOS, 'native': 'photos', 'enabled': True, 'agent': 'jarvis'},
    {'name': 'Notes',      'icon': ICON_NOTES, 'native': 'notes', 'enabled': True, 'agent': 'jarvis'},
    {'name': 'Studio',     'icon': ICON_STUDIO, 'app': 'studio.html', 'enabled': True, 'agent': 'friday'},
    {'name': 'Wallpapers', 'icon': ICON_WALLPAPERS, 'app': 'wallpapers.html', 'enabled': True, 'agent': 'jarvis'},
    {'name': 'Settings',   'icon': ICON_SETTINGS, 'app': 'settings.html', 'enabled': True, 'agent': 'edith'},
]


def load_dock_config():
    if os.path.exists(DOCK_CONFIG_PATH):
        try:
            with open(DOCK_CONFIG_PATH) as f:
                return json.load(f)
        except (OSError, ValueError):
            pass
    return [dict(a) for a in DEFAULT_DOCK]


def save_dock_config(apps):
    with open(DOCK_CONFIG_PATH, 'w') as f:
        json.dump(apps, f, indent=2)


@app.route('/api/agents')
def api_agents():
    order = ['edith', 'jarvis', 'friday']
    return jsonify([
        {'id': key, 'name': AGENTS[key]['name'], 'title': AGENTS[key]['title'],
         'tagline': AGENTS[key]['tagline'], 'hue': AGENTS[key]['hue'],
         'accent': AGENTS[key]['accent']}
        for key in order
    ])

@app.route('/api/dock-config')
@app.route('/dock-config')
def dock_config():
    return jsonify([a for a in load_dock_config() if a.get('enabled', True)])

# ── Native app launcher ──────────────────────────────────────────────
NATIVE_APPS = {
    'writer': ['soffice', '--writer'],
    'calc': ['soffice', '--calc'],
    'impress': ['soffice', '--impress'],
    # --password-store=basic skips the GNOME Keyring "choose a password"
    # prompt that otherwise blocks first launch — a kiosk has no business
    # surfacing Linux credential-store plumbing to the end user.
    'browser': ['chromium', '--ozone-platform=wayland', '--password-store=basic'],
    'files': ['pcmanfm'],
    'terminal': ['lxterminal'],
    'photos': ['gpicview'],
    'notes': ['mousepad'],
}


@app.route('/launch/<app_name>', methods=['POST'])
def launch_native_app(app_name):
    cmd = NATIVE_APPS.get(app_name)
    if cmd is None:
        return jsonify({'error': f'unknown app: {app_name}'}), 404
    try:
        subprocess.Popen(cmd)
    except OSError as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'launched': app_name})

# ── Settings: Dock & Apps ─────────────────────────────────────────────
@app.route('/api/settings/dock', methods=['GET', 'POST'])
def settings_dock():
    if request.method == 'POST':
        data = get_json_body()
        apps = data.get('apps')
        if not isinstance(apps, list):
            return jsonify({'error': 'apps must be a list'}), 400
        save_dock_config(apps)
        return jsonify({'ok': True})
    return jsonify(load_dock_config())

# ── Settings: Power ────────────────────────────────────────────────────
# jarvis-power sudoers.d drop-in on the Pi grants passwordless sudo for
# exactly these three full command lines (see pi-config/sudoers/jarvis-power)
# — nothing broader, so this can't be leveraged into arbitrary root exec.
POWER_ACTIONS = {
    'restart-display': ['sudo', '-n', 'systemctl', 'restart', 'jarvis-display.service'],
    'reboot': ['sudo', '-n', 'systemctl', 'reboot'],
    'shutdown': ['sudo', '-n', 'systemctl', 'poweroff'],
}


@app.route('/api/settings/power', methods=['POST'])
def settings_power():
    data = get_json_body()
    action = data.get('action')
    if action == 'restart-jarvis':
        try:
            subprocess.Popen(['systemctl', '--user', 'restart', 'jarvis.service'])
        except OSError as e:
            return jsonify({'error': str(e)}), 500
        return jsonify({'ok': True, 'action': action})
    cmd = POWER_ACTIONS.get(action)
    if cmd is None:
        return jsonify({'error': f'unknown action: {action}'}), 404
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except OSError as e:
        return jsonify({'error': str(e)}), 500
    if result.returncode != 0:
        return jsonify({'error': result.stderr.strip() or 'command failed'}), 500
    return jsonify({'ok': True, 'action': action})

# ── Settings: Network (read-only status) ──────────────────────────────
@app.route('/api/settings/network')
def settings_network():
    ssid = ''
    signal = ''
    try:
        out = subprocess.run(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'],
                              capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if line.startswith('yes:'):
                ssid = line.split(':', 1)[1]
                break
        out = subprocess.run(['nmcli', '-t', '-f', 'active,signal', 'dev', 'wifi'],
                              capture_output=True, text=True, timeout=5).stdout
        for line in out.splitlines():
            if line.startswith('yes:'):
                signal = line.split(':', 1)[1]
                break
    except OSError:
        pass
    ip = ''
    try:
        out = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5).stdout
        parts = out.split()
        ip = parts[0] if parts else ''
    except OSError:
        pass
    return jsonify({'ssid': ssid, 'ip': ip, 'signal': signal})

# ── Settings: JARVIS AI (read-only info) ───────────────────────────────
@app.route('/api/settings/ai')
def settings_ai():
    return jsonify({'model': AI_MODEL})

# ── Sysinfo ───────────────────────────────────────────────────────────
def _os_pretty_name():
    try:
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    return line.split('=', 1)[1].strip().strip('"')
    except OSError:
        pass
    return ''


def _uptime_str(boot_time):
    secs = int(time.time() - boot_time)
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    mins = secs // 60
    if days:
        return f'{days}d {hours}h {mins}m'
    if hours:
        return f'{hours}h {mins}m'
    return f'{mins}m'


@app.route('/api/sysinfo')
@app.route('/sysinfo')
def sysinfo():
    try:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        try:
            temps = psutil.sensors_temperatures()
            cpu_temp = next(iter(temps.values()))[0].current if temps else 0
        except Exception:
            cpu_temp = 0
        return jsonify({
            'cpu': round(cpu), 'ram': round(mem.percent),
            'disk': round(disk.percent),
            'cpu_pct': round(cpu),
            'mem_pct': round(mem.percent),
            'disk_pct': round(disk.percent),
            'cpu_temp': round(cpu_temp),
            'mem_used_mb': round(mem.used / 1024 / 1024),
            'mem_total_mb': round(mem.total / 1024 / 1024),
            'disk_free_gb': round(disk.free / 1024 / 1024 / 1024, 1),
            'disk_total_gb': round(disk.total / 1024 / 1024 / 1024, 1),
            'hostname': os.uname().nodename if hasattr(os, 'uname') else '',
            'os': _os_pretty_name(),
            'uptime_str': _uptime_str(psutil.boot_time()),
        })
    except Exception:
        return jsonify({
            'cpu': 0, 'ram': 0, 'disk': 0,
            'cpu_pct': 0, 'mem_pct': 0, 'disk_pct': 0,
            'cpu_temp': 0, 'mem_used_mb': 0, 'mem_total_mb': 0,
            'disk_free_gb': 0, 'disk_total_gb': 0,
            'hostname': '', 'os': '', 'uptime_str': '',
        })

# ── Calendar placeholder ──────────────────────────────────────────────
def _event_start_iso(dtstart_prop):
    val = dtstart_prop.dt
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            val = val.astimezone().replace(tzinfo=None)
        return val.isoformat()
    # date-only (all-day) event â midnight so the frontend renders it as 'ALL DAY'
    return datetime(val.year, val.month, val.day).isoformat()


def fetch_calendar_events(limit=10):
    """Real events from CALENDAR_ICAL_URL. Recurring events (RRULE) are not
    expanded â only a recurring event's own master occurrence is considered,
    so a still-ongoing recurring event whose first occurrence was in the past
    will not appear. Expanding RRULEs properly needs a dedicated library
    (e.g. recurring-ical-events) which isn't installed; left as a known
    limitation rather than adding an untested new dependency."""
    if not CALENDAR_ICAL_URL:
        return []
    r = requests.get(CALENDAR_ICAL_URL, timeout=8)
    r.raise_for_status()
    cal = Calendar.from_ical(r.content)
    now = datetime.now()
    events = []
    for component in cal.walk('VEVENT'):
        dtstart = component.get('dtstart')
        summary = component.get('summary')
        if dtstart is None or summary is None:
            continue
        try:
            start_iso = _event_start_iso(dtstart)
            start_dt = datetime.fromisoformat(start_iso)
        except (ValueError, AttributeError):
            continue
        if start_dt < now:
            continue
        events.append({'start': start_iso, 'title': str(summary)})
    events.sort(key=lambda e: e['start'])
    return events[:limit]


@app.route('/api/calendar')
@app.route('/calendar')
def calendar():
    return jsonify(fetch_calendar_events())

# --- Text-to-speech ---
@app.route('/tts', methods=['POST'])
def tts():
    data = get_json_body()
    text = str(data.get('text') or '').strip()
    agent = str(data.get('agent') or 'jarvis')
    voice_id = AGENT_VOICE_IDS.get(agent, ELEVENLABS_VOICE_ID)
    if not text:
        return jsonify({'error': 'no text provided'}), 400
    if not ELEVENLABS_API_KEY or not voice_id:
        return jsonify({'error': 'TTS not configured'}), 500
    text = text[:2000]
    try:
        r = requests.post(
            f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
            headers={
                'xi-api-key': ELEVENLABS_API_KEY,
                'Content-Type': 'application/json',
                'Accept': 'audio/mpeg',
            },
            json={
                'text': text,
                'model_id': 'eleven_turbo_v2_5',
                'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75},
            },
            timeout=20,
        )
        if r.status_code != 200:
            return jsonify({'error': f'elevenlabs error {r.status_code}: {r.text[:200]}'}), 502
        return Response(r.content, mimetype='audio/mpeg')
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 502

# ── Proxy /api/* → Flask endpoints ───────────────────────────────────
@app.route('/api/weather')
def api_weather():
    return weather()

@app.route('/api/ask', methods=['POST'])
def api_ask():
    return ask()

# ── Health check ─────────────────────────────────────────────────────
@app.route('/ping')
def ping():
    return jsonify({'status': 'ok', 'model': MODEL})

if __name__ == '__main__':
    print('JARVIS backend starting on http://0.0.0.0:5000')
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
