import json
import math
from rest_framework import serializers
from .models import Course, Source, Page, Region, Conversation, Message, Lesson, Revision, Job, StudyItem

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id','name','description','created_at']

class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id','page','label','x','y','width','height','text','confirmed']
    def validate(self, attrs):
        values = {k: attrs.get(k,getattr(self.instance,k,None)) for k in ('x','y','width','height')}
        if any(v is None or not math.isfinite(v) or not 0 <= v <= 1 for v in values.values()) or values['width']<=0 or values['height']<=0 or values['x']+values['width']>1.000001 or values['y']+values['height']>1.000001:
            raise serializers.ValidationError('Region must fit inside normalized page bounds.')
        if self.instance and 'page' in attrs and attrs['page'].id != self.instance.page_id:
            raise serializers.ValidationError('A region cannot be moved to another page.')
        return attrs

class PageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    regions = RegionSerializer(many=True, read_only=True)
    text = serializers.CharField(max_length=100000, allow_blank=True)
    class Meta:
        model = Page
        fields = ['id','source','number','text','original_text','corrected','image_url','width','height','regions']
        read_only_fields = ['source','number','original_text','corrected','width','height']
    def get_image_url(self,obj):
        return obj.image.url if obj.image else None

class SourceSerializer(serializers.ModelSerializer):
    pages = PageSerializer(many=True, read_only=True)
    original_url = serializers.SerializerMethodField()
    class Meta:
        model = Source
        fields = ['id','course','title','kind','status','error','original_url','created_at','pages','source_url','fetched_url','fetched_at','digest','extraction_notes']
        read_only_fields = ['kind','status','error']
    def get_original_url(self,obj):
        return obj.original.url if obj.original else None

class ConversationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Conversation
        fields = ['id','course','title','created_at']
    def validate_course(self,value):
        if self.instance and value.id != self.instance.course_id:
            raise serializers.ValidationError('Course cannot change.')
        return value

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id','conversation','role','content','citations','context','status','created_at']

class RevisionSerializer(serializers.ModelSerializer):
    manifest = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    captions_url = serializers.SerializerMethodField()
    transcript_url = serializers.SerializerMethodField()
    poster_url = serializers.SerializerMethodField()
    class Meta:
        model = Revision
        fields = ['id','lesson','number','spec','citations','teaching_plan','manifest','video_url','captions_url','transcript_url','poster_url','created_at']
    def get_manifest(self,obj):
        job = obj.lesson.jobs.filter(kind='render',status='complete',payload__revision_id=obj.id).order_by('-id').first()
        return job.result.get('manifest') if job else None
    def get_video_url(self,obj): return obj.video.url if obj.video else None
    def get_captions_url(self,obj): return obj.captions.url if obj.captions else None
    def get_transcript_url(self,obj): return obj.transcript.url if obj.transcript else None
    def get_poster_url(self,obj): return obj.poster.url if obj.poster else None

class JobSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ['id','course','lesson','kind','status','progress','error','result','created_at','updated_at']

class LessonSerializer(serializers.ModelSerializer):
    revisions = RevisionSerializer(many=True,read_only=True)
    jobs = JobSerializer(many=True,read_only=True)
    class Meta:
        model = Lesson
        fields = ['id','course','title','created_at','revisions','jobs']
    def validate_course(self,value):
        if self.instance and value.id != self.instance.course_id:
            raise serializers.ValidationError('Course cannot change.')
        return value

class StudyItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyItem
        fields = ['id','course','kind','title','body','data','completed','page','lesson','created_at']
    def validate(self, attrs):
        course = attrs.get('course',getattr(self.instance,'course',None))
        if self.instance and course.id != self.instance.course_id:
            raise serializers.ValidationError('Course cannot change.')
        page = attrs.get('page',getattr(self.instance,'page',None))
        lesson = attrs.get('lesson',getattr(self.instance,'lesson',None))
        if (page and page.source.course_id != course.id) or (lesson and lesson.course_id != course.id):
            raise serializers.ValidationError('References must belong to this course.')
        data = attrs.get('data',{})
        if not isinstance(data,dict) or len(json.dumps(data))>30000:
            raise serializers.ValidationError('data must be an object of at most 30,000 characters.')
        return attrs
