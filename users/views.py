# users/views.py — Authentication views

import uuid
# At the top of users/views.py

import firebase_config  # This will auto-initialize
import firebase_admin
from firebase_admin import auth
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.throttling import ScopedRateThrottle
from django.contrib.auth import get_user_model
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
)
from rest_framework.pagination import PageNumberPagination

User = get_user_model()

import json


class UsersPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class GoogleAuthView(APIView):
    """Login or register customer using Google ID token"""
    permission_classes = [AllowAny]

    def post(self, request):
        # Get the token from request
        id_token = request.data.get('id_token', '').strip()

        # Log for debugging
        print(f"📥 Received token: {id_token[:50] if id_token else 'None'}...")

        if not id_token:
            return Response(
                {'error': 'Google ID token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if Firebase is initialized
        if not firebase_admin._apps:
            return Response(
                {'error': 'Google sign-in is not configured on the server.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            # Verify the token with Firebase
            decoded = auth.verify_id_token(id_token)

            # Log success
            print(f"✅ Token verified for: {decoded.get('email')}")

        except auth.InvalidIdTokenError as e:
            print(f"❌ Invalid token: {e}")
            return Response(
                {'error': 'Invalid Google token. Please try signing in again.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except auth.ExpiredIdTokenError as e:
            print(f"❌ Expired token: {e}")
            return Response(
                {'error': 'Google token has expired. Please try signing in again.'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            print(f"❌ Token verification error: {e}")
            return Response(
                {'error': f'Token verification failed: {str(e)}'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        email = decoded.get('email')
        if not email:
            return Response(
                {'error': 'Google account email is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Continue with user creation/login...
        first_name, last_name = _split_name(decoded.get('name', ''))
        phone = decoded.get('phone_number', '') or ''

        user = User.objects.filter(email__iexact=email).first()

        if user and user.role != 'customer':
            return Response(
                {'error': 'This account is not allowed to sign in with customer Google auth.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not user:
            import uuid
            generated_password = str(uuid.uuid4())
            serializer = UserRegistrationSerializer(data={
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone,
                'role': 'customer',
                'password': generated_password,
                'password_confirm': generated_password,
            })
            if not serializer.is_valid():
                print(f"❌ Serializer errors: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            user = serializer.save()
            print(f"✅ Created new user: {email}")
        else:
            updated_fields = []
            if first_name and not user.first_name:
                user.first_name = first_name
                updated_fields.append('first_name')
            if last_name and not user.last_name:
                user.last_name = last_name
                updated_fields.append('last_name')
            if phone and not user.phone:
                user.phone = phone
                updated_fields.append('phone')
            if updated_fields:
                user.save(update_fields=updated_fields)
                print(f"✅ Updated user: {email}")

        refresh = RefreshToken.for_user(user)

        response_data = {
            'user': UserSerializer(user, context={'request': request}).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }

        print(f"✅ Google login successful for: {email}")
        return Response(response_data, status=status.HTTP_200_OK)


def _split_name(display_name):
    name = (display_name or '').strip()
    if not name:
        return '', ''
    parts = name.split()
    first_name = parts[0]
    last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''
    return first_name, last_name


class RegisterView(APIView):
    """
    Public registration — customers ONLY.
    Restaurant managers are registered exclusively from the admin dashboard.
    Platform admin uses the secret /admin-setup page.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        requested_role = request.data.get('role', 'customer')

        # Block anyone from self-registering as manager or admin
        if requested_role in ['restaurant_manager', 'platform_admin']:
            return Response(
                {'error': 'You cannot register as a manager or admin from this page.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Force role to customer regardless of what was sent
        data = request.data.copy()
        data['role'] = 'customer'

        serializer = UserRegistrationSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user, context={'request': request}).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# users/views.py - RegisterManagerView
class RegisterManagerView(APIView):
    """Admin only — register a restaurant manager"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if not request.user.is_platform_admin:
            return Response(
                {'error': 'Only platform admin can register restaurant managers.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Debug: Print the received data
        print("Received data:", request.data)

        data = request.data.copy()
        data['role'] = 'restaurant_manager'

        # Debug: Print the data being sent to serializer
        print("Data for serializer:", data)

        serializer = UserRegistrationSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            plain_password = request.data.get('password')
            return Response({
                'user': UserSerializer(user, context={'request': request}).data,
                'plain_password': plain_password,
                'login_email': user.email,
            }, status=status.HTTP_201_CREATED)

        # Debug: Print the validation errors
        print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PlatformAdminSetupView(APIView):
    """
    Used once for initial platform admin registration.
    Afterwards, only superusers can create new platform admins.
    """
    permission_classes = [AllowAny]  # Only the very first setup

    def post(self, request):
        setup_key = request.data.get('setup_key', '').strip()
        if not setup_key or setup_key != "PETERPRAISE":
            return Response(
                {'error': 'Invalid admin setup key.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        if User.objects.filter(role='platform_admin').exists():
            return Response(
                {'error': 'Platform admin already exists.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        data = request.data.copy()
        data['role'] = 'platform_admin'

        serializer = UserRegistrationSerializer(data=data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({'user': UserSerializer(user).data}, status=201)
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    """Login with email or username and password — throttled against brute force"""
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        identifier = request.data.get('identifier', '').strip()
        if not identifier:
            identifier = request.data.get('username', '').strip()
        if not identifier:
            identifier = request.data.get('email', '').strip()
        password = request.data.get('password', '')

        if not identifier or not password:
            return Response(
                {'error': 'Email/username and password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if '@' in identifier:
                user = User.objects.get(email__iexact=identifier)
            else:
                user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid email/username or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.check_password(password):
            return Response(
                {'error': 'Invalid email/username or password.'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not user.is_active:
            return Response(
                {'error': 'This account has been deactivated.'},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)
        return Response({
            'user': UserSerializer(user, context={'request': request}).data,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class ProfileView(APIView):
    """Get and update current user profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    def put(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                UserSerializer(request.user, context={'request': request}).data
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Logged in user changes their own password"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        current_password = serializer.validated_data['current_password']
        new_password = serializer.validated_data['new_password']

        # Verify current password is correct
        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        # Re-generate tokens since password changed
        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Password changed successfully.',
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class AvailableManagersView(APIView):
    """Admin only — search customers eligible to become a manager"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

        search = request.query_params.get('search', '').strip()
        users = User.objects.filter(role='customer')
        if search:
            from django.db.models import Q
            users = users.filter(
                Q(email__icontains=search) |
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        users = users.order_by('first_name', 'last_name')

        paginator = UsersPagination()
        page = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class ForgotPasswordView(APIView):
    """
    User submits their email.
    We generate a reset token, save it on the user, and email a reset link.
    In dev mode the email prints to the console/terminal.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response(
                {'error': 'Email address is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # We always return 200 even if email not found — security best practice
        # so attackers can't enumerate which emails are registered
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({
                'message': 'If that email is registered, a reset link has been sent.'
            })

        # Generate a unique token and store it on the user
        token = str(uuid.uuid4()).replace('-', '')
        user.password_reset_token = token
        user.save()

        # Build the reset URL pointing to our frontend
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{token}"

        # Send the email
        send_mail(
            subject='Reset Your FoodCourt Password',
            message=f"""
Hello {user.first_name or user.username},

You requested a password reset for your FoodCourt account.

Click the link below to set a new password:

{reset_url}

If you did not request this, please ignore this email.
Your password will not change.

— The FoodCourt Team
            """,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({
            'message': 'If that email is registered, a reset link has been sent.'
        })


class ResetPasswordView(APIView):
    """
    User clicks the link from email, submits new password with the token.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get('token', '').strip()
        new_password = request.data.get('new_password', '')
        confirm_password = request.data.get('confirm_password', '')

        if not token or not new_password:
            return Response(
                {'error': 'Token and new password are required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if new_password != confirm_password:
            return Response(
                {'error': 'Passwords do not match.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if len(new_password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find user by token
        try:
            user = User.objects.get(password_reset_token=token)
        except User.DoesNotExist:
            return Response(
                {'error': 'Invalid or expired reset link.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password and clear the token
        user.set_password(new_password)
        user.password_reset_token = ''
        user.save()

        return Response({'message': 'Password reset successfully. You can now log in.'})


class AllUsersView(APIView):
    """Admin only — list all users, paginated"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_platform_admin:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        users = User.objects.all().order_by('-date_joined')
        paginator = UsersPagination()
        page = paginator.paginate_queryset(users, request)
        serializer = UserSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)