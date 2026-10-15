"""Import the user's named ECE224 samples through the running local API.

Original content stays in ignored local_data. The ignored state file makes
repeated invocations resume without re-uploading the same bytes.
"""
from pathlib import Path
import hashlib
import json
import time
import requests

ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'artifacts/ece224-import.json'
NAMES=['ece224-Va-buses.pdf','ece224-VIIIa-serial.pdf','ece224-Vb-buses-semi.pdf','ece224-IV-drivers.pdf','ece224-IV-drivers (1).pdf','ece224-VIIb-parallel.pdf','ece224-VIb-arbitration.pdf','ece224-IX-DMA.pdf','ece224-VIIa-parallel.pdf','ece224midterm2026.pdf']


def main():
    STATE.parent.mkdir(parents=True,exist_ok=True)
    state=json.loads(STATE.read_text()) if STATE.exists() else {'sources':{},'duplicates':[]}
    session=requests.Session();session.trust_env=False
    base='http://127.0.0.1:8765/api/'
    def request(method,path,**kwargs):
        response=session.request(method,base+path,timeout=45,**kwargs)
        response.raise_for_status()
        return response.json()
    def save(): STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
    if 'course_id' not in state:
        course=request('POST','courses/',json={'name':'ECE224 — course samples','description':'Local study samples imported from the ten PDF files provided in this chat. Originals and extracted pages stay on this computer.'})
        state['course_id']=course['id'];save()
    course_id=state['course_id']
    request('GET',f'courses/{course_id}/')
    for name in NAMES:
        path=Path.home()/'Downloads'/name
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in state['sources']:
            previous=state['sources'][digest]
            if previous['name']!=name and name not in state['duplicates']:
                state['duplicates'].append(name);save()
            continue
        with path.open('rb') as stream:
            source=request('POST','sources/',data={'course':str(course_id),'title':path.stem},files={'file':(name,stream,'application/pdf')})
        state['sources'][digest]={'id':source['id'],'name':name,'job_id':source['job']['id'],'status':'queued'}
        save();print(json.dumps({'imported':name,'source_id':source['id']}),flush=True)
    deadline=time.monotonic()+1800
    while time.monotonic()<deadline:
        sources=request('GET',f'sources/?course={course_id}')
        counts={key:sum(item['status']==key for item in sources) for key in ('queued','ready','error')}
        for item in state['sources'].values():
            source=next((s for s in sources if s['id']==item['id']),None)
            if source: item.update(status=source['status'],pages=len(source['pages']),error=source.get('error',''))
        save()
        print(json.dumps({'course_id':course_id,**counts,'extracted_pages':sum(len(s['pages']) for s in sources)}),flush=True)
        if counts['error']: raise RuntimeError('An import failed; inspect its preserved source and job in the application.')
        if counts['ready']==len(state['sources']):
            print('All unique PDFs are ready; duplicate bytes were not imported twice.',flush=True)
            return
        time.sleep(4)
    raise RuntimeError('Import remains in progress. Run this script again to resume monitoring without duplicate uploads.')


if __name__=='__main__': main()
