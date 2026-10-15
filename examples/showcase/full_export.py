"""Assemble, validate, then install the authored lesson in its local course.

Supplied course images are never written to frontend/public. This is an explicit
local fixture importer, not an AI generation path or an executable upload API.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

import av
import imageio_ffmpeg

from full_render import digest,chapter_key
from timing_math import timing_window

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'artifacts/ece224-lesson'
ASSEMBLED=OUTPUT/'assembled'

LESSON_OBJECT_KEYS={'id','kind','label','text','latex','points','shape','nodes','signals','source_ref','overlays','calculation'}


def lesson_context_object(obj,source_ref=None):
    """Strip export metadata while retaining the closed lesson object contract."""
    value={key:obj[key] for key in LESSON_OBJECT_KEYS if key in obj}
    if value['kind']=='source_image' and source_ref:value['source_ref']=source_ref
    return value


def manifest_context_object(obj,asset=None):
    """Preserve explicit provenance and immutable source identity for context."""
    value=dict(obj)
    value['provenance']='original_source' if obj['kind']=='source_image' else obj.get('provenance','conceptual')
    if obj['kind']=='source_image':
        if asset is None:raise ValueError('Source context requires its immutable asset identity.')
        value.update(source_ref=asset['ref'],asset_sha256=asset['sha256'],crop=asset['crop'])
    return value


def context_source_refs(objects,source_ref,authored_notes_ref):
    """Bind conceptual examples to authored notes while retaining the source figure."""
    refs=[source_ref]
    if any(obj['kind']!='source_image' for obj in objects):refs.append(authored_notes_ref)
    return refs


def duration(path):
    with av.open(str(path)) as container:
        stream=container.streams.video[0]
        if (stream.width,stream.height)!=(1920,1080) or float(stream.average_rate)!=30 or len(container.streams.audio)!=1:
            raise ValueError('Unexpected chapter media streams.')
        return container.duration/av.time_base


def stamp(seconds):
    ms=round(seconds*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02}.{ms%1000:03}'


def assemble():
    started=time.perf_counter()
    narration=json.loads((OUTPUT/'audio/narration.json').read_text(encoding='utf-8'))
    opening=json.loads((ROOT/'frontend/tldr-frontend/public/sample/showcase/manifest.json').read_text(encoding='utf-8'))
    original=json.loads((ROOT/'artifacts/showcase/opening/visual-timing.json').read_text(encoding='utf-8'))
    assets=json.loads((OUTPUT/'assets.json').read_text(encoding='utf-8'))
    paths=[ROOT/'artifacts/showcase/opening/opening.mp4']+[OUTPUT/f'{b["id"]}.mp4' for b in narration['beats']]
    opening_proof=json.loads((ROOT/'artifacts/showcase/opening/export-verification.json').read_text())
    if digest(paths[0])!=opening_proof['sha256']:raise ValueError('Opening differs from its reviewed export.')
    for beat,path in zip(narration['beats'],paths[1:]):
        marker=json.loads((OUTPUT/f'complete-{beat["id"]}.json').read_text())
        if marker['key']!=chapter_key(beat,assets) or marker['sha256']!=digest(path):raise ValueError('Chapter is incomplete, stale or changed; render it first.')
    lengths=[duration(path) for path in paths]
    if not 600<=sum(lengths)<=1200:raise ValueError('Actual full lesson must be 10–20 minutes.')
    ASSEMBLED.mkdir(parents=True,exist_ok=True)
    # Fixed short local filenames keep concat parsing independent of user paths.
    for i,path in enumerate(paths):shutil.copyfile(path,ASSEMBLED/f'part-{i:02}.mp4')
    (ASSEMBLED/'concat.txt').write_text('\n'.join(f"file 'part-{i:02}.mp4'" for i in range(len(paths))),encoding='utf-8')
    cues=list(opening['cues']);timeline=[];chapters=[];practice=[];offset=lengths[0]
    for scene,beat in zip(opening['scenes'],original['beats']):
        timeline.append(scene|{'narration':beat['narration'],'original_model':True})
    chapters.append({'id':'opening','title':'Where versus when','start_seconds':0,'end_seconds':offset})
    for b,clip_length in zip(narration['beats'],lengths[1:]):
        timing=json.loads((OUTPUT/f'{b["id"]}-timing.json').read_text())
        if abs(timing['duration_seconds']-clip_length)>.1:raise ValueError('Chapter clock mismatch.')
        for event in timing['events']:
            if abs(event['visual_seconds']-event['cue_seconds'])>1/30+.001:raise ValueError('A visual missed its narration cue.')
        for i,scene in enumerate(timing['scenes']):
            start=scene['sentence_index'];stop=timing['scenes'][i+1]['sentence_index'] if i+1<len(timing['scenes']) else len(b['cues'])
            timeline.append(scene|{'scene_id':scene['id'],'chapter_id':b['id'],'title':scene['label'],
                           'start_seconds':offset+scene['start_seconds'],'end_seconds':offset+scene['end_seconds'],
                           'narration':' '.join(c['text'] for c in b['cues'][start:stop]),'original_model':False})
        for cue in b['cues']:
            cues.append(cue|{'start_seconds':offset+cue['start_seconds'],'end_seconds':offset+cue['end_seconds']})
        for i,point in enumerate(b.get('practice',[])):
            t=b['cues'][point['after_sentence']]['end_seconds']+.5
            selected=next(s for s in timing['scenes'] if s['start_seconds']<=t<s['end_seconds'])
            practice.append({'id':f'{b["id"]}-practice-{i}','scene_id':selected['id'],'time_seconds':offset+t,'question':point['question'],'answer':point['answer']})
        chapters.append({'id':b['id'],'title':b['title'],'start_seconds':offset,'end_seconds':offset+clip_length})
        offset+=clip_length
    if any(not 0<=c['start_seconds']<c['end_seconds']<=offset for c in cues):raise ValueError('Invalid caption interval.')
    for left,right in zip(timeline,timeline[1:]):
        if abs(left['end_seconds']-right['start_seconds'])>.05:raise ValueError('Scene gap or overlap.')
    (ASSEMBLED/'captions.vtt').write_text('WEBVTT\n\n'+'\n\n'.join(f'{i+1}\n{stamp(c["start_seconds"])} --> {stamp(c["end_seconds"])}\n{c["text"]}' for i,c in enumerate(cues))+'\n',encoding='utf-8')
    ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
    with (OUTPUT/'assemble.log').open('w',encoding='utf-8') as log:
        subprocess.run([ffmpeg,'-y','-f','concat','-safe','1','-i','concat.txt','-i','captions.vtt',
                        '-map','0:v:0','-map','0:a:0','-map','1:0','-c:v','copy','-c:a','aac','-c:s','mov_text',
                        '-metadata:s:s:0','language=eng','-movflags','+faststart','lesson.pending.mp4'],cwd=ASSEMBLED,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=1200)
    actual=duration(ASSEMBLED/'lesson.pending.mp4')
    if abs(actual-offset)>.2:raise ValueError('Full concatenation changed the measured timeline.')
    with av.open(str(ASSEMBLED/'lesson.pending.mp4')) as container:
        if len(container.streams.subtitles)!=1:raise ValueError('Missing embedded captions.')
    (ASSEMBLED/'lesson.pending.mp4').replace(ASSEMBLED/'lesson.mp4')
    with av.open(str(ASSEMBLED/'lesson.mp4')) as container:
        stream=container.streams.video[0];container.seek(int(84/stream.time_base),stream=stream)
        for frame in container.decode(stream):
            if frame.time>=84:frame.to_image().save(ASSEMBLED/'poster.jpg');break
    (ASSEMBLED/'transcript.txt').write_text('\n\n'.join(s['narration'] for s in timeline),encoding='utf-8')
    result={'duration_seconds':actual,'chapters':chapters,'scenes':timeline,'cues':cues,'practice':practice,
            'scope':narration['scope'],'caption_alignment':narration['alignment'],'narration_engine':narration['engine'],
            'voice':narration['voice'],'warnings':[],'assembly_wall_seconds':time.perf_counter()-started,
            'video_sha256':digest(ASSEMBLED/'lesson.mp4')}
    (ASSEMBLED/'manifest.preinstall.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    return result,assets


def install(manifest,assets):
    sys.path.insert(0,str(ROOT/'backend/tldr_backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','tldr_backend.settings')
    import django
    django.setup()
    from django.conf import settings
    from django.db import transaction
    from django.core.files.base import ContentFile
    from study.models import Course,Source,Lesson,Revision,Job,StudyItem
    from study.ingestion import make_page
    from study.retrieval import bind_source_assets,resolve_revision_assets
    from study.rendering.schema import validate_lesson
    from PIL import Image
    course=Course.objects.get(pk=assets['course_id'])
    install_fingerprint=hashlib.sha256(json.dumps({'video':manifest['video_sha256'],
        'script':digest(Path(__file__).with_name('full_lesson.json')),'exporter':digest(__file__),
        'assets':assets},sort_keys=True).encode()).hexdigest()
    state_path=OUTPUT/'installed.json'
    previous={}
    if state_path.exists():
        previous=json.loads(state_path.read_text())
        revision=Revision.objects.filter(pk=previous['revision_id'],lesson__course=course).first()
        if previous.get('install_fingerprint')==install_fingerprint and revision and revision.video and Path(revision.video.path).is_file() and digest(revision.video.path)==manifest['video_sha256']:
            print(json.dumps(previous|{'cached_install':True}));return
    text=(ASSEMBLED/'transcript.txt').read_text(encoding='utf-8')
    notes_hash=hashlib.sha256(text.encode()).hexdigest()
    notes,created=Source.objects.get_or_create(course=course,title='TLDR — authored bus-read teaching notes',digest=notes_hash,
                                              defaults={'kind':'text','status':'ready'})
    if created:
        notes.original.save('authored-notes.txt',ContentFile(text.encode()),save=True)
        with Image.open(ROOT/'frontend/tldr-frontend/public/sample/showcase/source.png') as image:make_page(notes,1,text,image)
    page=notes.pages.get(number=1);notes_ref=f'p{page.id}'
    first_quote=text.split('.')[0]+'.'
    citations=assets['citations']+[{'page_id':page.id,'source_id':notes.id,'source_title':notes.title,'page_number':1,'quote':first_quote,'visual':False}]
    citations=bind_source_assets(citations,course.id)
    chapters=[]
    for chapter in manifest['chapters']:
        scenes=[]
        for entry in [s for s in manifest['scenes'] if s['chapter_id']==chapter['id']]:
            raw_objects=None;page_asset=None
            if entry.get('original_model'):
                objects=entry['objects'];refs=[notes_ref]
            elif entry.get('page'):
                page_asset=assets['pages'][str(entry['page'])]
                raw_objects=entry.get('objects') or [{'id':f'diagram-{entry["page"]}','kind':'source_image','label':f'Original Part Va diagram, page {entry["page"]}'}]
                refs=context_source_refs(raw_objects,page_asset['ref'],notes_ref)
                objects=[lesson_context_object(obj,page_asset['ref']) for obj in raw_objects]
            else:
                refs=[notes_ref]
                objects=[{'id':'receiving-window' if chapter['id']=='window' else 'prediction','kind':'equation','label':entry['title'],'text':entry['title']}]
            scene={'id':entry['scene_id'],'title':entry['title'],'narration':entry['narration'],'source_refs':refs,'objects':objects,
                   'steps':[{'object_ids':[o['id'] for o in objects],'caption':entry['title'][:180]}]}
            scenes.append(scene);entry['source_refs']=refs
            entry['objects']=[]
            for index,obj in enumerate(objects):
                original_obj=raw_objects[index] if raw_objects is not None else obj
                value=manifest_context_object(original_obj,page_asset if original_obj['kind']=='source_image' else None)
                if obj['kind']=='source_image':
                    if not entry.get('page'):
                        value['provenance']='original_source'
                elif chapter['id']=='window' and entry['sentence_index']>=5 or chapter['id']=='predict' and 5<=entry['sentence_index']<9:
                    index=entry['sentence_index']
                    a,b=(7,11.5) if chapter['id']=='predict' else (6,12) if index<=9 else (8.5,12) if index<=11 else (6,10.5)
                    value.update(provenance='verified_tool',calculation_result=timing_window(10,2,1,a,b))
                entry['objects'].append(value)
        chapters.append({'id':chapter['id'],'title':chapter['title'],'scenes':scenes})
    spec=validate_lesson({'id':'ece224-where-who-when','title':'A bus read: where, who, and when','target_minutes':15,'purpose':'lesson',
                         'learning_objectives':['Identify the selected address, permitted driver and valid sampling condition.','Read the original synchronous and fully interlocked diagrams.','Check setup and hold as separate receiving-side conditions.'],'chapters':chapters})
    with transaction.atomic():
        lesson=Lesson.objects.filter(pk=previous.get('lesson_id'),course=course).first()
        if not lesson:lesson=Lesson.objects.create(course=course,title=spec['title'])
        revision=Revision.objects.create(lesson=lesson,number=lesson.revisions.count()+1,spec=spec,citations=citations)
        resolved=resolve_revision_assets(revision)  # same immutable source boundary as general rendering
        for asset in assets['pages'].values():
            if resolved[asset['ref']]['sha256']!=asset['sha256']:
                raise ValueError('A rendered source crop differs from its revision-bound original.')
        # Use the existing revision render tree so normal lesson/course deletion
        # also removes this authored movie, manifest and related media.
        directory=settings.MEDIA_ROOT/'renders'/str(revision.id)/'authored';directory.mkdir(parents=True,exist_ok=True)
        for field,filename in [('video','lesson.mp4'),('captions','captions.vtt'),('transcript','transcript.txt'),('poster','poster.jpg')]:
            target=directory/filename;shutil.copyfile(ASSEMBLED/filename,target)
            setattr(revision,field,target.relative_to(settings.MEDIA_ROOT).as_posix())
        revision.save()
        (directory/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
        Job.objects.create(course=course,lesson=lesson,kind='render',status='complete',progress=100,payload={'revision_id':revision.id,'authored_import':True},result={'revision_id':revision.id,'manifest':manifest})
        for point in manifest['practice']:
            StudyItem.objects.get_or_create(course=course,lesson=lesson,kind='flashcard',title=point['question'],defaults={'data':{'answer':point['answer'],'lesson_time_seconds':point['time_seconds']}})
    result={'course_id':course.id,'lesson_id':lesson.id,'revision_id':revision.id,'duration_seconds':manifest['duration_seconds'],
            'video_sha256':manifest['video_sha256'],'install_fingerprint':install_fingerprint,'url':f'http://127.0.0.1:5173/?course={course.id}&revision={revision.id}',
            'practice_points':len(manifest['practice']),'scenes':len(manifest['scenes'])}
    state_path.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)


if __name__=='__main__':install(*assemble())
