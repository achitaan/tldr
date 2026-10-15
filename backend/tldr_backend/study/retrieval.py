"""Course-scoped SQLite FTS5 with optional local embeddinggemma reranking."""
import math
import os
import re
import requests
import hashlib
import io
from pathlib import Path
from types import MappingProxyType
from django.db import connection
from .models import Page, Region, RuntimeState

def ensure_fts():
    with connection.cursor() as cur:
        cur.execute('CREATE VIRTUAL TABLE IF NOT EXISTS study_page_fts USING fts5(text, course UNINDEXED)')

def embedding(text):
    if os.getenv('TLDR_OLLAMA_EMBEDDINGS') != '1':
        return []
    try:
        session = requests.Session()
        session.trust_env = False
        response = session.post('http://127.0.0.1:11434/api/embed', json={'model': 'embeddinggemma', 'input': text[:12000]}, timeout=(2, 30))
        response.raise_for_status()
        vectors = response.json()['embeddings']
        result = vectors[0]
        if not isinstance(result, list) or not 16 <= len(result) <= 8192 or any(not isinstance(x, (int,float)) or not math.isfinite(x) for x in result):
            raise ValueError('Invalid embedding response')
        RuntimeState.objects.update_or_create(key='embedding', defaults={'value': {'status': 'ready'}})
        return result
    except (requests.RequestException, ValueError, KeyError, IndexError, TypeError):
        RuntimeState.objects.update_or_create(key='embedding', defaults={'value': {'status': 'unavailable', 'detail': 'Local embeddings unavailable; lexical retrieval remains active.'}})
        return []

def index_page(page):
    ensure_fts()
    with connection.cursor() as cur:
        cur.execute('DELETE FROM study_page_fts WHERE rowid=%s', [page.id])
        cur.execute('INSERT INTO study_page_fts(rowid,text,course) VALUES(%s,%s,%s)', [page.id, page.text, page.source.course_id])
    vector = embedding(page.text)
    Page.objects.filter(pk=page.id).update(embedding=vector)

def cosine(a,b):
    if len(a) != len(b) or not a or not b:
        return 0
    denominator = math.sqrt(sum(x*x for x in a) * sum(x*x for x in b))
    return sum(x*y for x,y in zip(a,b)) / denominator if denominator else 0

