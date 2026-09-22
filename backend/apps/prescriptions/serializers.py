"""Prescription serializers."""
from rest_framework import serializers
from .models import Prescription, Medicine


class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = ('id', 'name', 'dosage', 'frequency', 'duration', 'notes')


class PrescriptionSerializer(serializers.ModelSerializer):
    medicines = MedicineSerializer(many=True, read_only=True)
    pipeline_status = serializers.SerializerMethodField()
    # Alias for frontend compatibility
    ocr_text = serializers.CharField(source='cleaned_ocr_text', read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = (
            'id', 'raw_ocr_text', 'cleaned_ocr_text', 'ocr_text',
            'ocr_engine', 'ocr_confidence', 'low_confidence', 'warning',
            'pipeline_status', 'status',
            'medicines', 'created_at',
        )

    def get_pipeline_status(self, obj):
        if not obj.cleaned_ocr_text and not obj.raw_ocr_text:
            return 'OCR_FAILED'
        if not obj.medicines.exists():
            return 'PARTIAL'
        if obj.low_confidence:
            return 'LOW_CONFIDENCE'
        return 'SUCCESS'

    def get_status(self, obj):
        """Alias for pipeline_status for frontend compatibility."""
        return self.get_pipeline_status(obj)


class PrescriptionListSerializer(serializers.ModelSerializer):
    medicine_count = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = ('id', 'ocr_engine', 'ocr_confidence', 'medicine_count', 'created_at')

    def get_medicine_count(self, obj):
        return obj.medicines.count()
