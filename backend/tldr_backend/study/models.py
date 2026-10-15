from django.db import models

class Course(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, max_length=4000)
    created_at = models.DateTimeField(auto_now_add=True)

class Source(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sources')
    title = models.CharField(max_length=240)
    kind = models.CharField(max_length=16)
    original = models.FileField(upload_to='originals/%Y/%m/', blank=True)
    digest = models.CharField(max_length=64, blank=True)
    source_url = models.URLField(max_length=2048, blank=True)
    fetched_url = models.URLField(max_length=2048, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    extraction_notes = models.TextField(blank=True)
    status = models.CharField(max_length=16, default='queued')
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Page(models.Model):
    source = models.ForeignKey(Source, on_delete=models.CASCADE, related_name='pages')
    number = models.PositiveIntegerField()
    text = models.TextField(blank=True)
    original_text = models.TextField(blank=True)
    corrected = models.BooleanField(default=False)
    image = models.FileField(upload_to='pages/', blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    embedding = models.JSONField(default=list, blank=True)
    class Meta:
        ordering = ['number']
        constraints = [models.UniqueConstraint(fields=['source', 'number'], name='unique_source_page')]

class Region(models.Model):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='regions')
    label = models.CharField(max_length=160, blank=True)
    x = models.FloatField()
    y = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    text = models.TextField(blank=True, max_length=20000)
    confirmed = models.BooleanField(default=False)

class Conversation(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=240, default='New conversation')
    created_at = models.DateTimeField(auto_now_add=True)

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=12)
    content = models.TextField(blank=True)
    citations = models.JSONField(default=list)
    context = models.JSONField(default=dict)
    status = models.CharField(max_length=16, default='complete')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['id']

class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=240)
    created_at = models.DateTimeField(auto_now_add=True)

class Revision(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='revisions')
    number = models.PositiveIntegerField()
    spec = models.JSONField()
    citations = models.JSONField(default=list)
    teaching_plan = models.JSONField(null=True, blank=True, default=None)
    video = models.FileField(blank=True)
    captions = models.FileField(blank=True)
    transcript = models.FileField(blank=True)
    poster = models.FileField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['number']
        constraints = [models.UniqueConstraint(fields=['lesson', 'number'], name='unique_lesson_revision')]

class Job(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='jobs')
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.CASCADE, related_name='jobs')
    kind = models.CharField(max_length=16)
    status = models.CharField(max_length=16, default='queued')
    worker_active = models.BooleanField(default=False)
    progress = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    result = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['id']

class StudyItem(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='study_items')
    kind = models.CharField(max_length=16, choices=[(x,x) for x in ['flashcard','quiz','checklist','bookmark','confusion']])
    title = models.CharField(max_length=240)
    body = models.TextField(blank=True, max_length=20000)
    data = models.JSONField(default=dict)
    completed = models.BooleanField(default=False)
    page = models.ForeignKey(Page, null=True, blank=True, on_delete=models.SET_NULL)
    lesson = models.ForeignKey(Lesson, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

class RuntimeState(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    value = models.JSONField(default=dict)
