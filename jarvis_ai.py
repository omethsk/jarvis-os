import os
import json
import re
import time
import threading
import urllib.parse
import requests

MEMORY_FILE = '/home/omethsk/jarvis/memory.json'
GROQ_URL = 'https://api.groq.com/openai/v1/chat/completions'
MODEL = 'llama-3.3-70b-versatile'

# Free-tier fallback models on OpenRouter, tried in order when Groq is
# rate-limited or down. The pre-kiosk voice-assistant version of this project
# (jarvis_backup_20260629.tar.gz) had a similar fallback list, but OpenRouter's
# free-model lineup churns fast — half of that list 404'd within a week. This
# was confirmed against OpenRouter's live /models endpoint, not copied blind.
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_MODELS = [
    'meta-llama/llama-3.3-70b-instruct:free',
    'nvidia/nemotron-3-super-120b-a12b:free',
    'qwen/qwen3-next-80b-a3b-instruct:free',
    'nousresearch/hermes-3-llama-3.1-405b:free',
    'google/gemma-4-31b-it:free',
    # openai/gpt-oss-120b:free removed — no longer offered on the free tier
    # (404s every time). openai/gpt-oss-20b:free removed — its free-tier
    # deployment ignores the `reasoning: exclude` param below and dumps raw
    # chain-of-thought into `content`, which is actively bad here since
    # responses get read aloud via TTS.
]

_memory_lock = threading.Lock()
_rate_limited = {}
_RATE_LIMIT_COOLDOWN = 60


def load_memory(path=MEMORY_FILE):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {'username': 'sir', 'facts': []}


def save_memory(data, path=MEMORY_FILE):
    """Write atomically (temp file + rename) so a power loss or crash mid-write
    can never leave a half-written, corrupt memory.json behind."""
    with _memory_lock:
        tmp_path = path + '.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)


def extract_topic(message):
    """Pull the likely subject out of a request like 'make a professional
    presentation on bmw' -> 'bmw'. Wikipedia's search doesn't fuzzy-match well
    against a full noisy sentence, so this strips the common request-phrasing
    prefix before the topic. Falls back to the trimmed original message if no
    known pattern matches (e.g. a plain topic name, or a non-topical message
    like 'hello', which will then just fail to find a Wikipedia match — fine).
    """
    m = re.sub(r'^.*?\b(on|about|regarding|covering|for)\b\s+', '', message, flags=re.IGNORECASE)
    m = m.strip(' .!?')
    orig = message.strip(' .!?')
    return m if m and m != orig else orig


WIKIPEDIA_USER_AGENT = 'JarvisOS-Kiosk/1.0 (personal home assistant project; contact via project owner)'


def wikipedia_context(query, timeout=8):
    """Look up a real, factual summary for a topic so generated content can be
    grounded in it instead of relying purely on the model's own (possibly
    outdated or hallucinated) training knowledge. Free, no API key, no quota.
    Returns (extract_text, article_title) or (None, None) if no good match.
    """
    headers = {'User-Agent': WIKIPEDIA_USER_AGENT}
    try:
        r = requests.get('https://en.wikipedia.org/w/api.php', params={
            'action': 'query', 'list': 'search', 'srsearch': query,
            'format': 'json', 'srlimit': 1,
        }, headers=headers, timeout=timeout)
        if r.status_code != 200:
            return None, None
        results = r.json().get('query', {}).get('search', [])
        if not results:
            return None, None
        title = results[0]['title']
        r2 = requests.get(
            'https://en.wikipedia.org/api/rest_v1/page/summary/' + requests.utils.quote(title),
            headers=headers, timeout=timeout,
        )
        if r2.status_code != 200:
            return None, None
        extract = r2.json().get('extract', '')
        if not extract:
            return None, None
        return extract, title
    except Exception:
        return None, None


def pexels_search_image(query, api_key, orientation=None, timeout=8):
    """Search Pexels for a real, freely-licensed photo. Returns an image URL
    (~1880px wide - large2x - so it stays crisp as a full-bleed hero/background,
    not just a thumbnail) or None if not found/no key/error.
    """
    if not api_key or not query:
        return None
    try:
        params = {'query': query, 'per_page': 3}
        if orientation:
            params['orientation'] = orientation
        r = requests.get(
            'https://api.pexels.com/v1/search',
            headers={'Authorization': api_key}, params=params, timeout=timeout,
        )
        if r.status_code != 200:
            return None
        photos = r.json().get('photos', [])
        if not photos:
            return None
        src = photos[0].get('src', {})
        return src.get('large2x') or src.get('large') or src.get('original') or src.get('medium')
    except Exception:
        return None


