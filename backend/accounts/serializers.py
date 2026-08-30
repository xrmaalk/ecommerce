from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

User = get_user_model()


def normalize_email(value):
    return User.objects.normalize_email(value).strip().lower()


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "last_name", "date_joined")
        read_only_fields = ("id", "date_joined")


class RegistrationSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        email = normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "The passwords do not match."}
            )

        candidate = User(
            username=attrs["email"],
            email=attrs["email"],
            first_name=attrs["first_name"].strip(),
            last_name=attrs["last_name"].strip(),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": list(error.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        email = validated_data.pop("email")
        try:
            with transaction.atomic():
                return User.objects.create_user(
                    username=email,
                    email=email,
                    password=password,
                    first_name=validated_data["first_name"].strip(),
                    last_name=validated_data["last_name"].strip(),
                )
        except IntegrityError:
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            )


class SignInSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return normalize_email(value)


class ProfileSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=254)

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def validate_email(self, value):
        email = normalize_email(value)
        duplicate = User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return email

    def update(self, instance, validated_data):
        email = validated_data.get("email", instance.email)
        try:
            with transaction.atomic():
                instance.email = email
                instance.username = email
                instance.first_name = validated_data.get("first_name", instance.first_name).strip()
                instance.last_name = validated_data.get("last_name", instance.last_name).strip()
                instance.save(update_fields=("email", "username", "first_name", "last_name"))
        except IntegrityError:
            instance.refresh_from_db()
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            )
        return instance


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_current_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError("The current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "The passwords do not match."}
            )
        try:
            validate_password(attrs["new_password"], user=self.context["request"].user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"new_password": list(error.messages)})
        return attrs