def evidence_window(text,tokens,limit=6000):
    if len(text)<=limit: return text
    # Prefer distinctive matches, retaining an exact contiguous source substring.
    position=0
    for token in sorted(set(tokens),key=len,reverse=True):
        match=re.search(r'\b'+re.escape(token)+r'\b',text,re.IGNORECASE)
        if match:
            position=match.start();break
    start=max(0,min(len(text)-limit,position-limit//3))
    return text[start:start+limit]

def retrieve(course_id, question, region_ids=(), limit=8):
    ensure_fts()
    tokens = re.findall(r'\w+', question, flags=re.UNICODE)[:30]
    ids = []
    if tokens:
        query = ' OR '.join('"' + token.replace('"','') + '"' for token in tokens)
        with connection.cursor() as cur:
            cur.execute('SELECT rowid FROM study_page_fts WHERE study_page_fts MATCH %s AND course=%s ORDER BY rank LIMIT 30', [query, course_id])
            ids = [row[0] for row in cur.fetchall()]
    scores = {pk: 1/(60+i) for i,pk in enumerate(ids)}
    query_vector = embedding(question)
    if query_vector:
        candidates = Page.objects.filter(source__course_id=course_id).exclude(embedding=[]).only('id','embedding')[:1000]
        ranked = sorted(((cosine(query_vector,p.embedding),p.id) for p in candidates), reverse=True)[:30]
        for i,(_,pk) in enumerate(ranked):
            scores[pk] = scores.get(pk,0) + 1/(60+i)
    ranked_ids = sorted(scores, key=scores.get, reverse=True)
    pages = {p.id:p for p in Page.objects.filter(pk__in=ranked_ids, source__course_id=course_id).select_related('source')}
    evidence = []
    for region in Region.objects.filter(id__in=region_ids, page__source__course_id=course_id).select_related('page__source'):
        # Region text is user-confirmed region evidence; full-page OCR must not be
        # attributed to a crop that may not contain it.
        text = region.text.strip()
        evidence.append({'id':f'r{region.id}', 'page_id':region.page_id, 'region_id':region.id, 'source_id':region.page.source_id, 'source_title':region.page.source.title, 'page_number':region.page.number, 'text':evidence_window(text,tokens)})
    for pk in ranked_ids:
        if pk in pages:
            page = pages[pk]
            evidence.append({'id':f'p{pk}', 'page_id':pk, 'source_id':page.source_id, 'source_title':page.source.title, 'page_number':page.number, 'text':evidence_window(page.text,tokens)})
        if len(evidence)>=limit:
            break
    return evidence[:limit]

def validate_citations(citations, evidence):
    if not isinstance(citations,list) or len(citations)>30:
        raise ValueError('Invalid citations.')
    validated = []
    for item in citations:
        if not isinstance(item,dict):
            raise ValueError('Invalid citation.')
        quote = item.get('quote')
        match = next((e for e in evidence if e['page_id']==item.get('page_id') and e.get('region_id')==item.get('region_id')), None)
        visual = bool(match and match.get('image_supplied') and item.get('visual') is True and item.get('region_id') and quote == '' and not match['text'].strip())
        if not visual and (not match or not isinstance(quote,str) or not quote.strip() or len(quote)>1200 or quote not in match['text']):
            raise ValueError('A citation did not match the retrieved source exactly.')
        validated.append({k:v for k,v in match.items() if k not in ('text','id','image_supplied')} | {'quote':quote, 'visual':visual})
    return validated

def image_parts(evidence):
    """Bounded downsampled images/crops; fixed local files, no remote URL fetches."""
    import base64
    import io
    from PIL import Image
    parts=[]
    for item in evidence:
        if len(parts)>=6: break
        page=Page.objects.filter(pk=item['page_id']).first()
        if not page or not page.image: continue
        with Image.open(page.image.path) as image:
            image=image.convert('RGB')
            if item.get('region_id'):
                region=Region.objects.get(pk=item['region_id'],page=page)
                w,h=image.size
                image=image.crop((int(region.x*w),int(region.y*h),max(int((region.x+region.width)*w),int(region.x*w)+1),max(int((region.y+region.height)*h),int(region.y*h)+1)))
            image.thumbnail((1200,1200))
            output=io.BytesIO();image.save(output,format='JPEG',quality=80)
            parts.extend([{'text':f"Source image {item['id']}; page_id={page.id}; region_id={item.get('region_id')}. Use visual:true with an empty quote only if this selected image region has no extracted text."},{'inlineData':{'mimeType':'image/jpeg','data':base64.b64encode(output.getvalue()).decode('ascii')}}])
            item['image_supplied']=True
    return parts

def bind_source_assets(citations, course_id):
    """Snapshot trusted image identity and region geometry into revision citations."""
    from PIL import Image
    bound=[]
    for citation in citations:
        item=dict(citation)
        page=Page.objects.filter(pk=item['page_id'],source__course_id=course_id).first()
        if not page:
            raise ValueError('A citation no longer belongs to this course.')
        if page.image:
            path=Path(page.image.path)
            if not path.is_file():
                raise ValueError('A cited source image is missing.')
            raw=path.read_bytes()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                pixel_width,pixel_height=image.size
            crop={'x':0.0,'y':0.0,'width':1.0,'height':1.0}
            if item.get('region_id'):
                region=Region.objects.filter(pk=item['region_id'],page=page).first()
                if not region:
                    raise ValueError('A cited source region is missing.')
                crop={key:float(getattr(region,key)) for key in ('x','y','width','height')}
                if any(not math.isfinite(value) for value in crop.values()) or crop['x']<0 or crop['y']<0 or crop['width']<=0 or crop['height']<=0 or crop['x']+crop['width']>1 or crop['y']+crop['height']>1:
                    raise ValueError('A cited source region has invalid normalized bounds.')
            item['source_asset']={'page_id':page.id,'source_id':page.source_id,
                **({'region_id':item['region_id']} if item.get('region_id') else {}),
                'image_sha256':hashlib.sha256(raw).hexdigest(),'pixel_width':pixel_width,
                'pixel_height':pixel_height,'crop':crop}
        bound.append(item)
    return bound

def resolve_revision_assets(revision):
    """Resolve only revision-bound, same-course source refs to immutable PNG crops."""
    from PIL import Image
    course_id=revision.lesson.course_id
    assets={}
    cited={f"r{c['region_id']}" if c.get('region_id') else f"p{c['page_id']}":c for c in revision.citations}
    requested={obj['source_ref'] for chapter in revision.spec.get('chapters',[]) for scene in chapter.get('scenes',[]) for obj in scene.get('objects',[]) if obj.get('kind')=='source_image'}
    for ref in requested:
        citation=cited.get(ref)
        snapshot=citation.get('source_asset') if citation else None
        if not citation or not isinstance(snapshot,dict):
            raise ValueError(f'Source image {ref} is not bound to this revision.')
        page=Page.objects.filter(pk=citation['page_id'],source__course_id=course_id).first()
        if not page or not page.image or page.source_id != snapshot.get('source_id'):
            raise ValueError(f'Source image {ref} is missing or belongs to another course.')
        if citation.get('region_id'):
            region=Region.objects.filter(pk=citation['region_id'],page=page).first()
            if not region or region.id != snapshot.get('region_id'):
                raise ValueError(f'Source region {ref} is missing or stale.')
            current={key:float(getattr(region,key)) for key in ('x','y','width','height')}
            if current != snapshot.get('crop'):
                raise ValueError(f'Source region {ref} changed after this revision was created.')
        path=Path(page.image.path)
        if not path.is_file():
            raise ValueError(f'Source image {ref} is missing.')
        raw=path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != snapshot.get('image_sha256'):
            raise ValueError(f'Source image {ref} changed after this revision was created.')
        crop=snapshot.get('crop')
        if not isinstance(crop,dict) or set(crop)!={'x','y','width','height'} or any(isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) for value in crop.values()) or crop['x']<0 or crop['y']<0 or crop['width']<=0 or crop['height']<=0 or crop['x']+crop['width']>1 or crop['y']+crop['height']>1:
            raise ValueError(f'Source image {ref} has invalid revision crop bounds.')
        with Image.open(io.BytesIO(raw)) as image:
            image=image.convert('RGB')
            if list(image.size) != [snapshot.get('pixel_width'),snapshot.get('pixel_height')]:
                raise ValueError(f'Source image {ref} dimensions changed after this revision was created.')
            w,h=image.size
            box=(int(crop['x']*w),int(crop['y']*h),max(int((crop['x']+crop['width'])*w),int(crop['x']*w)+1),max(int((crop['y']+crop['height'])*h),int(crop['y']*h)+1))
            image=image.crop(box)
            output=io.BytesIO();image.save(output,format='PNG',optimize=False)
        content=output.getvalue()
        assets[ref]=MappingProxyType({'content':content,'sha256':hashlib.sha256(content).hexdigest(),
            'width':image.width,'height':image.height,'crop':MappingProxyType(dict(crop)),
            'provenance':'original_source'})
    return MappingProxyType(assets)
