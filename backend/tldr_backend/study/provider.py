"""One explicit Gemini REST provider. No provider fallback, no billing inference."""
import json
import os
import re
import time
import requests
from .models import RuntimeState

class GenerationUnavailable(Exception):
    pass
class QuotaPaused(GenerationUnavailable):
    pass

def configuration():
    issues = []
    if not os.getenv('GEMINI_API_KEY'):
        issues.append('Set GEMINI_API_KEY in the local runtime environment.')
    if os.getenv('TLDR_FREE_PROJECT_ACK') != 'I_CONFIRM_BILLING_IS_DISABLED':
        issues.append('Confirm that the dedicated Gemini project has billing disabled.')
    if os.getenv('TLDR_DATA_TERMS_ACK') != 'I_ACCEPT_GOOGLE_FREE_TIER_DATA_TERMS':
        issues.append('Accept Google free-tier data terms before sending course excerpts.')
    model = os.getenv('TLDR_GEMINI_MODEL','gemini-3.8-flash')
    if model != 'gemini-3.8-flash':
        issues.append('Only the verified free-tier model gemini-3.8-flash is enabled.')
    paused = RuntimeState.objects.filter(key='quota', value__paused=True).exists()
    return {'provider':'Gemini', 'model':model, 'generation_enabled':not issues and not paused, 'configuration_issues':issues, 'quota_paused':paused}

def generate_json(prompt, *, cancelled=lambda:False, images=()):
    config = configuration()
    if config['quota_paused']:
        raise QuotaPaused('Gemini quota is paused. Resume explicitly after the quota resets.')
    if config['configuration_issues']:
        raise GenerationUnavailable(' '.join(config['configuration_issues']))
    if len(prompt)>120000:
        raise ValueError('Generation context exceeds its bound.')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{config['model']}:generateContent"
    session = requests.Session()
    session.trust_env = False
    parts = [{'text':prompt}] + list(images)
    payload = {'contents':[{'role':'user','parts':parts}], 'generationConfig':{'responseMimeType':'application/json','temperature':0.25,'maxOutputTokens':24000}}
    for attempt in range(2):
        if cancelled():
            raise InterruptedError('Cancelled.')
        try:
            response = session.post(url, headers={'x-goog-api-key':os.environ['GEMINI_API_KEY']}, json=payload, timeout=(10,150), allow_redirects=False)
        except requests.RequestException:
            if attempt==0:
                time.sleep(1)
                continue
            raise GenerationUnavailable('Gemini could not be reached. No alternative provider was used.') from None
        if response.status_code==429:
            RuntimeState.objects.update_or_create(key='quota', defaults={'value':{'paused':True}})
            raise QuotaPaused('Gemini free-tier quota reached; generation paused. Resume explicitly after quota resets.')
        if response.status_code>=500 and attempt==0:
            time.sleep(1)
            continue
        if response.status_code>=500:
            raise GenerationUnavailable(f'Gemini is temporarily unavailable (HTTP {response.status_code}). Your work is saved. Retry later; no alternative model was used.')
        if response.status_code!=200:
            raise GenerationUnavailable(f'Gemini rejected the request (HTTP {response.status_code}). Check model availability, key and project settings.')
        if len(response.content)>2_000_000:
            raise ValueError('Gemini response exceeds its bound.')
        try:
            body = response.json()
            candidates = body['candidates']
            if candidates[0].get('finishReason') not in ('STOP',None):
                raise ValueError('Generation was incomplete or blocked.')
            raw = ''.join(p.get('text','') for p in candidates[0]['content']['parts'])
            result = json.loads(raw)
            if not isinstance(result,dict):
                raise ValueError('Expected a JSON object.')
            return result
        except (KeyError,IndexError,TypeError,json.JSONDecodeError):
            raise ValueError('Gemini returned invalid structured output.') from None
    raise GenerationUnavailable('Gemini request failed.')
