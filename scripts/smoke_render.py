"""Real API/worker rendering proof. Requires generation disabled; makes no cloud calls.

Creates and deletes only its own temporary course. Run from the repository root
with backend/.venv/Scripts/python.exe scripts/smoke_render.py.
"""
import json
import time
import uuid
from pathlib import Path
import requests


def main():
    session=requests.Session()
    session.trust_env=False
    origin='http://127.0.0.1:8765'
    def call(method,path,expected=200,**kwargs):
        response=session.request(method,origin+'/api/'+path,timeout=30,**kwargs)
        assert response.status_code==expected,(path,response.status_code,response.text[:300])
        return response.json() if response.content else None
    def wait(job_id):
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            job=call('GET',f'jobs/{job_id}/')
            if job['status'] in ('complete','failed','paused','cancelled'): return job
            time.sleep(.5)
        raise AssertionError('Job did not finish within ten minutes')
    status=call('GET','status/')
    assert status['worker']['running'] and not status['generation_enabled'], 'Requires running worker and disabled cloud generation.'
    course=call('POST','courses/',201,json={'name':'Render verification '+uuid.uuid4().hex[:8]})
    try:
        note='The processor places address 16 on the address bus and asserts a read request. Memory returns data 42 with a valid signal. The processor samples only when data is valid. This is a simplified teaching bus.'
        source=call('POST','sources/',201,json={'course':course['id'],'title':'Original teaching notes','text':note})
        assert wait(source['job']['id'])['status']=='complete'
        page=call('GET',f"sources/{source['id']}/")['pages'][0]
        lesson=call('POST','lessons/',201,json={'course':course['id'],'title':'Read handshake proof','prompt':'Explain processor address and data.'})
        assert wait(lesson['job']['id'])['status']=='paused'
        spec=json.loads((Path(__file__).resolve().parents[1]/'examples/bus-read.json').read_text(encoding='utf-8'))
        for chapter in spec['chapters']:
            for scene in chapter['scenes']: scene['source_refs']=[f"p{page['id']}"]
        revision=call('POST',f"lessons/{lesson['id']}/revisions/",201,json={'spec':spec,'citations':[{'page_id':page['id'],'quote':note}]})
        render=call('POST',f"lessons/{lesson['id']}/render/",202,json={'revision_id':revision['id']})
        job=wait(render['job']['id'])
        assert job['status']=='complete',job['error']
        result=call('GET',f"lessons/{lesson['id']}/")['revisions'][0]
        assert result['video_url'] and result['captions_url'] and result['transcript_url']
        video=session.get(origin+result['video_url'],headers={'Range':'bytes=0-99'},timeout=30)
        assert video.status_code==206 and len(video.content)==100
        scene=result['manifest']['scenes'][0]
        context={'revision_id':revision['id'],'scene_id':scene['scene_id'],'time_seconds':scene['start_seconds']+1,'object_ids':[scene['objects'][0]['id']]}
        conversation=call('POST','conversations/',201,json={'course':course['id'],'title':'Paused question'})
        question=call('POST',f"conversations/{conversation['id']}/messages/",202,json={'content':'Why?','context':context})
        assert wait(question['job']['id'])['status']=='paused'
        assert call('GET',f"conversations/{conversation['id']}/messages/")[0]['context']==context
        followup=call('POST','lessons/',201,json={'course':course['id'],'title':'Follow-up','prompt':'Why?','purpose':'followup','target_minutes':2,'context':context})
        assert followup['id']!=lesson['id'] and wait(followup['job']['id'])['status']=='paused'
        assert len(call('GET',f"lessons/{lesson['id']}/")['revisions'])==1
        print('PASS: API storyboard -> real worker render -> media range -> persisted scene question -> separate follow-up; cloud jobs pause without credentials.')
        print(json.dumps({'duration_seconds':result['manifest']['duration_seconds'],'scene_count':len(result['manifest']['scenes'])}))
    finally:
        for attempt in range(30):
            response=session.delete(origin+f"/api/courses/{course['id']}/",timeout=30)
            if response.status_code==204: break
            assert response.status_code==409,response.text
            time.sleep(1)
        else: raise AssertionError('Temporary course still has an active job; retry deletion after worker stops.')
    print('PASS: temporary course, source media, render and cache deleted.')


if __name__=='__main__': main()