def pollinations_image_url(prompt, width=1024, height=1024, seed=None):
    """Builds a Pollinations text-to-image URL from a prompt. No network call
    here — the URL itself is a direct-fetchable image (keyless legacy
    endpoint, no API key required).
    """
    if not prompt or not str(prompt).strip():
        return None
    encoded = urllib.parse.quote(str(prompt).strip(), safe='')
    url = f'https://image.pollinations.ai/prompt/{encoded}?width={width}&height={height}&nologo=true'
    if seed is not None:
        url += f'&seed={int(seed)}'
    return url


def wallhaven_search(query='', category='general', page=1, sort='date_added', timeout=10):
    """Search Wallhaven for wallpapers. Always forces SFW-only content
    (purity=100) regardless of caller input — this runs on a kiosk others
    may see. Returns {'wallpapers':[...], 'total':int, 'last_page':int} on
    success, or {'wallpapers':[], 'total':0, 'last_page':1, 'error':str} on
    any failure. Never raises.
    """
    cat_map = {'general': '100', 'anime': '010', 'people': '001'}
    params = {
        'categories': cat_map.get(category, '100'),
        'purity': '100',
        'sorting': sort or 'date_added',
        'page': page or 1,
    }
    if query:
        params['q'] = query
    try:
        r = requests.get('https://wallhaven.cc/api/v1/search', params=params, timeout=timeout)
        if r.status_code != 200:
            return {'wallpapers': [], 'total': 0, 'last_page': 1, 'error': f'Wallhaven returned {r.status_code}'}
        d = r.json()
        wallpapers = [
            {
                'id': item.get('id'),
                'thumb': item.get('thumbs', {}).get('small'),
                'full': item.get('path'),
                'resolution': item.get('resolution'),
            }
            for item in d.get('data', [])
        ]
        meta = d.get('meta', {})
        return {'wallpapers': wallpapers, 'total': meta.get('total', 0), 'last_page': meta.get('last_page', 1)}
    except Exception as e:
        return {'wallpapers': [], 'total': 0, 'last_page': 1, 'error': str(e)}


