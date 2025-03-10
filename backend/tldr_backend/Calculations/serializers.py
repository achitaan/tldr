from rest_framework import serializers
from .models import cvImage, TextHistory, Question

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ('id', 'question_text', 'answer', 'created_at')

class TextHistorySerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = TextHistory
        fields = ('id', 'text', 'created_at', 'questions')

class cvImageSerializer(serializers.ModelSerializer):  # Changed from HyperlinkedModelSerializer
    text_history = TextHistorySerializer(many=True, read_only=True)

    class Meta:
        model = cvImage
        fields = ('id', 'image', 'processed_image', 'extracted_text', 
                 'gpt_response', 'uploaded_at', 'text_history')