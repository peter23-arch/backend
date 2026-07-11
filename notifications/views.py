# notifications/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class SaveFCMTokenView(APIView):
    """
    Frontend calls this after getting an FCM token from Firebase.
    We save it on the user so we can push notifications to them.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token', '').strip()
        
        if not token:
            return Response(
                {'error': 'Token is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Optional: Validate token length/format
        if len(token) < 50:  # FCM tokens are typically longer
            return Response(
                {'error': 'Invalid token format.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save token to user
        request.user.fcm_token = token
        request.user.save()
        
        return Response(
            {'message': 'FCM token saved successfully.'},
            status=status.HTTP_200_OK
        )