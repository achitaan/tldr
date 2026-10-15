"""Verify installed full media and optional no-cloud contextual API behavior."""
from pathlib import Path
import argparse
import json
import time
import requests
import av
from full_render import digest

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'artifacts/ece224-lesson'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--context-smoke',action='store_true');args=parser.parse_args()
    state=json.loads((OUTPUT/'installed.json').read_text())
    session=requests.Session();session.trust_env=False
    base='http://127.0.0.1:8765'
    def request(method,path,**kwargs):
        response=session.request(method,base+'/api/'+path,timeout=30,**kwargs);response.raise_for_status()
        return response.json() if response.status_code!=204 else None
    lesson=request('GET',f'lessons/{state["lesson_id"]}/')
    revision=next(r for r in lesson['revisions'] if r['id']==state['revision_id'])
    manifest=revision['manifest'];duration=manifest['duration_seconds']
    assert 600<=duration<=1200 and len(manifest['chapters'])==8 and len(manifest['scenes'])==100
    assert len(manifest['practice'])==6
    for point in manifest['practice']:
        scene=next(s for s in manifest['scenes'] if s['scene_id']==point['scene_id'])
        assert scene['start_seconds']<=point['time_seconds']<scene['end_seconds']
    for left,right in zip(manifest['scenes'],manifest['scenes'][1:]):assert abs(left['end_seconds']-right['start_seconds'])<.05
    assert all(0<=cue['start_seconds']<cue['end_seconds']<=duration for cue in manifest['cues'])
    for field in ('video_url','captions_url','transcript_url'):
        assert revision[field].startswith('/media/')
    response=session.get(base+revision['video_url'],headers={'Range':'bytes=0-4095'},timeout=30)
    assert response.status_code==206 and len(response.content)==4096 and 'bytes 0-4095/' in response.headers['Content-Range']
    caption=session.get(base+revision['captions_url'],timeout=30);caption.raise_for_status()
    assert caption.text.startswith('WEBVTT') and caption.text.count(' --> ')==len(manifest['cues'])
    movie=OUTPUT/'assembled/lesson.mp4'
    assert digest(movie)==state['video_sha256']==manifest['video_sha256']
    with av.open(str(movie)) as container:
        video=container.streams.video[0]
        assert (video.width,video.height)==(1920,1080) and float(video.average_rate)==30
        assert len(container.streams.audio)==1 and len(container.streams.subtitles)==1
        assert abs(container.duration/av.time_base-duration)<.1
    contexts=[]
    if args.context_smoke:
        status=request('GET','status/')
        if status['generation_enabled']:raise ValueError('Context smoke only runs with cloud generation disabled; refuse a possible provider request.')
        scene=next(s for s in manifest['scenes'] if s['chapter_id']=='propagation' and s.get('page')==22)
        context={'revision_id':revision['id'],'scene_id':scene['scene_id'],
                 'time_seconds':round((scene['start_seconds']+scene['end_seconds'])/2,3),'object_ids':[scene['objects'][0]['id']]}
        conversation=None;followup=None
        try:
            conversation=request('POST','conversations/',json={'course':state['course_id'],'title':'[Verification] Authored lesson context'})
            message=request('POST',f'conversations/{conversation["id"]}/messages/',json={'content':'Why must we check the receiving endpoint in this exact scene?','region_ids':[],'context':context})
            assert message['message']['context']==context
            followup=request('POST','lessons/',json={'course':state['course_id'],'title':'[Verification] Separate contextual follow-up','prompt':'Explain this exact paused scene in a separate focused lesson.','purpose':'followup','target_minutes':2,'context':context})
            jobs=[message['job']['id'],followup['job']['id']]
            deadline=time.monotonic()+30
            while True:
                snapshots=[request('GET',f'jobs/{id_}/') for id_ in jobs]
                if all(job['status']=='paused' for job in snapshots):break
                if any(job['status'] in ('failed','cancelled','complete') for job in snapshots) or time.monotonic()>deadline:raise ValueError('Expected a preserved paused job without configured AI.')
                time.sleep(.5)
            assert request('GET',f'lessons/{state["lesson_id"]}/')['revisions'][-1]['video_url']==revision['video_url']
            contexts=[{'kind':'chat','paused':True,'context':context},{'kind':'separate_followup','paused':True,'original_preserved':True}]
        finally:
            if conversation:request('DELETE',f'conversations/{conversation["id"]}/')
            if followup:request('DELETE',f'lessons/{followup["id"]}/')
    result={'duration_seconds':duration,'chapters':len(manifest['chapters']),'scenes':len(manifest['scenes']),
            'caption_cues':len(manifest['cues']),'practice_points':len(manifest['practice']),
            'http_range':True,'sidecar_and_embedded_captions':True,'video_sha256':state['video_sha256'],
            'context_smoke':contexts,'scope':'functional/media evidence; not a perceptual teaching-quality score'}
    (OUTPUT/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
