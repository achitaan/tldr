import io
import json
import math
import mimetypes
import time
import zipfile
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.exceptions import APIException
from rest_framework.renderers import BaseRenderer, JSONRenderer
from .models import Course, Source, Page, Region, Conversation, Message, Lesson, Revision, Job, StudyItem, RuntimeState
from .serializers import CourseSerializer, SourceSerializer, PageSerializer, RegionSerializer, ConversationSerializer, MessageSerializer, LessonSerializer, RevisionSerializer, JobSerializer, StudyItemSerializer
from .jobs import TERMINAL
from .provider import configuration
from .retrieval import index_page


class EventStreamRenderer(BaseRenderer):
    """Accept the browser's SSE header before the streaming action runs.

    Successful streams use StreamingHttpResponse directly. DRF exceptions that
    occur before streaming retain their HTTP status and an SSE error payload.
    """
    media_type='text/event-stream'
    format='event-stream'

    def render(self,data,accepted_media_type=None,renderer_context=None):
        return ('event: error\ndata: '+json.dumps(data,ensure_ascii=False)+'\n\n').encode('utf-8')


def integer(value,label='id'):
    try:
        if isinstance(value,bool): raise ValueError()
        result = int(value)
        if result<=0: raise ValueError()
        return result
    except (ValueError,TypeError,OverflowError):
        raise serializers.ValidationError({label:'A positive integer is required.'})

def bounded(value,label,limit=12000):
    if not isinstance(value,str) or not value.strip() or len(value)>limit:
        raise serializers.ValidationError({label:f'Provide text between 1 and {limit} characters.'})
    return value.strip()

def region_ids(data,course):
    values = data.get('region_ids',[])
    if not isinstance(values,list) or len(values)>8:
        raise serializers.ValidationError('Select at most eight regions.')
    values = list({integer(v,'region_ids') for v in values})
    if Region.objects.filter(pk__in=values,page__source__course=course).count()!=len(values):
        raise serializers.ValidationError('Selected regions must belong to this course.')
    return values

def target_minutes(data):
    purpose=data.get('purpose','lesson')
    if purpose not in ('lesson','followup'): raise serializers.ValidationError('Invalid lesson purpose.')
    value=data.get('target_minutes',2 if purpose=='followup' else 15)
    allowed=(1,2,3) if purpose=='followup' else (10,15,20)
    if isinstance(value,bool) or value not in allowed: raise serializers.ValidationError(f'Choose a target from {allowed} minutes.')
    return value

def validated_context(data,course):
    context = data.get('context',{})
    if not isinstance(context,dict) or len(json.dumps(context))>6000:
        raise serializers.ValidationError('Invalid lesson context.')
    if not context: return {}
    allowed = {'revision_id','scene_id','time_seconds','object_ids'}
    if set(context)-allowed: raise serializers.ValidationError('Unknown context field.')
    revision = get_object_or_404(Revision,pk=integer(context.get('revision_id'),'revision_id'),lesson__course=course)
    scene_id = context.get('scene_id')
    scene = next((s for ch in revision.spec.get('chapters',[]) for s in ch.get('scenes',[]) if s.get('id')==scene_id),None)
    if not scene: raise serializers.ValidationError('Scene does not belong to this lesson revision.')
    objects = context.get('object_ids',[])
    if not isinstance(objects,list) or any(not isinstance(x,str) for x in objects) or not set(objects).issubset({o['id'] for o in scene.get('objects',[])}):
        raise serializers.ValidationError('Selected objects do not belong to this scene.')
    position = context.get('time_seconds',0)
    if isinstance(position,bool) or not isinstance(position,(int,float)) or not math.isfinite(position) or not 0<=position<=7200:
        raise serializers.ValidationError('Invalid playback position.')
    position=math.floor(position*1000+.5)/1000
    timeline=(RevisionSerializer().get_manifest(revision) or {}).get('scenes',[])
    if timeline:
        current=next((entry for entry in timeline if entry['scene_id']==scene_id),None)
        tail=.25 if current==timeline[-1] else 0
        if not current or not math.floor(current['start_seconds']*1000+.5)/1000<=position<math.floor(current['end_seconds']*1000+.5)/1000+tail:
            raise serializers.ValidationError('Playback position does not belong to the selected scene.')
    return {'revision_id':revision.id,'scene_id':scene_id,'time_seconds':position,'object_ids':objects}

