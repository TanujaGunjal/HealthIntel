"""User serializers."""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True, label='Confirm password')

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'password2')
        extra_kwargs = {'email': {'required': True}}

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    profile_complete = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'full_name', 'age', 'sex', 'height_cm', 'weight_kg',
            'known_allergies', 'existing_conditions',
            'profile_complete', 'created_at',
        )
        read_only_fields = ('id', 'email', 'created_at', 'profile_complete')

    def get_profile_complete(self, obj):
        return obj.profile_complete


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for PATCH /api/auth/profile/ — only profile fields."""
    class Meta:
        model = User
        fields = (
            'full_name', 'age', 'sex', 'height_cm', 'weight_kg',
            'known_allergies', 'existing_conditions',
        )

    def validate_age(self, value):
        if value is not None and (value < 1 or value > 120):
            raise serializers.ValidationError('Age must be between 1 and 120.')
        return value
