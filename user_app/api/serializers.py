from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import os
from user_app.models import Address
from django.contrib.staticfiles.storage import staticfiles_storage

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']


class RegistrationSerializer(serializers.ModelSerializer):
    
    first_name = serializers.CharField(required=True,min_length=3,max_length=20)
    last_name = serializers.CharField(required=True,min_length=3,max_length=20)
    profile_pic = serializers.ImageField(required=False)
    username = serializers.CharField(required=True,min_length=4, max_length=20)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name','last_name','profile_pic']
        extra_kwargs = {
            'password' : {'write_only': True}
        }
        
    def validate_profile_pic(self, value):
        ext = os.path.splitext(value.name)[1]
        valid_extensions = ['.jpg', '.jpeg', '.png','.jfif','.jpg']
        if not ext.lower() in valid_extensions:
            raise serializers.ValidationError("File extension not supported. Supported extensions are .png, .jpeg, .jpg, .jfif.")
        
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size exceeds the limit of 5 MB.")
        
        return value
    
    def validate_first_name_last_name(self, data):
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        if not isinstance(first_name, str):
            raise serializers.ValidationError("First name must be a string.")
        
        if not isinstance(last_name, str):
            raise serializers.ValidationError("Last name must be a string.")
        
        if len(first_name) < 3 or len(first_name) > 20:
            raise serializers.ValidationError("First name length must be between 4 and 20 characters.")
        
        if len(last_name) < 3 or len(last_name) > 20:
            raise serializers.ValidationError("Last name length must be between 4 and 20 characters.")
        
        return data
    
    def validate_username(self, value):
        if not isinstance(value, str):
            raise serializers.ValidationError("Username must be a string.")
        
        if len(value) < 4 or len(value) > 20:
            raise serializers.ValidationError("Username length must be between 4 and 20 characters.")
        
        return value
    
    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        return value

    def save(self):
        password = self.validated_data['password']
        profile_pic = self.validated_data.get('profile_pic')

        if User.objects.filter(username=self.validated_data['username']).exists():
            raise serializers.ValidationError({'error': 'username already exists!'})

        if User.objects.filter(email=self.validated_data['email']).exists():
            raise serializers.ValidationError({'error': 'Email already exists!'})

        user = User(
            email=self.validated_data['email'],
            username=self.validated_data['username'],
            first_name=self.validated_data['first_name'],
            last_name=self.validated_data['last_name'],
        )

        user.set_password(password)

        default_profile_pic_path = os.path.join(settings.STATICFILES_DIRS[0], 'default.png')
        default_profile_pic_name = os.path.basename(default_profile_pic_path)
        
        if not profile_pic:
            user.profile_pic = default_profile_pic_name
        else:
            ext = os.path.splitext(profile_pic.name)[1]
            filename = str(self.validated_data['username']) + ext
            fs = FileSystemStorage(location=settings.STATICFILES_DIRS[0])
            fs.save(filename, profile_pic)
            user.profile_pic = filename
        
        user.save()

        return user
        

class UserUpdateSerializer(serializers.ModelSerializer):
    
    profile_pic = serializers.ImageField(required=False)
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'profile_pic', 'username')

    def create(self, validated_data):
        raise NotImplementedError("Cannot create new user with UserUpdateSerializer.")

    def update(self, instance, validated_data):
        instance.email = validated_data.get('email', instance.email)
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)

        password = validated_data.get('password')
        if password:
            instance.set_password(password)

        profile_pic = validated_data.get('profile_pic')
        if profile_pic:
            old_username = instance.username
            new_username = validated_data.get('username', old_username)
            ext = os.path.splitext(profile_pic.name)[1]
            old_filename = str(old_username) + ext
            new_filename = str(new_username) + ext
            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            if fs.exists(old_filename):
                fs.delete(new_filename) # Delete new file if it exists
                fs.move(old_filename, new_filename)
            fs.save(new_filename, profile_pic)
            instance.profile_pic = new_filename

        instance.username = validated_data.get('username', instance.username)
        instance.save()

        return instance


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['id', 'user', 'street_name', 'street_no', 'government', 'district', 'house_no', 'apartment_no', 'floor_no', 'additional_info']
        read_only_fields = ['id', 'user']

    def validate(self, data):
        """
        Check if the address fields are valid.
        """
        street_name = data.get('street_name')
        if not isinstance(street_name, str):
            raise serializers.ValidationError("Street name must be a string.")
        if len(street_name) < 2 or len(street_name) > 100:
            raise serializers.ValidationError("Street name length must be between 2 and 100 characters.")
        if not street_name:
            raise serializers.ValidationError("Street name cannot be empty.")
        if any(char.isdigit() for char in street_name):
            raise serializers.ValidationError("Street name cannot contain numbers.")

        street_no = data.get('street_no')
        if not isinstance(street_no, str):
            raise serializers.ValidationError("Street number must be a string.")
        if len(street_no) < 1 or len(street_no) > 10:
            raise serializers.ValidationError("Street number length must be between 1 and 10 characters.")

        government = data.get('government')
        if not isinstance(government, str):
            raise serializers.ValidationError("Government must be a string.")
        if len(government) < 2 or len(government) > 100:
            raise serializers.ValidationError("Government length must be between 2 and 100 characters.")
        if not government:
            raise serializers.ValidationError("Government cannot be empty.")
        if any(char.isdigit() for char in government):
            raise serializers.ValidationError("Government cannot contain numbers.")

        district = data.get('district')
        if not isinstance(district, str):
            raise serializers.ValidationError("District must be a string.")
        if len(district) < 2 or len(district) > 100:
            raise serializers.ValidationError("District length must be between 2 and 100 characters.")

        house_no = data.get('house_no')
        if not isinstance(house_no, str):
            raise serializers.ValidationError("House number must be a string.")
        if len(house_no) < 1 or len(house_no) > 10:
            raise serializers.ValidationError("House number length must be between 1 and 10 characters.")

        apartment_no = data.get('apartment_no')
        if apartment_no and not isinstance(apartment_no, str):
            raise serializers.ValidationError("Apartment number must be a string.")
        if apartment_no and (len(apartment_no) < 1 or len(apartment_no) > 10):
            raise serializers.ValidationError("Apartment number length must be between 1 and 10 characters.")

        floor_no = data.get('floor_no')
        if floor_no and not isinstance(floor_no, str):
            raise serializers.ValidationError("Floor number must be a string.")
        if floor_no and (len(floor_no) < 1 or len(floor_no) > 10):
            raise serializers.ValidationError("Floor number length must be between 1 and 10 characters.")

        additional_info = data.get('additional_info')
        if additional_info and not isinstance(additional_info, str):
            raise serializers.ValidationError("Additional info must be a string.")
        if additional_info and len(additional_info) > 500:
            raise serializers.ValidationError("Additional info length must be less than or equal to 500 characters.")

        return data