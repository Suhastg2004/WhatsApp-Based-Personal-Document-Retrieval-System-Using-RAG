from rest_framework import serializers


class QueryRequestSerializer(serializers.Serializer):
    wa_id = serializers.CharField(max_length=32)
    question = serializers.CharField(min_length=2, max_length=2000)
    top_k = serializers.IntegerField(min_value=1, max_value=20, required=False)


class SourceChunkSerializer(serializers.Serializer):
    document_id = serializers.CharField()
    source = serializers.CharField()
    chunk_index = serializers.IntegerField()
    text = serializers.CharField()
    score = serializers.FloatField()


class QueryResponseSerializer(serializers.Serializer):
    answer = serializers.CharField()
    sources = SourceChunkSerializer(many=True)


class IngestTextRequestSerializer(serializers.Serializer):
    wa_id = serializers.CharField(max_length=32)
    text = serializers.CharField(min_length=1, max_length=50000)
    source_label = serializers.CharField(max_length=255, required=False, default="text_message")
