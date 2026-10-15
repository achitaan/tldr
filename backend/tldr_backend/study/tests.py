import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from .models import Course, Source, Page, Region, Conversation, Message, Lesson, Revision, Job, RuntimeState, StudyItem
from .jobs import claim,run_job
from .provider import generate_json,configuration,QuotaPaused,GenerationUnavailable
from .retrieval import retrieve,index_page,validate_citations,ensure_fts,bind_source_assets,resolve_revision_assets

ACKS={'GEMINI_API_KEY':'test-secret','TLDR_FREE_PROJECT_ACK':'I_CONFIRM_BILLING_IS_DISABLED','TLDR_DATA_TERMS_ACK':'I_ACCEPT_GOOGLE_FREE_TIER_DATA_TERMS','TLDR_GEMINI_MODEL':'gemini-3.8-flash','TLDR_OLLAMA_EMBEDDINGS':'0'}

class WorkspaceTests(TestCase):
    def test_worker_survives_heartbeat_database_contention(self):
        from django.db import OperationalError
        from .management.commands.study_worker import heartbeat
        with patch('study.management.commands.study_worker.RuntimeState.objects.update_or_create', side_effect=OperationalError('database is locked')):
            self.assertFalse(heartbeat())
        self.assertTrue(heartbeat())

    def test_sparse_diagram_ocr_retries_isolated_label_mode(self):
        from .ingestion import ocr
        from PIL import Image
        with patch('study.ingestion.ocr_available', return_value=True), patch('study.ingestion.tesseract_command', return_value='tesseract'), patch('pytesseract.image_to_string', side_effect=['  ', 'PROCESSOR MEMORY']) as extract:
            self.assertEqual(ocr(Image.new('RGB', (10, 10))), 'PROCESSOR MEMORY')
            self.assertEqual(extract.call_args.kwargs['config'], '--psm 11')

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.override=override_settings(MEDIA_ROOT=Path(self.temp.name)/'media',DATA_ROOT=Path(self.temp.name))
        self.override.enable()
        self.env=patch.dict(os.environ,ACKS);self.env.start()
        self.client=APIClient()
        self.course=Course.objects.create(name='Circuits')
        self.other=Course.objects.create(name='Finance')
        self.source=Source.objects.create(course=self.course,title='Lecture',kind='text',status='ready')
        self.page=Page.objects.create(source=self.source,number=1,text='The resistance is 10 ohms. Voltage is 5 volts.',original_text='The resistance is 10 ohms. Voltage is 5 volts.')
        index_page(self.page)
    def tearDown(self):
        self.env.stop();self.override.disable();self.temp.cleanup()
    def post(self,path,data): return self.client.post('/api/'+path,data,format='json')
    def test_success_ingestion_correction_retrieval_and_citation(self):
        response=self.post('sources/',{'course':self.course.id,'title':'Assignment','text':'Kirchhoff current law conserves charge.'})
        self.assertEqual(response.status_code,201)
        job=claim('generation');run_job(job)
        source=Source.objects.get(pk=response.data['id'])
        self.assertEqual(source.status,'ready')
        page=source.pages.get()
        changed=self.client.patch(f'/api/pages/{page.id}/',{'text':'Kirchhoff current law conserves electric charge.'},format='json')
        self.assertEqual(changed.status_code,200)
        page.refresh_from_db();self.assertTrue(page.corrected)
        self.assertEqual(page.original_text,'Kirchhoff current law conserves charge.')
        evidence=retrieve(self.course.id,'Kirchhoff charge')
        cites=validate_citations([{'page_id':page.id,'quote':'conserves electric charge'}],evidence)
        self.assertEqual(cites[0]['source_id'],source.id)
    def test_course_isolation_retrieval_regions_context_and_study_items(self):
        source=Source.objects.create(course=self.other,title='Private finance',kind='text')
        page=Page.objects.create(source=source,number=1,text='The resistance is private finance.');index_page(page)
        self.assertNotIn(page.id,[e['page_id'] for e in retrieve(self.course.id,'resistance')])
        region=Region.objects.create(page=page,x=0,y=0,width=1,height=1)
        conversation=Conversation.objects.create(course=self.course)
        response=self.post(f'conversations/{conversation.id}/messages/',{'content':'Explain this','region_ids':[region.id]})
        self.assertEqual(response.status_code,400)
        response=self.post('study-items/',{'course':self.course.id,'kind':'bookmark','title':'Cross course','page':page.id})
        self.assertEqual(response.status_code,400)
        self.assertEqual(self.client.get('/api/sources/').status_code,400)
    def test_selected_region_and_invalid_rectangle(self):
        response=self.post('regions/',{'page':self.page.id,'x':0.8,'y':0,'width':0.4,'height':1})
        self.assertEqual(response.status_code,400)
        response=self.post('regions/',{'page':self.page.id,'x':0.1,'y':0.2,'width':0.4,'height':0.5,'text':'Resistance','confirmed':True})
        self.assertEqual(response.status_code,201)
        self.assertEqual(retrieve(self.course.id,'Explain',[response.data['id']])[0]['region_id'],response.data['id'])
    def test_invalid_citation_rejected(self):
        evidence=retrieve(self.course.id,'resistance')
        with self.assertRaises(ValueError): validate_citations([{'page_id':self.page.id,'quote':'Invented answer'}],evidence)
        with self.assertRaises(ValueError): validate_citations([{'page_id':999,'quote':'10 ohms'}],evidence)
    def test_late_page_match_is_in_evidence(self):
        self.page.text='Introduction filler. '*1000+'Zener breakdown happens at the threshold.'
        self.page.save();index_page(self.page)
        evidence=retrieve(self.course.id,'Zener breakdown threshold')
        self.assertIn('Zener breakdown',evidence[0]['text'])
        self.assertIn(evidence[0]['text'],self.page.text)
    @patch('study.jobs.generate_json')
    def test_chat_success_persists_and_stream_reconnect(self,generate):
        generate.return_value={'answer':'Use Ohm’s law with 10 ohms.','citations':[{'page_id':self.page.id,'quote':'The resistance is 10 ohms.'}]}
        conversation=Conversation.objects.create(course=self.course)
        response=self.post(f'conversations/{conversation.id}/messages/',{'content':'Explain resistance'})
        self.assertEqual(response.status_code,202)
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'complete')
        self.assertEqual(conversation.messages.filter(role='assistant',status='complete').count(),1)
        response=self.client.get(f'/api/conversations/{conversation.id}/stream/?job={job.id}',HTTP_ACCEPT='text/event-stream')
        self.assertEqual(response.status_code,200)
        self.assertEqual(response['Content-Type'],'text/event-stream')
        stream=b''.join(response.streaming_content).decode()
        self.assertIn('event: message',stream);self.assertIn('event: done',stream)
        # Non-browser clients can still reconnect with the default Accept header.
        response=self.client.get(f'/api/conversations/{conversation.id}/stream/?job={job.id}')
        self.assertIn(b'event: done',b''.join(response.streaming_content))
    @patch('study.jobs.generate_json',side_effect=GenerationUnavailable('AI setup required.'))
    def test_browser_stream_reports_paused_job_and_finishes(self,generate):
        conversation=Conversation.objects.create(course=self.course)
        self.post(f'conversations/{conversation.id}/messages/',{'content':'Explain resistance'})
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'paused')
        response=self.client.get(f'/api/conversations/{conversation.id}/stream/?job={job.id}',HTTP_ACCEPT='text/event-stream')
        self.assertEqual(response.status_code,200)
        stream=b''.join(response.streaming_content).decode()
        self.assertIn('event: error',stream);self.assertIn('AI setup required.',stream)
        self.assertIn('event: done',stream);self.assertIn('"status": "paused"',stream)
    def test_event_stream_negotiation_keeps_course_scope_and_normal_api_contract(self):
        conversation=Conversation.objects.create(course=self.course)
        other=Conversation.objects.create(course=self.other)
        job=Job.objects.create(course=self.course,kind='chat',status='complete',payload={'conversation_id':conversation.id})
        response=self.client.get(f'/api/conversations/{other.id}/stream/?job={job.id}',HTTP_ACCEPT='text/event-stream')
        self.assertEqual(response.status_code,404)
        self.assertIn(b'event: error',response.content)
        self.assertNotIn(b'conversation_id',response.content)
        self.assertEqual(self.client.get('/api/courses/',HTTP_ACCEPT='text/event-stream').status_code,406)
    @patch('study.jobs.generate_json')
    def test_invalid_model_output_fails_chat_without_fake_success(self,generate):
        generate.return_value={'answer':'Confident hallucination','citations':[{'page_id':self.page.id,'quote':'fake'}]}
        conversation=Conversation.objects.create(course=self.course)
        self.post(f'conversations/{conversation.id}/messages/',{'content':'resistance'})
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'failed')
        self.assertFalse(conversation.messages.filter(role='assistant',status='complete').exists())
    @patch('study.jobs.generate_json',side_effect=QuotaPaused('Quota reached'))
    def test_quota_pause_retry_and_cancel(self,generate):
        conversation=Conversation.objects.create(course=self.course)
        self.post(f'conversations/{conversation.id}/messages/',{'content':'resistance'})
        job=claim('generation');run_job(job);job.refresh_from_db();self.assertEqual(job.status,'paused')
        RuntimeState.objects.update_or_create(key='quota',defaults={'value':{'paused':True}})
        self.assertEqual(self.post(f'jobs/{job.id}/retry/',{}).status_code,409)
        self.post('status/resume/',{})
        self.assertEqual(self.post(f'jobs/{job.id}/retry/',{}).status_code,200)
        self.assertEqual(self.post(f'jobs/{job.id}/cancel/',{}).data['status'],'cancelled')
        self.assertIsNone(claim('generation'))
    @patch('study.jobs.generate_json')
    def test_cancel_during_generation_does_not_persist_success(self,generate):
        conversation=Conversation.objects.create(course=self.course)
        self.post(f'conversations/{conversation.id}/messages/',{'content':'resistance'})
        job=claim('generation')
        def cancel(*args,**kwargs):
            self.post(f'jobs/{job.id}/cancel/',{})
            return {'answer':'10 ohms','citations':[{'page_id':self.page.id,'quote':'10 ohms'}]}
        generate.side_effect=cancel
        run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'cancelled');self.assertEqual(job.result,{})
    def test_cloud_acknowledgement_and_no_model_fallback(self):
        with patch.dict(os.environ,{'TLDR_FREE_PROJECT_ACK':''}):
            with patch('study.provider.requests.Session') as session:
                with self.assertRaises(GenerationUnavailable):generate_json('hi')
                session.assert_not_called()
        with patch.dict(os.environ,{'TLDR_GEMINI_MODEL':'gemini-paid-model'}):
            self.assertFalse(configuration()['generation_enabled'])
    @patch('study.provider.requests.Session')
    def test_429_pauses_without_retry_and_key_is_only_header(self,session):
        response=Mock(status_code=429)
        session.return_value.post.return_value=response
        with self.assertRaises(QuotaPaused):generate_json('hi')
        session.return_value.post.assert_called_once()
        args,kwargs=session.return_value.post.call_args
        self.assertNotIn('test-secret',args[0]);self.assertEqual(kwargs['headers']['x-goog-api-key'],'test-secret')
        self.assertTrue(configuration()['quota_paused'])
    @patch('study.provider.time.sleep')
    @patch('study.provider.requests.Session')
    def test_service_unavailable_preserves_question_and_pauses_after_bounded_retry(self,session,sleep):
        session.return_value.post.return_value=Mock(status_code=503)
        conversation=Conversation.objects.create(course=self.course)
        self.post(f'conversations/{conversation.id}/messages/',{'content':'Explain resistance'})
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'paused')
        self.assertIn('temporarily unavailable (HTTP 503)',job.error)
        self.assertIn('Your work is saved',job.error)
        self.assertEqual(conversation.messages.get(role='user').content,'Explain resistance')
        self.assertEqual(conversation.messages.get(role='assistant').status,'error')
        self.assertEqual(session.return_value.post.call_count,2)
        self.assertEqual({call.args[0] for call in session.return_value.post.call_args_list},{'https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent'})
        sleep.assert_called_once_with(1)
        self.assertFalse(configuration()['quota_paused'])
    def test_foreign_origin_and_upload_type_rejected(self):
        response=self.client.post('/api/courses/',{'name':'Attack'},format='json',HTTP_ORIGIN='https://evil.example')
        self.assertEqual(response.status_code,403)
        response=self.client.post('/api/sources/',{'course':self.course.id,'file':SimpleUploadedFile('attack.html',b'<script>alert(1)</script>')},format='multipart')
        self.assertEqual(response.status_code,400)
    def test_study_item_crud_export_delete_and_fts_cleanup(self):
        item=self.post('study-items/',{'course':self.course.id,'kind':'flashcard','title':'Ohm','data':{'answer':'V=IR'}})
        self.assertEqual(item.status_code,201)
        response=self.client.patch(f"/api/study-items/{item.data['id']}/",{'completed':True},format='json')
        self.assertTrue(response.data['completed'])
        exported=self.client.get(f'/api/courses/{self.course.id}/export/')
        self.assertEqual(exported.status_code,200);exported.close()
        self.client.delete(f'/api/courses/{self.course.id}/')
        self.assertFalse(StudyItem.objects.exists())
        self.assertEqual(retrieve(self.course.id,'resistance'),[])
    def test_schema_rejects_executable_lesson(self):
        from .rendering import validate_lesson
        with self.assertRaises(ValueError):validate_lesson({'id':'x','python':'import os'})
    def test_paused_lesson_context_checks_scene_and_course(self):
        lesson=Lesson.objects.create(course=self.other,title='Other')
        revision=Revision.objects.create(lesson=lesson,number=1,spec={'chapters':[]})
        conversation=Conversation.objects.create(course=self.course)
        response=self.post(f'conversations/{conversation.id}/messages/',{'content':'Explain','context':{'revision_id':revision.id,'scene_id':'bad'}})
        self.assertEqual(response.status_code,404)
    def test_video_range_seeking_and_invalid_range(self):
        root=settings.MEDIA_ROOT/'renders';root.mkdir(parents=True)
        (root/'test.mp4').write_bytes(b'0123456789')
        response=self.client.get('/media/renders/test.mp4',HTTP_RANGE='bytes=2-5')
        self.assertEqual(response.status_code,206)
        self.assertEqual(response['Content-Range'],'bytes 2-5/10')
        self.assertEqual(b''.join(response.streaming_content),b'2345')
        response=self.client.get('/media/renders/test.mp4',HTTP_RANGE='bytes=-3')
        self.assertEqual(b''.join(response.streaming_content),b'789')
        self.assertEqual(self.client.get('/media/renders/test.mp4',HTTP_RANGE='bytes=99-').status_code,416)
        self.assertEqual(self.client.get('/media/renders/test.mp4',HTTP_RANGE='bytes=0-1,4-5').status_code,416)
    def lesson_spec(self):
        return {'id':'lesson1','title':'Resistance','target_minutes':15,'chapters':[{'id':'chapter1','title':'Basics','scenes':[{'id':'scene1','title':'Ohm law','narration':'The resistance is ten ohms. This relation connects voltage and current.','source_refs':[f'p{self.page.id}'],'objects':[{'id':'equation1','kind':'equation','label':'Ohm law','text':'V = I × R'}],'steps':[{'object_ids':['equation1'],'caption':'Read the relation'}]}]}]}

    def source_image_revision(self):
        fixture=Path(__file__).parent/'rendering'/'fixtures'/'source-grid.ppm'
        original=fixture.read_bytes()
        self.page.image.save('source-grid.ppm',ContentFile(original),save=False)
        self.page.width,self.page.height=4,2;self.page.save(update_fields=['image','width','height'])
        region=Region.objects.create(page=self.page,x=.5,y=0,width=.5,height=1,text='right half',confirmed=True)
        citation={'page_id':self.page.id,'region_id':region.id,'source_id':self.source.id,'source_title':self.source.title,'page_number':1,'quote':'right half'}
        citations=bind_source_assets([citation],self.course.id)
        spec=self.lesson_spec();scene=spec['chapters'][0]['scenes'][0];ref=f'r{region.id}'
        scene['source_refs']=[ref];scene['objects']=[{'id':'source1','kind':'source_image','label':'Preserved diagram','source_ref':ref,'overlays':[{'x':0,'y':0,'width':.5,'height':.5}]}];scene['steps']=[{'object_ids':['source1'],'caption':'Inspect the original'}]
        lesson=Lesson.objects.create(course=self.course,title='Source visual')
        return Revision.objects.create(lesson=lesson,number=1,spec=spec,citations=citations),region,original

    def test_revision_source_crop_preserves_exact_pixels_and_original(self):
        from PIL import Image
        import io
        revision,_,original=self.source_image_revision()
        assets=resolve_revision_assets(revision);asset=assets[next(iter(assets))]
        with Image.open(io.BytesIO(asset['content'])) as crop:
            self.assertEqual(crop.size,(2,2))
            # Fixture definition: the selected right half is green above yellow.
            self.assertEqual(list(crop.getdata()),[(0,255,0),(0,255,0),(255,255,0),(255,255,0)])
        self.assertEqual(Path(self.page.image.path).read_bytes(),original)

    def test_revision_source_assets_are_course_scoped_and_fail_when_deleted(self):
        with self.assertRaisesRegex(ValueError,'course'):
            bind_source_assets([{'page_id':self.page.id}],self.other.id)
        revision,_,_=self.source_image_revision()
        Path(self.page.image.path).unlink()
        with self.assertRaisesRegex(ValueError,'missing'):
            resolve_revision_assets(revision)

    def test_revision_source_region_change_invalidates_binding(self):
        revision,region,_=self.source_image_revision()
        baseline=resolve_revision_assets(revision)[f'r{region.id}']['sha256']
        region.x=.25;region.width=.75;region.save(update_fields=['x','width'])
        with self.assertRaisesRegex(ValueError,'changed'):
            resolve_revision_assets(revision)
        region.x=.5;region.width=.5;region.save(update_fields=['x','width'])
        self.assertEqual(resolve_revision_assets(revision)[f'r{region.id}']['sha256'],baseline)

    def test_source_asset_binding_rejects_nonfinite_region(self):
        fixture=Path(__file__).parent/'rendering'/'fixtures'/'source-grid.ppm'
        self.page.image.save('source-grid.ppm',ContentFile(fixture.read_bytes()),save=False);self.page.save(update_fields=['image'])
        region=Region.objects.create(page=self.page,x=float('inf'),y=0,width=.5,height=.5,text='bad')
        with self.assertRaisesRegex(ValueError,'normalized bounds'):
            bind_source_assets([{'page_id':self.page.id,'region_id':region.id}],self.course.id)

    def test_revision_api_binds_source_image_to_reviewed_citation(self):
        revision,region,_=self.source_image_revision()
        response=self.post(f'lessons/{revision.lesson_id}/revisions/',{'spec':revision.spec,'citations':[{'page_id':self.page.id,'region_id':region.id,'quote':'right half'}]})
        self.assertEqual(response.status_code,201,response.data)
        binding=response.data['citations'][0]['source_asset']
        self.assertEqual(binding['region_id'],region.id)
        self.assertEqual(binding['crop'],{'x':.5,'y':0.,'width':.5,'height':1.})

    @patch('study.rendering.render_lesson')
    def test_render_job_passes_only_resolved_revision_crop(self,render):
        from PIL import Image
        import io
        from .jobs import render_job
        revision,region,_=self.source_image_revision()
        job=Job.objects.create(course=self.course,lesson=revision.lesson,kind='render',status='running',payload={'revision_id':revision.id})
        def inspect_assets(*args,**kwargs):
            assets=kwargs['trusted_assets'];self.assertEqual(set(assets),{f'r{region.id}'})
            with Image.open(io.BytesIO(assets[f'r{region.id}']['content'])) as crop:
                self.assertEqual(crop.size,(2,2))
            return {}
        render.side_effect=inspect_assets
        render_job(job)
    @patch('study.jobs.generate_json')
    def test_followup_preserves_original_and_supplies_actual_scene_evidence(self,generate):
        original=Lesson.objects.create(course=self.course,title='Original')
        spec=self.lesson_spec()
        citations=[{'page_id':self.page.id,'quote':'The resistance is 10 ohms.'}]
        revision=Revision.objects.create(lesson=original,number=1,spec=spec,citations=citations)
        context={'revision_id':revision.id,'scene_id':'scene1','time_seconds':12,'object_ids':['equation1']}
        response=self.post('lessons/',{'course':self.course.id,'title':'Why?','prompt':'Why?','purpose':'followup','target_minutes':2,'context':context})
        self.assertEqual(response.status_code,201)
        self.assertNotEqual(response.data['id'],original.id)
        spec=spec | {'purpose':'followup','target_minutes':2}
        generate.return_value={'spec':spec,'citations':citations}
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'complete',job.error)
        prompt=generate.call_args.args[0]
        self.assertIn('Ohm law',prompt)
        self.assertIn('The resistance is 10 ohms.',prompt)
        revision.refresh_from_db()
        self.assertEqual(revision.spec['target_minutes'],15)
        self.assertEqual(original.revisions.count(),1)
        self.assertEqual(self.post(f'lessons/{original.id}/revisions/',{'prompt':'Why?','purpose':'followup','target_minutes':2,'context':context}).status_code,400)
    def test_playback_timestamp_must_match_rendered_scene(self):
        lesson=Lesson.objects.create(course=self.course,title='Rendered')
        revision=Revision.objects.create(lesson=lesson,number=1,spec=self.lesson_spec())
        Job.objects.create(course=self.course,lesson=lesson,kind='render',status='complete',payload={'revision_id':revision.id},result={'manifest':{'scenes':[{'scene_id':'scene1','start_seconds':10,'end_seconds':20}]}})
        conversation=Conversation.objects.create(course=self.course)
        context={'revision_id':revision.id,'scene_id':'scene1','time_seconds':5,'object_ids':['equation1']}
        self.assertEqual(self.post(f'conversations/{conversation.id}/messages/',{'content':'Why?','context':context}).status_code,400)
        context['time_seconds']=15
        self.assertEqual(self.post(f'conversations/{conversation.id}/messages/',{'content':'Why?','context':context}).status_code,202)
    def test_browser_clock_rounding_selects_the_next_scene_consistently(self):
        lesson=Lesson.objects.create(course=self.course,title='Precise chapter')
        spec=self.lesson_spec()
        second=json.loads(json.dumps(spec['chapters'][0]['scenes'][0]));second['id']='scene2'
        spec['chapters'][0]['scenes'].append(second)
        revision=Revision.objects.create(lesson=lesson,number=1,spec=spec)
        Job.objects.create(course=self.course,lesson=lesson,kind='render',status='complete',payload={'revision_id':revision.id},result={'manifest':{'scenes':[{'scene_id':'scene1','start_seconds':0,'end_seconds':74.99999999999987},{'scene_id':'scene2','start_seconds':74.99999999999987,'end_seconds':90}]}})
        conversation=Conversation.objects.create(course=self.course)
        context={'revision_id':revision.id,'scene_id':'scene2','time_seconds':74.999999,'object_ids':[]}
        response=self.post(f'conversations/{conversation.id}/messages/',{'content':'Why?','context':context})
        self.assertEqual(response.status_code,202)
        self.assertEqual(response.data['message']['context']['time_seconds'],75)
        context['scene_id']='scene1'
        self.assertEqual(self.post(f'conversations/{conversation.id}/messages/',{'content':'Why?','context':context}).status_code,400)
    @patch('study.rendering.render_lesson')
    def test_render_progress_tracks_completed_scenes(self,render):
        from .jobs import render_job
        lesson=Lesson.objects.create(course=self.course,title='Render progress')
        revision=Revision.objects.create(lesson=lesson,number=1,spec=self.lesson_spec())
        job=Job.objects.create(course=self.course,lesson=lesson,kind='render',status='running',payload={'revision_id':revision.id})
        def fake_render(*args,**kwargs):
            kwargs['on_progress']({'stage':'rendering','scene_id':'second','completed':1,'total':2})
            job.refresh_from_db()
            self.assertEqual(job.progress,47)
            self.assertEqual(job.result['completed'],1)
            kwargs['on_progress']({'stage':'assembling','completed':2,'total':2})
            job.refresh_from_db();self.assertEqual(job.progress,95)
            return {}
        render.side_effect=fake_render
        render_job(job)
    @patch('study.jobs.generate_json')
    def test_lesson_requires_review_then_explicit_render_and_context(self,generate):
        spec=self.lesson_spec()
        cites=[{'page_id':self.page.id,'quote':'The resistance is 10 ohms.'}]
        generate.return_value={'spec':spec,'citations':cites}
        response=self.post('lessons/',{'course':self.course.id,'title':'Resistance lesson','prompt':'Explain resistance'})
        self.assertEqual(response.status_code,201)
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'complete')
        self.assertEqual(Job.objects.filter(kind='render').count(),0)
        revision=Revision.objects.get(pk=job.result['revision_id'])
        self.assertEqual(revision.spec['target_minutes'],15)
        spec['chapters'][0]['scenes'][0]['title']='Revised title'
        response=self.post(f'lessons/{revision.lesson_id}/revisions/',{'spec':spec,'citations':cites})
        self.assertEqual(response.status_code,201)
        revision.refresh_from_db();self.assertEqual(revision.spec['chapters'][0]['scenes'][0]['title'],'Ohm law')
        rendered=self.post(f'lessons/{revision.lesson_id}/render/',{'revision_id':revision.id})
        self.assertEqual(rendered.status_code,202)
        conversation=Conversation.objects.create(course=self.course)
        response=self.post(f'conversations/{conversation.id}/messages/',{'content':'Explain resistance','context':{'revision_id':revision.id,'scene_id':'scene1','time_seconds':12,'object_ids':['equation1']}})
        self.assertEqual(response.status_code,202)
        context=conversation.messages.first().context
        self.assertEqual(context['object_ids'],['equation1'])
    def test_edited_lesson_cannot_reference_other_course(self):
        lesson=Lesson.objects.create(course=self.other,title='Other')
        response=self.post(f'lessons/{lesson.id}/revisions/',{'spec':self.lesson_spec(),'citations':[{'page_id':self.page.id,'quote':'10 ohms'}]})
        self.assertEqual(response.status_code,404)
    @patch('study.jobs.generate_json')
    def test_visual_only_region_sends_crop_and_tracks_visual_citation(self,generate):
        from PIL import Image
        from django.core.files.base import ContentFile
        import io
        output=io.BytesIO();Image.new('RGB',(100,100),'white').save(output,format='PNG')
        self.page.text='';self.page.image.save('visual.png',ContentFile(output.getvalue()));index_page(self.page)
        region=Region.objects.create(page=self.page,x=0.1,y=0.1,width=0.5,height=0.5,confirmed=True)
        generate.return_value={'answer':'This region is blank.','citations':[{'page_id':self.page.id,'region_id':region.id,'quote':'','visual':True}]}
        conversation=Conversation.objects.create(course=self.course)
        self.post(f'conversations/{conversation.id}/messages/',{'content':'Explain selected region','region_ids':[region.id]})
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'complete')
        self.assertTrue(generate.call_args.kwargs['images'][1]['inlineData']['data'])
        message=Message.objects.get(pk=job.result['message_id'])
        self.assertTrue(message.citations[0]['visual'])
    def test_worker_claim_is_exclusive_and_delete_waits_for_release(self):
        job=Job.objects.create(course=self.course,kind='ingest',payload={'source_id':self.source.id})
        claimed=claim('generation');self.assertEqual(claimed.id,job.id)
        self.assertIsNone(claim('generation'))
        with patch('study.views.time.monotonic',side_effect=[0,3]):
            response=self.client.delete(f'/api/courses/{self.course.id}/')
        self.assertEqual(response.status_code,409)
        self.assertTrue(Course.objects.filter(pk=self.course.id).exists())
        job.refresh_from_db();self.assertEqual(job.status,'cancelled')
        Job.objects.filter(pk=job.id).update(worker_active=False)
        self.assertEqual(self.client.delete(f'/api/courses/{self.course.id}/').status_code,204)
    def test_secret_is_never_returned_in_status(self):
        response=self.client.get('/api/status/')
        self.assertEqual(response.status_code,200)
        self.assertNotIn('test-secret',json.dumps(response.data))
    def test_invalid_pdf_fails_and_preserves_original(self):
        response=self.client.post('/api/sources/',{'course':self.course.id,'file':SimpleUploadedFile('broken.pdf',b'not a pdf')},format='multipart')
        self.assertEqual(response.status_code,201)
        job=claim('generation');run_job(job);job.refresh_from_db()
        self.assertEqual(job.status,'failed')
        source=Source.objects.get(pk=response.data['id'])
        self.assertEqual(source.status,'error');self.assertTrue(Path(source.original.path).is_file())
    def test_region_does_not_inherit_unrelated_full_page_quote(self):
        region=Region.objects.create(page=self.page,x=0,y=0,width=0.2,height=0.2)
        evidence=retrieve(self.course.id,'resistance',[region.id])
        self.assertEqual(evidence[0]['text'],'')
        with self.assertRaises(ValueError):
            validate_citations([{'page_id':self.page.id,'region_id':region.id,'quote':'10 ohms'}],evidence)
