"""Install original local LaTeX samples and render them; never generates with AI."""
from pathlib import Path
import hashlib
import json
import os
import sys
import time

import requests

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'artifacts/math-workspace'
TITLE='Mathematics — LaTeX samples'
NOTES=r'''Original TLDR math examples for checking local typesetting.

Squaring the real number 2 gives 4.
\[y=x^2,\quad x=2\Rightarrow y=4\]

For differentiable functions, the derivative is the limit of the difference quotient.
\[f'(x)=\lim_{h\to0}\frac{f(x+h)-f(x)}{h}\]
In particular, for real x and f(x)=x squared, f prime of x is 2x.
\[\frac{d}{dx}x^2=2x\]

The determinant of the matrix with rows (1,2) and (3,4) is 1 times 4 minus 2 times 3, or -2.
\[A=\begin{bmatrix}1&2\\3&4\end{bmatrix},\quad\det(A)=1\cdot4-2\cdot3=-2\]

These examples are authored notes, not output from a live AI request. Typesetting does not verify other formulas.
'''


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    state_path=OUTPUT/'installed.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {}
    session=requests.Session();session.trust_env=False
    def call(method,path,**kwargs):
        response=session.request(method,'http://127.0.0.1:8765/api/'+path,timeout=30,**kwargs)
        response.raise_for_status()
        return response.json() if response.status_code!=204 else None
    def save():
        temp=state_path.with_suffix('.tmp');temp.write_text(json.dumps(state,indent=2),encoding='utf-8');temp.replace(state_path)
    if 'course_id' not in state:
        course=call('POST','courses/',json={'name':TITLE,'description':'Original local examples: formatted notes, editable flashcards, quiz choices and a short equation video. No AI generation.'})
        state['course_id']=course['id'];save()
    course=call('GET',f'courses/{state["course_id"]}/')
    if course['name']!=TITLE:raise ValueError('Sample course was renamed; refuse to modify it automatically.')
    if 'source_id' not in state:
        source=call('POST','sources/',json={'course':course['id'],'title':'Original LaTeX example notes','text':NOTES})
        state['source_id']=source['id'];save()
    deadline=time.monotonic()+120
    while True:
        source=call('GET',f'sources/{state["source_id"]}/')
        if source['status']=='ready':break
        if source['status']=='error' or time.monotonic()>deadline:raise ValueError('Sample source is not ready. Its saved state is retained.')
        time.sleep(.5)
    page=source['pages'][0]
    if 'study_ids' not in state:
        state['study_ids']=[];save()
    cards=[
        {'kind':'flashcard','title':r"For \(f(x)=x^2\), find \(f'(x)\).",'data':{'answer':r'\[\frac{d}{dx}x^2=2x\] The slope is twice the input, for real x.'}},
        {'kind':'flashcard','title':r'Find \(\det(A)\) for \(A=\begin{bmatrix}1&2\\3&4\end{bmatrix}\).','data':{'answer':r'\[\det(A)=1\cdot4-2\cdot3=-2\]'}},
        {'kind':'quiz','title':r'Which value is \(\det\begin{bmatrix}1&2\\3&4\end{bmatrix}\)?','body':r'Use \(ad-bc\) for a two by two matrix.','data':{'options':[r'\(-2\)',r'\(2\)',r'\(10\)'],'answer':r'\(-2\)','attempts':[]}},
    ]
    for card in cards[len(state['study_ids']):]:
        item=call('POST','study-items/',json={'course':course['id'],'completed':False,**card})
        state['study_ids'].append(item['id']);save()
    # Explicit authored fixture creation queues no provider request. Save/review
    # validation and the actual render job still use the normal local API.
    sys.path.insert(0,str(ROOT/'backend/tldr_backend'));os.environ.setdefault('DJANGO_SETTINGS_MODULE','tldr_backend.settings')
    import django
    django.setup()
    from study.models import Course,Lesson,Revision
    if Course.objects.get(pk=course['id']).name!=TITLE:raise ValueError('The API and authoring process must use the same local database.')
    if 'lesson_id' not in state:
        lesson=Lesson.objects.create(course_id=course['id'],title='LaTeX equation typesetting — short sample')
        state['lesson_id']=lesson.id;save()
    if 'revision_id' not in state:
        spec=json.loads((ROOT/'examples/math.json').read_text(encoding='utf-8'))
        spec['id']='latex-typesetting-sample';spec['title']='LaTeX equation typesetting — short sample'
        scenes=spec['chapters'][0]['scenes'];scenes[0]['source_refs']=[f'p{page["id"]}']
        for identifier,title,tex,narration in [
            ('difference-quotient','A fraction inside a limit',r"f'(x)=\lim_{h\to0}\frac{f(x+h)-f(x)}{h}",'For a differentiable function, the derivative is the limit of a difference quotient. The numerator compares two nearby function values. The denominator is the change in the input. The limit asks what happens as that input change approaches zero. This is notation for the definition, not a numerical simulation.'),
            ('matrix','Rows, brackets and a determinant',r'A=\begin{bmatrix}1&2\\3&4\end{bmatrix},\quad\det(A)=-2','Read the first row as one, two, and the second row as three, four. For this two by two matrix, the determinant is one times four minus two times three. Four minus six is minus two. The brackets and rows are typeset from the stored mathematical notation.'),
        ]:
            scenes.append({'id':identifier,'title':title,'narration':narration,'source_refs':[f'p{page["id"]}'],'objects':[{'id':identifier+'-equation','kind':'equation','label':title,'text':title,'latex':tex}],'steps':[{'object_ids':[identifier+'-equation'],'caption':title}]})
        quote='Squaring the real number 2 gives 4.'
        assert quote in page['text']
        revision=call('POST',f'lessons/{state["lesson_id"]}/revisions/',json={'spec':spec,'citations':[{'page_id':page['id'],'source_id':source['id'],'source_title':source['title'],'page_number':1,'quote':quote}]})
        state['revision_id']=revision['id'];save()
    if 'render_job_id' not in state:
        job=call('POST',f'lessons/{state["lesson_id"]}/render/',json={'revision_id':state['revision_id']})
        state['render_job_id']=job['job']['id'];save()
    last=None;deadline=time.monotonic()+900
    while True:
        job=call('GET',f'jobs/{state["render_job_id"]}/')
        progress=(job['status'],job['progress'])
        if progress!=last:print(json.dumps({'job_id':job['id'],'status':job['status'],'progress':job['progress']}),flush=True);last=progress
        if job['status']=='complete':break
        if job['status'] in {'failed','cancelled','paused'} or time.monotonic()>deadline:raise ValueError('Sample render is not complete. Inspect the existing saved job; do not restart it blindly.')
        time.sleep(1)
    revision=Revision.objects.get(pk=state['revision_id'],lesson__course_id=course['id'])
    state.update(url=f'http://127.0.0.1:5173/?course={course["id"]}&revision={revision.id}',duration_seconds=job['result']['manifest']['duration_seconds'],video_sha256=hashlib.sha256(Path(revision.video.path).read_bytes()).hexdigest())
    save();print(json.dumps(state),flush=True)


if __name__=='__main__':main()