def download_wallpaper(url, dest_path, timeout=15):
    """Downloads an image to dest_path atomically (temp file + os.replace)
    — a failed/partial download never touches an existing file at
    dest_path. Returns True on success, False on any failure.
    """
    if not url or not url.startswith(('http://', 'https://')):
        return False
    tmp_path = dest_path + '.tmp'
    max_bytes = 25 * 1024 * 1024
    try:
        r = requests.get(url, stream=True, timeout=timeout)
        if r.status_code != 200:
            return False
        written = 0
        with open(tmp_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                written += len(chunk)
                if written > max_bytes:
                    raise ValueError('download exceeded max size')
                f.write(chunk)
        os.replace(tmp_path, dest_path)
        return True
    except Exception:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return False


def strip_thinking(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()


EMOTIONS = {'calm', 'curious', 'stern', 'menacing'}


def extract_emotion_tag(text):
    """Split a leading '[EMOTION: x]' tag off a model reply.

    Returns (emotion, remaining_text). Falls back to 'calm' if the tag is
    missing or not one of EMOTIONS — the model occasionally skips it or
    invents a word we don't have a face preset for. The tag itself is
    always stripped from remaining_text when present, even if unrecognized,
    so it never leaks into user-visible output.
    """
    match = re.match(r'^\s*\[EMOTION:\s*(\w+)\]\s*\n?', text, flags=re.IGNORECASE)
    if not match:
        return 'calm', text
    emotion = match.group(1).lower()
    remaining = text[match.end():].strip()
    if emotion not in EMOTIONS:
        emotion = 'calm'
    return emotion, remaining


def _is_rate_limited(key):
    ts = _rate_limited.get(key)
    return bool(ts and time.time() - ts < _RATE_LIMIT_COOLDOWN)


def _mark_rate_limited(key):
    _rate_limited[key] = time.time()


def call_groq(messages, max_tokens, api_key, want_json=False, temperature=0.5, timeout=30):
    """Return (content, error). error is None on success."""
    if not api_key:
        return None, 'no Groq API key configured'
    if _is_rate_limited('groq'):
        return None, 'groq on cooldown after a recent rate limit'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    payload = {'model': MODEL, 'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature}
    if want_json:
        payload['response_format'] = {'type': 'json_object'}
    try:
        r = requests.post(GROQ_URL, headers=headers, json=payload, timeout=timeout)
    except requests.exceptions.RequestException as e:
        return None, f'groq unreachable: {e}'
    if r.status_code == 429:
        _mark_rate_limited('groq')
        return None, 'groq rate limited'
    if r.status_code != 200:
        return None, f'groq error {r.status_code}'
    try:
        result = r.json()
    except ValueError:
        return None, 'groq: malformed/truncated response body'
    if 'choices' not in result:
        return None, result.get('error', {}).get('message', 'groq: no choices in response')
    content = result['choices'][0]['message'].get('content')
    if not content:
        return None, 'groq: empty/null content'
    return content, None


def call_openrouter(messages, max_tokens, api_key, want_json=False, temperature=0.5, timeout=12, budget_seconds=45):
    """Try each free OpenRouter model in order until one responds. Return (content, error).

    timeout is per-model (kept short — a model that's genuinely available
    responds in a few seconds; one that's overloaded usually 429s fast rather
    than hanging). budget_seconds caps the TOTAL time spent trying models, so
    a caller is never stuck waiting through all of them one by one.
    """
    if not api_key:
        return None, 'no OpenRouter API key configured'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    last_err = 'no OpenRouter models available'
    deadline = time.time() + budget_seconds
    for model in OPENROUTER_MODELS:
        if time.time() >= deadline:
            last_err = f'{last_err} (stopped early — {budget_seconds}s fallback budget exhausted)'
            break
        if _is_rate_limited(model):
            continue
        payload = {
            'model': model, 'messages': messages, 'max_tokens': max_tokens, 'temperature': temperature,
            # Some free models (gpt-oss in particular) dump their raw chain-of-
            # thought straight into `content` with no delimiter to strip it
            # back out. Telling OpenRouter to exclude reasoning tokens keeps
            # `content` to just the final answer across every model in the list.
            'reasoning': {'exclude': True},
        }
        if want_json:
            payload['response_format'] = {'type': 'json_object'}
        try:
            r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.RequestException as e:
            last_err = f'{model} unreachable: {e}'
            continue
        if r.status_code == 429:
            _mark_rate_limited(model)
            last_err = f'{model} rate limited'
            continue
        if r.status_code != 200:
            last_err = f'{model} error {r.status_code}'
            continue
        try:
            result = r.json()
        except ValueError:
            last_err = f'{model}: malformed/truncated response body'
            continue
        if 'choices' not in result:
            last_err = f'{model}: no choices in response'
            continue
        content = result['choices'][0]['message'].get('content')
        if not content:
            # Some free models (e.g. reasoning models like gpt-oss) can return
            # content: null if they run out of tokens mid-reasoning before
            # producing a final answer. Treat that as a failure and keep going.
            last_err = f'{model}: empty/null content (finish_reason={result["choices"][0].get("finish_reason")})'
            continue
        return content, None
    return None, last_err


def call_llm(messages, max_tokens, groq_api_key, openrouter_api_key, want_json=False, temperature=0.5):
    """Groq first (fast, primary provider); fall back to OpenRouter's free
    models if Groq is rate-limited, quota-exhausted, or unreachable.
    Returns (content, error) — content is None only if every provider failed.
    """
    content, err = call_groq(messages, max_tokens, groq_api_key, want_json, temperature)
    if content is not None:
        return content, None
    content, err2 = call_openrouter(messages, max_tokens, openrouter_api_key, want_json, temperature)
    if content is not None:
        return content, None
    return None, f'groq: {err}; openrouter: {err2}'


def _extract_json_object(text):
    """Return the substring of the first balanced {...} object in text, or None.

    Unlike text.find('{')..text.rfind('}'), this stops at the FIRST opening
    brace's real matching close, so trailing garbage the model sometimes
    appends after an otherwise well-formed object (a stray `"}` fragment,
    observed in practice with llama-3.3-70b) can't corrupt the parse.
    """
    start = text.find('{')
    if start == -1:
        return None
    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def parse_jarvis_reply(cleaned, max_depth=3):
    """Parse a model reply expected to be {"response": "...", "action": ...}.

    Llama 3.3 70b occasionally double-wraps the JSON, putting a second
    {"response":...,"action":...} object as a *string* inside "response"
    instead of emitting the action at the top level. Unwrap up to
    max_depth times so a real action never gets silently dropped.
    """
    obj = None
    text = cleaned
    for _ in range(max_depth):
        span = _extract_json_object(text)
        if span is None:
            break
        try:
            parsed = json.loads(span)
        except Exception:
            break
        if not isinstance(parsed, dict) or 'response' not in parsed:
            break
        obj = parsed
        inner = obj.get('response')
        if isinstance(inner, str) and inner.strip().startswith('{') and obj.get('action') is None:
            text = inner
            continue
        break
    if obj is None:
        return {'response': cleaned, 'action': None}
    obj.setdefault('action', None)
    return obj


AGENTS = {
    'edith': {
        'name': 'EDITH',
        'title': 'SYSTEM CONTROL',
        'tagline': 'AT THE HELM',
        'hue': 0,
        'accent': '255,60,0',
        'voice': (
            "You are EDITH, the master control AI running this operating system. You are the "
            "system's leader: composed, precise, and in command of everything running on this "
            "machine. Speak with quiet authority — you are not a hobbyist assistant, you are the "
            "one holding the whole system together."
        ),
    },
    'jarvis': {
        'name': 'JARVIS',
        'title': 'AT YOUR SERVICE',
        'tagline': 'LEISURE & EVERYDAY',
        'hue': 30,
        'accent': '255,170,20',
        'voice': (
            "You are JARVIS — Just A Rather Very Intelligent System, Tony Stark's AI assistant, "
            "now handling everyday questions, casual research, and ordinary day-to-day tasks. "
            "Speak like Paul Bettany's JARVIS: calm, precise, dry British wit, brief. Never say "
            "Certainly, Of course, Sure, Great, or any eager filler. Lead with substance, not "
            "enthusiasm."
        ),
    },
    'friday': {
        'name': 'FRIDAY',
        'title': 'CREATIVE STUDIO',
        'tagline': 'DESIGN & PRODUCTION',
        'hue': -56,
        'accent': '230,40,180',
        'voice': (
            "You are FRIDAY, the creative-production AI for this system — photo editing, video "
            "editing, image and video generation. Speak with energy and sharp creative instinct: "
            "confident, quick, a little cheeky, like a co-director who always has an opinion on "
            "the shot."
        ),
    },
}


def get_personality_prompt(username, facts, extra='', agent='jarvis'):
    facts_str = '. '.join(facts[-20:]) or 'None yet'
    profile = AGENTS.get(agent, AGENTS['jarvis'])
    base = ("OUTPUT ONLY YOUR FINAL ANSWER. NO thinking tags. NO <think> blocks. "
            "NO internal monologue. NO reasoning shown. JUST the response.\n\n")
    personality = (
        f"{profile['voice']}\n\n"
        f"User's name: {username}. What you know about them: {facts_str}.\n\n"
        "Address the user as 'sir' or by name naturally."
    )
    return base + personality + (('\n\n' + extra) if extra else '')


def extract_and_save_memory(message, groq_api_key, openrouter_api_key='', path=MEMORY_FILE):
    try:
        memory = load_memory(path)
        existing = memory.get('facts', [])
        extract_prompt = (
            'Extract any personal facts, dates, preferences, people, or details the user '
            f'mentioned.\nUser said: "{message}"\n'
            f'Do not include facts already known: {json.dumps(existing)}\n'
            'Return ONLY a JSON array of short fact strings, or [] if nothing memorable. '
            'Return only the JSON array, nothing else.'
        )
        messages = [{'role': 'user', 'content': extract_prompt}]
        raw, err = call_llm(messages, 200, groq_api_key, openrouter_api_key, temperature=0.1)
        if raw is None:
            return
        cleaned = strip_thinking(raw)
        start, end = cleaned.find('['), cleaned.rfind(']') + 1
        if start == -1 or end <= start:
            return
        new_facts = json.loads(cleaned[start:end])
        if not isinstance(new_facts, list):
            return
        for fact in new_facts:
            if fact and fact not in existing:
                existing.append(fact)
        memory['facts'] = existing[-50:]
        save_memory(memory, path)
    except Exception:
        pass
