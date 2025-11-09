from rest_framework import serializers
from .models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    order_count = serializers.IntegerField(read_only=True, default=0)
    
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'phone_number', 'role', 'created_at', 'order_count']
        read_only_fields = ['id', 'created_at', 'order_count']


class UserCreateSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    phone_number = serializers.CharField(max_length=15)
    role = serializers.ChoiceField(choices=['user', 'staff', 'admin'], default='user')
    password = serializers.CharField(max_length=128, required=False, write_only=True)
    firebase_uid = serializers.CharField(max_length=128, required=False, allow_blank=True)
    
    def validate_username(self, value):
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError('Username already exists')
        return value
    
    def validate_phone_number(self, value):
        if CustomUser.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Phone number already exists')
        return value


class UserUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['user', 'staff', 'admin'])