def remove_source_files(source):
    from .retrieval import ensure_fts
    from django.db import connection
    ensure_fts()
    with connection.cursor() as cursor:
        for page_id in source.pages.values_list('id',flat=True):
            cursor.execute('DELETE FROM study_page_fts WHERE rowid=%s',[page_id])
    source.original.delete(save=False)
    for page in source.pages.all(): page.image.delete(save=False)

class ActiveJobConflict(APIException):
    status_code=409
    default_detail='Work has been cancelled. Wait for the active operation to finish, then delete again. If the worker stopped, restart it first.'

def await_idle(jobs):
    jobs.exclude(status__in=TERMINAL).update(status='cancelled',error='Cancelled before deletion.')
    deadline=time.monotonic()+2
    while jobs.filter(worker_active=True).exists():
        if time.monotonic()>=deadline: raise ActiveJobConflict()
        time.sleep(0.1)

def remove_lesson_files(lesson):
    for revision in lesson.revisions.all():
        for field in ('video','captions','transcript','poster'):
            getattr(revision,field).delete(save=False)
    import shutil
    for revision in lesson.revisions.all():
        root=(settings.MEDIA_ROOT/'renders'/str(revision.id)).resolve()
        if root.is_relative_to(settings.MEDIA_ROOT.resolve()): shutil.rmtree(root,ignore_errors=True)

def remove_course(course):
    await_idle(course.jobs.all())
    for source in course.sources.all(): remove_source_files(source)
    for lesson in course.lessons.all(): remove_lesson_files(lesson)
    import shutil
    cache=(settings.DATA_ROOT/'render_cache'/str(course.id)).resolve()
    if cache.is_relative_to(settings.DATA_ROOT.resolve()): shutil.rmtree(cache,ignore_errors=True)
    course.delete()

class ScopedViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        qs = super().get_queryset()
        value = self.request.query_params.get('course')
        if value is not None:
            qs = qs.filter(course_id=integer(value,'course'))
        elif self.action=='list':
            raise serializers.ValidationError({'course':'Choose a course.'})
        return qs

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all().order_by('id')
    serializer_class = CourseSerializer
    http_method_names = ['get','post','patch','delete','head','options']
    def perform_destroy(self,instance): remove_course(instance)
    @action(detail=True,methods=['post'],url_path='teaching-plan/validate')
    def validate_teaching_plan(self,request,pk=None):
        from .rendering import validate_lesson
        from .teaching_plan import TeachingPlanShapeError, teaching_plan_report, validate_teaching_plan_shape
        course=self.get_object()
        if not isinstance(request.data,dict):
            raise serializers.ValidationError({'request':'Expected a JSON object.'})
        try:
            request_size=len(json.dumps(request.data,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
        except (TypeError,ValueError,OverflowError,RecursionError):
            raise serializers.ValidationError({'request':'Request must contain JSON data.'})
        if request_size>4*1024*1024:
            raise serializers.ValidationError({'request':'Request must be at most 4 MiB.'})
        fields=set(request.data)
        if fields=={'revision_id'}:
            revision_id=request.data['revision_id']
            if isinstance(revision_id,bool) or not isinstance(revision_id,int) or revision_id<=0:
                raise serializers.ValidationError({'revision_id':'A positive integer is required.'})
            revision=get_object_or_404(Revision,pk=revision_id,lesson__course=course)
            spec=revision.spec
            plan=revision.teaching_plan
            manifest=RevisionSerializer().get_manifest(revision)
            media_status='saved_revision'
        elif fields=={'spec','teaching_plan'}:
            try:
                spec=validate_lesson(request.data['spec'])
            except ValueError as exc:
                raise serializers.ValidationError({'spec':str(exc)})
            plan=request.data['teaching_plan']
            revision=None
            manifest=None
            media_status='draft_not_rendered'
        else:
            raise serializers.ValidationError({'request':'Provide exactly revision_id, or spec with teaching_plan.'})
        try:
            plan=validate_teaching_plan_shape(plan) if plan is not None else None
        except TeachingPlanShapeError as exc:
            raise serializers.ValidationError({'teaching_plan':exc.errors})
        return Response(teaching_plan_report(spec,plan,course.id,manifest,media_status=media_status))
    @action(detail=True,methods=['get'])
    def export(self,request,pk=None):
        course=self.get_object()
        data={'course':CourseSerializer(course).data,'sources':SourceSerializer(course.sources.all(),many=True).data,'conversations':[], 'lessons':LessonSerializer(course.lessons.all(),many=True).data,'study_items':StudyItemSerializer(course.study_items.all(),many=True).data}
        for conversation in course.conversations.all():
            data['conversations'].append(ConversationSerializer(conversation).data | {'messages':MessageSerializer(conversation.messages.all(),many=True).data})
        import tempfile
        output=tempfile.SpooledTemporaryFile(max_size=5*1024*1024)
        with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('course.json',json.dumps(data,ensure_ascii=False,indent=2))
            for source in course.sources.all():
                if source.original: archive.write(source.original.path,'originals/'+str(source.id)+'/'+Path(source.original.name).name)
                for page in source.pages.all():
                    if page.image: archive.write(page.image.path,'pages/'+str(page.id)+'.png')
            for lesson in course.lessons.all():
                for revision in lesson.revisions.all():
                    for field in ('video','captions','transcript','poster'):
                        asset=getattr(revision,field)
                        if asset and Path(asset.path).is_file(): archive.write(asset.path,f'lessons/{lesson.id}/{revision.number}/'+Path(asset.name).name)
        output.seek(0)
        return FileResponse(output,as_attachment=True,filename=f'course-{course.id}.zip')

class SourceViewSet(ScopedViewSet):
    queryset=Source.objects.all().order_by('id')
    serializer_class=SourceSerializer
    http_method_names=['get','post','delete','head','options']
    def create(self,request):
        course=get_object_or_404(Course,pk=integer(request.data.get('course'),'course'))
        upload=request.FILES.get('file')
        if 'url' in request.data:
            if upload or 'text' in request.data:
                raise serializers.ValidationError('Import a URL, a file, or text separately.')
            from .web_ingestion import validate_url
            try:
                url=validate_url(request.data.get('url'))
            except ValueError as exc:
                raise serializers.ValidationError({'url':str(exc)})
            title=bounded(request.data.get('title') or url[:240],'title',240)
            with transaction.atomic():
                source=Source.objects.create(course=course,title=title,kind='web',source_url=url)
                job=Job.objects.create(course=course,kind='ingest',payload={'source_id':source.id})
            return Response(SourceSerializer(source).data | {'job':JobSerializer(job).data},status=201)
        if upload:
            if upload.size>20*1024*1024: raise serializers.ValidationError('File exceeds 20 MB.')
            suffix=Path(upload.name).suffix.lower()
            kind={'.pdf':'pdf','.png':'image','.jpg':'image','.jpeg':'image','.webp':'image','.txt':'text','.md':'text'}.get(suffix)
            if not kind: raise serializers.ValidationError('Use PDF, PNG, JPEG, WebP, TXT or Markdown.')
            filename='source'+suffix
            title=request.data.get('title') or Path(upload.name).stem
        else:
            text=bounded(request.data.get('text'),'text',500000)
            upload=ContentFile(text.encode('utf-8'))
            kind,filename,title='text','source.txt',request.data.get('title') or 'Pasted notes'
        title=bounded(title,'title',240)
        source=Source(course=course,title=title,kind=kind)
        source.original.save(filename,upload,save=False)
        try:
            with transaction.atomic():
                source.save()
                job=Job.objects.create(course=course,kind='ingest',payload={'source_id':source.id})
        except Exception:
            source.original.delete(save=False)
            raise
        return Response(SourceSerializer(source).data | {'job':JobSerializer(job).data},status=201)
    def perform_destroy(self,instance):
        await_idle(Job.objects.filter(course=instance.course,payload__source_id=instance.id))
        remove_source_files(instance)
        instance.delete()

class PageViewSet(viewsets.GenericViewSet):
    queryset=Page.objects.select_related('source').all()
    serializer_class=PageSerializer
    def retrieve(self,request,pk=None): return Response(PageSerializer(self.get_object()).data)
    def partial_update(self,request,pk=None):
        page=self.get_object()
        serializer=PageSerializer(page,data=request.data,partial=True)
        serializer.is_valid(raise_exception=True)
        page=serializer.save(corrected=True)
        index_page(page)
        return Response(PageSerializer(page).data)

class RegionViewSet(viewsets.ModelViewSet):
    queryset=Region.objects.all().order_by('id')
    serializer_class=RegionSerializer
    http_method_names=['get','post','patch','delete','head','options']
    def get_queryset(self):
        qs=super().get_queryset()
        value=self.request.query_params.get('course')
        if value is not None: return qs.filter(page__source__course_id=integer(value,'course'))
        if self.action=='list': raise serializers.ValidationError({'course':'Choose a course.'})
        return qs

class ConversationViewSet(ScopedViewSet):
    queryset=Conversation.objects.all().order_by('id')
    serializer_class=ConversationSerializer
    http_method_names=['get','post','patch','delete','head','options']
    @action(detail=True,methods=['get','post'])
    def messages(self,request,pk=None):
        conversation=self.get_object()
        if request.method=='GET': return Response(MessageSerializer(conversation.messages.all(),many=True).data)
        content=bounded(request.data.get('content'),'content')
        regions=region_ids(request.data,conversation.course)
        context=validated_context(request.data,conversation.course)
        if Job.objects.filter(course=conversation.course,kind='chat',status__in=['queued','running'],payload__conversation_id=conversation.id).exists():
            return Response({'detail':'Wait for or cancel the active reply.'},status=409)
        with transaction.atomic():
            user=Message.objects.create(conversation=conversation,role='user',content=content,context=context)
            message=Message.objects.create(conversation=conversation,role='assistant',status='pending',context=context)
            job=Job.objects.create(course=conversation.course,kind='chat',payload={'conversation_id':conversation.id,'message_id':message.id,'user_message_id':user.id,'content':content,'context':context,'region_ids':regions})
        return Response({'message':MessageSerializer(user).data,'job':JobSerializer(job).data},status=202)
    @action(detail=True,methods=['get'],renderer_classes=[JSONRenderer,EventStreamRenderer])
    def stream(self,request,pk=None):
        conversation=self.get_object()
        job=get_object_or_404(Job,pk=integer(request.query_params.get('job'),'job'),course=conversation.course,kind='chat',payload__conversation_id=conversation.id)
        def event(name,data): return f'event: {name}\ndata: {json.dumps(data)}\n\n'
        def events():
            previous=None
            for _ in range(180):
                try: job.refresh_from_db()
                except Job.DoesNotExist:
                    yield event('error',{'detail':'Job was deleted.'}); return
                signature=(job.status,job.progress,job.error)
                if signature!=previous:
                    yield event('status',JobSerializer(job).data)
                    previous=signature
                if job.status in TERMINAL:
                    if job.status=='complete':
                        message=Message.objects.filter(pk=job.result.get('message_id'),conversation=conversation).first()
                        if message: yield event('message',MessageSerializer(message).data)
                    else: yield event('error',{'detail':job.error or job.status,'status':job.status})
                    yield event('done',{'status':job.status}); return
                yield ': heartbeat\n\n'
                time.sleep(1)
            yield event('reconnect',{'job_id':job.id})
        response=StreamingHttpResponse(events(),content_type='text/event-stream')
        response['X-Accel-Buffering']='no'
        return response
    def perform_destroy(self,instance):
        jobs=Job.objects.filter(course=instance.course,payload__conversation_id=instance.id)
        await_idle(jobs)
        jobs.delete()
        instance.delete()

class LessonViewSet(ScopedViewSet):
    queryset=Lesson.objects.all().order_by('id')
    serializer_class=LessonSerializer
    http_method_names=['get','post','patch','delete','head','options']
    def create(self,request):
        serializer=self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prompt=bounded(request.data.get('prompt'),'prompt')
        regions=region_ids(request.data,serializer.validated_data['course'])
        context=validated_context(request.data,serializer.validated_data['course'])
        purpose=request.data.get('purpose','lesson')
        minutes=target_minutes(request.data)
        if purpose=='followup' and not context:
            raise serializers.ValidationError('A follow-up clip requires a selected lesson moment.')
        with transaction.atomic():
            lesson=serializer.save()
            job=Job.objects.create(course=lesson.course,lesson=lesson,kind='lesson',payload={'prompt':prompt,'region_ids':regions,'target_minutes':minutes,'purpose':purpose,'context':context})
        return Response(LessonSerializer(lesson).data | {'job':JobSerializer(job).data},status=201)
    @action(detail=True,methods=['get','post'])
    def revisions(self,request,pk=None):
        lesson=self.get_object()
        if request.method=='GET': return Response(RevisionSerializer(lesson.revisions.all(),many=True).data)
        if 'spec' not in request.data and request.data.get('teaching_plan') is not None:
            raise serializers.ValidationError({'teaching_plan':'A teaching plan can only be saved with a storyboard spec.'})
        if 'spec' in request.data:
            from .rendering import validate_lesson
            from .retrieval import validate_citations, bind_source_assets
            from .teaching_plan import TeachingPlanShapeError, teaching_plan_report, validate_teaching_plan_shape
            teaching_plan=request.data.get('teaching_plan')
            if teaching_plan is not None:
                try:
                    teaching_plan=validate_teaching_plan_shape(teaching_plan)
                except TeachingPlanShapeError as exc:
                    raise serializers.ValidationError({'teaching_plan':exc.errors})
            try:
                spec=validate_lesson(request.data['spec'])
                citations=request.data.get('citations',[])
                if not isinstance(citations,list) or len(citations)>30: raise ValueError('Invalid citations.')
                evidence=[]
                for cite in citations:
                    if not isinstance(cite,dict): raise ValueError('Invalid citation.')
                    page=get_object_or_404(Page,pk=integer(cite.get('page_id')),source__course=lesson.course)
                    region=get_object_or_404(Region,pk=integer(cite['region_id']),page=page) if cite.get('region_id') else None
                    evidence.append({'page_id':page.id,'source_id':page.source_id,'source_title':page.source.title,'page_number':page.number,'text':region.text if region else page.text,**({'region_id':region.id,'image_supplied':bool(page.image)} if region else {})})
                citations=validate_citations(citations,evidence)
                if not citations: raise ValueError('Keep at least one supporting citation.')
                citations=bind_source_assets(citations,lesson.course_id)
                refs={f"r{c['region_id']}" if c.get('region_id') else f"p{c['page_id']}" for c in citations}
                if any(not s['source_refs'] or not set(s['source_refs']).issubset(refs) for ch in spec['chapters'] for s in ch['scenes']): raise ValueError('Scene source references must match citations.')
            except ValueError as exc:
                raise serializers.ValidationError(str(exc))
            if teaching_plan is not None:
                report=teaching_plan_report(spec,teaching_plan,lesson.course_id)
                errors=[issue for issue in report['issues'] if issue['severity']=='error']
                if errors:
                    raise serializers.ValidationError({'teaching_plan':errors})
            with transaction.atomic():
                revision=Revision.objects.create(lesson=lesson,number=lesson.revisions.count()+1,spec=spec,citations=citations,teaching_plan=teaching_plan)
            return Response(RevisionSerializer(revision).data,status=201)
        prompt=bounded(request.data.get('prompt'),'prompt')
        regions=region_ids(request.data,lesson.course)
        if lesson.jobs.filter(kind='lesson',status__in=['queued','running']).exists(): return Response({'detail':'A revision is already being generated.'},status=409)
        context=validated_context(request.data,lesson.course)
        purpose=request.data.get('purpose','lesson')
        minutes=target_minutes(request.data)
        if purpose=='followup':
            raise serializers.ValidationError('Create a separate lesson for a follow-up clip.')
        job=Job.objects.create(course=lesson.course,lesson=lesson,kind='lesson',payload={'prompt':prompt,'region_ids':regions,'target_minutes':minutes,'purpose':purpose,'context':context})
        return Response({'job':JobSerializer(job).data},status=202)
    @action(detail=True,methods=['post'])
    def render(self,request,pk=None):
        lesson=self.get_object()
        revision=get_object_or_404(Revision,pk=integer(request.data.get('revision_id'),'revision_id'),lesson=lesson)
        existing=lesson.jobs.filter(kind='render',status__in=['queued','running'],payload__revision_id=revision.id).first()
        job=existing or Job.objects.create(course=lesson.course,lesson=lesson,kind='render',payload={'revision_id':revision.id})
        return Response({'job':JobSerializer(job).data},status=202)
    def perform_destroy(self,instance):
        await_idle(instance.jobs.all())
        remove_lesson_files(instance)
        instance.delete()

class JobViewSet(ScopedViewSet):
    queryset=Job.objects.all()
    serializer_class=JobSerializer
    http_method_names=['get','post','head','options']
    def create(self,request): return Response({'detail':'Create jobs through a source, conversation or lesson.'},status=405)
    @action(detail=True,methods=['post'])
    def cancel(self,request,pk=None):
        job=self.get_object()
        if job.status not in {'complete','failed','cancelled'}:
            job.status='cancelled'; job.error='Cancelled by you.'; job.save(update_fields=['status','error','updated_at'])
            if job.kind=='chat': Message.objects.filter(pk=job.payload.get('message_id')).update(status='error',content='Cancelled by you.')
            if job.kind=='ingest': Source.objects.filter(pk=job.payload.get('source_id')).update(status='error',error='Cancelled by you.')
        return Response(JobSerializer(job).data)
    @action(detail=True,methods=['post'])
    def retry(self,request,pk=None):
        job=self.get_object()
        if job.status not in {'failed','paused'}: return Response({'detail':'Only failed or paused jobs can be retried.'},status=409)
        if job.worker_active: return Response({'detail':'The previous operation is still stopping.'},status=409)
        if job.kind in {'chat','lesson'} and not configuration()['generation_enabled']:
            return Response({'detail':'Resolve generation configuration or quota pause before retrying.'},status=409)
        job.status='queued';job.error='';job.progress=0;job.save(update_fields=['status','error','progress','updated_at'])
        if job.kind=='chat': Message.objects.filter(pk=job.payload.get('message_id')).update(status='pending',content='')
        if job.kind=='ingest': Source.objects.filter(pk=job.payload.get('source_id')).update(status='queued',error='')
        return Response(JobSerializer(job).data)

class StudyItemViewSet(ScopedViewSet):
    queryset=StudyItem.objects.all().order_by('id')
    serializer_class=StudyItemSerializer
    http_method_names=['get','post','patch','delete','head','options']

@api_view(['GET'])
def status(request):
    from .ingestion import ocr_available
    from . import provider
    import os
    data=provider.configuration()
    state=RuntimeState.objects.filter(key='worker').first()
    heartbeat=state.value.get('heartbeat') if state else None
    alive=False
    if heartbeat:
        from django.utils.dateparse import parse_datetime
        timestamp=parse_datetime(heartbeat)
        alive=bool(timestamp and (timezone.now()-timestamp).total_seconds()<15)
    data.update({'ocr_available':ocr_available(),'embedding_enabled':os.getenv('TLDR_OLLAMA_EMBEDDINGS')=='1','embedding_model':'embeddinggemma','embedding_status':getattr(RuntimeState.objects.filter(key='embedding').first(),'value',{'status':'disabled'}),'worker':{'running':alive,'heartbeat':heartbeat}})
    try:
        from .rendering import dependency_status
        data['rendering']=dependency_status()
    except ImportError:
        data['rendering']={'available':False,'detail':'Renderer dependencies unavailable.'}
    return Response(data)

@api_view(['POST'])
def resume(request):
    RuntimeState.objects.update_or_create(key='quota',defaults={'value':{'paused':False}})
    return Response(configuration())

@api_view(['DELETE'])
def delete_data(request):
    if request.data.get('confirm')!='DELETE ALL LOCAL DATA': return Response({'detail':'Explicit deletion confirmation is required.'},status=400)
    await_idle(Job.objects.all())
    for course in Course.objects.all(): remove_course(course)
    from django.db import connection
    from .retrieval import ensure_fts
    ensure_fts()
    with connection.cursor() as cursor: cursor.execute('DELETE FROM study_page_fts')
    import shutil
    cache=(settings.DATA_ROOT/'render_cache').resolve()
    if cache.is_relative_to(settings.DATA_ROOT.resolve()): shutil.rmtree(cache,ignore_errors=True)
    return Response(status=204)

def serve_media(request,path):
    target=(settings.MEDIA_ROOT/path).resolve()
    if not target.is_relative_to(settings.MEDIA_ROOT.resolve()) or not target.is_file():
        return HttpResponse(status=404)
    # Never render uploaded originals as active browser content.
    content_type=mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
    size=target.stat().st_size
    byte_range=request.headers.get('Range')
    if byte_range:
        import re
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',byte_range)
        try:
            if not match or not any(match.groups()): raise ValueError()
            first,last=match.groups()
            start=int(first) if first else max(0,size-int(last))
            end=min(int(last),size-1) if first and last else size-1
            if start<0 or start>=size or end<start: raise ValueError()
        except (ValueError,OverflowError):
            response=HttpResponse(status=416)
            response['Content-Range']=f'bytes */{size}'
            return response
        def chunks():
            with open(target,'rb') as handle:
                handle.seek(start)
                remaining=end-start+1
                while remaining:
                    block=handle.read(min(65536,remaining))
                    if not block: break
                    remaining-=len(block)
                    yield block
        response=StreamingHttpResponse(chunks(),status=206,content_type=content_type)
        response['Content-Range']=f'bytes {start}-{end}/{size}'
        response['Content-Length']=str(end-start+1)
    else:
        response=FileResponse(open(target,'rb'),content_type=content_type)
    response['Accept-Ranges']='bytes'
    if path.startswith('originals/'):
        response['Content-Disposition']='attachment; filename="source'+target.suffix+'"'
    response['Content-Security-Policy']="default-src 'none'; sandbox"
    return response
