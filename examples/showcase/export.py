"""Verify and export the opening quality study into the static app demo."""
from pathlib import Path
import hashlib
import json
import shutil
import av

ROOT=Path(__file__).resolve().parents[2]
INPUT=ROOT/'artifacts/showcase/opening'
PUBLIC=ROOT/'frontend/tldr-frontend/public/sample/showcase'


def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'


def main():
    narration=json.loads((INPUT/'narration.json').read_text())
    visual=json.loads((INPUT/'visual-timing.json').read_text())
    events=visual['visual_events']
    assert len(events)>=19
    # Manim quantizes waits to video frames, so an event may precede its cue
    # by less than one frame even when scheduled at that exact audio boundary.
    assert all(-1/30<=event['visual_seconds']-event['cue_seconds']<=.12 for event in events)
    with av.open(str(INPUT/'opening.mp4')) as container:
        video=container.streams.video[0]
        duration=container.duration/av.time_base
        assert (video.width,video.height)==(1920,1080) and float(video.average_rate)==30
        assert len(container.streams.audio)==1
        assert abs(duration-visual['duration_seconds'])<.1
    PUBLIC.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(INPUT/'opening.mp4',PUBLIC/'opening.mp4')
    with av.open(str(INPUT/'opening.mp4')) as container:
        stream=container.streams.video[0]
        container.seek(int(20/stream.time_base),stream=stream)
        for frame in container.decode(stream):
            if frame.time>=20:
                frame.to_image().save(PUBLIC/'source.png')
                frame.to_image().save(PUBLIC/'poster.jpg')
                break
    cues=[]
    scenes=[]
    labels={'question':'The question','where':'Where and what','address':'Selecting location 16','waiting':'A value is not a promise','early':'The early-sampling mistake','ready':'Ready to trust the data','timing':'One shared time axis','takeaway':'Where versus when'}
    for beat in visual['beats']:
        for cue in beat['cues']:
            cues.append(cue|{'start_seconds':beat['start_seconds']+cue['start_seconds'],'end_seconds':min(beat['start_seconds']+cue['end_seconds'],duration)})
        objects=[{'id':'processor','kind':'bus','label':'Processor and selected memory row','nodes':['Processor','Memory']}]
        if beat['id']!='question':
            objects.append({'id':'address-value','kind':'text','label':'Address 16 — where to look','text':'16'})
            ready=beat['id'] in ('ready','timing','takeaway')
            objects.append({'id':'data-value','kind':'text','label':'Valid data 42' if ready else 'Old data 19 — not yet valid','text':'42' if ready else '19'})
        if beat['id'] in ('timing','takeaway'):
            objects.append({'id':'shared-timing','kind':'timing','label':'Request, validity and sample on one time axis','signals':[{'name':'Request','values':[0,1,1,1,0,0]},{'name':'Valid','values':[0,0,1,1,0,0]},{'name':'Sample','values':[0,0,0,1,0,0]}]})
        scenes.append({'id':beat['id'],'title':labels[beat['id']],'narration':beat['narration'],'source_refs':['ppage-why-wait'],
                       'objects':objects,'steps':[{'object_ids':[obj['id'] for obj in objects],'caption':labels[beat['id']]}]})
    assert all(0<=c['start_seconds']<c['end_seconds']<=duration for c in cues)
    (PUBLIC/'captions.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f"{i+1}\n{stamp(c['start_seconds'])} --> {stamp(c['end_seconds'])}\n{c['text']}" for i,c in enumerate(cues))+'\n',encoding='utf-8')
    transcript='\n\n'.join(beat['text'] for beat in narration['beats'])
    (PUBLIC/'transcript.txt').write_text(transcript,encoding='utf-8')
    citation={'page_id':'page-why-wait','source_id':'source-why-wait','source_title':'Why wait — original TLDR teaching notes','page_number':1,'quote':narration['beats'][0]['text']}
    manifest={'duration_seconds':duration,'warnings':[],
              'scenes':[{'scene_id':s['id'],'chapter_id':'opening','title':s['title'],'start_seconds':b['start_seconds'],'end_seconds':b['end_seconds'],'source_refs':s['source_refs'],'objects':s['objects']} for s,b in zip(scenes,visual['beats'])],
              'chapters':[{'id':'opening','title':'Where versus when','start_seconds':0,'end_seconds':duration}],
              'cues':cues,'practice':[{'id':'why-wait-predict','scene_id':'question','time_seconds':5.74,
                 'question':'Why should the processor wait before accepting memory data?',
                 'answer':'The data wires can still carry an old value. The receiving side needs the protocol’s valid sampling condition before it accepts the returned data.'}],
              'scope':narration['scope'],'status':'Opening-sequence quality study; full visual lesson remains in progress.',
              'caption_alignment':narration['alignment'],'narration_engine':narration['engine'],'voice':narration['voice'],'model_hashes':narration['model_hashes']}
    (PUBLIC/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    source={'id':'source-why-wait','course':'demo-transport','title':'Why wait — original TLDR teaching notes','kind':'image','status':'ready',
            'pages':[{'id':'page-why-wait','source':'source-why-wait','number':1,'text':transcript,'original_text':transcript,'corrected':False,'image_url':'/sample/showcase/source.png','width':1920,'height':1080,'regions':[]}]}
    lesson={'id':'lesson-why-wait','course':'demo-transport','title':'Why a computer has to wait · opening study',
            'revisions':[{'id':'revision-why-wait','lesson':'lesson-why-wait','number':1,
                          'spec':{'id':'why-wait-opening','title':narration['title'],'purpose':'followup','target_minutes':2,'learning_objectives':['Distinguish the address from the stored value.','Explain why a present value is not necessarily ready to sample.'],'chapters':[{'id':'opening','title':'Where versus when','objective':'Follow one original teaching transaction into its timing diagram.','scenes':scenes}]},
                          'citations':[citation],'video_url':'/sample/showcase/opening.mp4','captions_url':'/sample/showcase/captions.vtt','transcript_url':'/sample/showcase/transcript.txt','poster_url':'/sample/showcase/poster.jpg','manifest':manifest}]}
    typescript="// Generated by examples/showcase/export.py from verified local media.\nimport type { Lesson, Source } from '../types'\n\nexport const openingSource: Source = "+json.dumps(source,ensure_ascii=False,indent=2)+"\n\nexport const openingLesson: Lesson = "+json.dumps(lesson,ensure_ascii=False,indent=2)+"\n"
    (ROOT/'frontend/tldr-frontend/src/data/showcase.ts').write_text(typescript,encoding='utf-8')
    proof={'duration_seconds':duration,'resolution':[1920,1080],'fps':30,'audio_tracks':1,'caption_cues':len(cues),'visual_events':len(events),'maximum_cue_error_seconds':max(abs(event['visual_seconds']-event['cue_seconds']) for event in events),'sentence_alignment':narration['alignment'],'sha256':hashlib.sha256((PUBLIC/'opening.mp4').read_bytes()).hexdigest(),'scope':manifest['status']}
    (INPUT/'export-verification.json').write_text(json.dumps(proof,indent=2))
    print(json.dumps(proof,indent=2))


if __name__=='__main__': main()
