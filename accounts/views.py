from django.contrib.auth import get_user_model
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Profile
from .serializers import LoginSerializer, ProfileSerializer, RegisterSerializer

User = get_user_model()


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # TODO(verif): Require Proof-of-Work (client puzzle) token validation before registration.
        # TODO(verif): Support alternative verification via small crypto deposit to user's unique address.
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create profile for new user
        Profile.objects.get_or_create(user=user)

        # Send welcome email
        try:
            from notifications.services import send_welcome_email
            send_welcome_email(user)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send welcome email to {user.email}: {e}")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # TODO(verif): Validate Proof-of-Work (client puzzle) token for login throttling/anti-abuse.
        import logging
        logger = logging.getLogger(__name__)
        
        # Debug logging (note: can't access request.body after request.data is accessed)
        logger.info(f"Login request received. Content-Type: {request.content_type}")
        logger.info(f"Request data: {request.data}")
        
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Serializer validation failed: {serializer.errors}")
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        logger.info(f"Attempting login for email: {email}")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            logger.warning(f"Login failed: User not found for email: {email}")
            return Response(
                {'detail': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not user.check_password(password):
            logger.warning(f"Login failed: Invalid password for email: {email}")
            return Response(
                {'detail': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        
        logger.info(f"Login successful for email: {email}")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                'user': {
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                },
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
            },
            status=status.HTTP_200_OK,
        )


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
