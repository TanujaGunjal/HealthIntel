"""Authenticated Google Calendar medication reminder endpoints."""
import hashlib
import json
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.core import signing
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.prescriptions.models import Medicine
from .models import GoogleCalendarCredential, MedicationCalendarEvent

SCOPES = ['https://www.googleapis.com/auth/calendar.events']


def _oauth_flow(state=None):
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError:
        raise RuntimeError('Google Calendar dependencies are not installed.')
    client_config = {
        'web': {
            'client_id': settings.GOOGLE_CLIENT_ID,
            'client_secret': settings.GOOGLE_CLIENT_SECRET,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def _credentials(credential):
    from google.oauth2.credentials import Credentials
    data = signing.loads(credential.token_data, salt='google-calendar-token')
    return Credentials.from_authorized_user_info(data, SCOPES)


class AuthorizeView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            return Response({'error': 'Google Calendar is not configured.'}, status=503)
        state = signing.dumps({'user_id': request.user.pk}, salt='google-calendar-oauth')
        try:
            flow = _oauth_flow(state)
            url, _ = flow.authorization_url(access_type='offline', prompt='consent',
                                            include_granted_scopes='true')
        except RuntimeError as exc:
            return Response({'error': str(exc)}, status=503)
        return Response({'authorization_url': url})


class StatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        credential = GoogleCalendarCredential.objects.filter(user=request.user).first()
        connected = bool(credential)
        scheduled_events = list(
            MedicationCalendarEvent.objects.filter(user=request.user).values('medicine_id', 'event_id', 'calendar_id')
        )
        scheduled_ids = list(dict.fromkeys(item['medicine_id'] for item in scheduled_events))
        return Response({
            'connected': connected,
            'calendar_id': credential.calendar_id if credential else None,
            'scheduled_medicine_ids': scheduled_ids,
            'scheduled_events': scheduled_events,
        })


class CallbackView(APIView):
    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        error_msg = None
        try:
            payload = signing.loads(request.query_params.get('state', ''),
                                    salt='google-calendar-oauth', max_age=600)
            flow = _oauth_flow(request.query_params.get('state'))
            flow.fetch_token(authorization_response=request.build_absolute_uri())
            token = json.loads(flow.credentials.to_json())
            GoogleCalendarCredential.objects.update_or_create(
                user_id=payload['user_id'],
                defaults={'token_data': signing.dumps(token, salt='google-calendar-token')},
            )
        except (signing.BadSignature, KeyError):
            error_msg = 'Invalid or expired OAuth state.'
        except Exception:
            error_msg = 'Google authorization failed.'

        # Check if client explicitly prefers JSON (e.g. programmatic tests)
        accept = request.headers.get('Accept', '')
        if 'application/json' in accept and 'text/html' not in accept:
            if error_msg:
                return Response({'error': error_msg}, status=400)
            return Response({'message': 'Google Calendar connected.'})

        if error_msg:
            redirect_url = f"{frontend_url}/prescriptions?calendar_error={error_msg}"
            html = f"""<!DOCTYPE html>
<html>
<head><title>Authorization Failed</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #0f172a; color: #f87171;">
    <h2>Google Calendar Authorization Failed</h2>
    <p>{error_msg}</p>
    <p>Returning to HealthIntel...</p>
    <script>
        try {{
            if (window.opener) {{
                window.opener.postMessage({{ type: 'GOOGLE_CALENDAR_ERROR', error: '{error_msg}' }}, '*');
                setTimeout(() => window.close(), 1500);
            }} else {{
                window.location.href = '{redirect_url}';
            }}
        }} catch(e) {{
            window.location.href = '{redirect_url}';
        }}
    </script>
</body>
</html>"""
            return HttpResponse(html, content_type='text/html', status=400)

        redirect_url = f"{frontend_url}/prescriptions?calendar_connected=true"
        html = f"""<!DOCTYPE html>
<html>
<head><title>Google Calendar Connected</title></head>
<body style="font-family: sans-serif; text-align: center; padding: 40px; background: #0f172a; color: #34d399;">
    <h2>✓ Google Calendar Connected</h2>
    <p>Returning to HealthIntel...</p>
    <script>
        try {{
            if (window.opener) {{
                window.opener.postMessage({{ type: 'GOOGLE_CALENDAR_CONNECTED' }}, '*');
                setTimeout(() => window.close(), 1000);
            }} else {{
                window.location.href = '{redirect_url}';
            }}
        }} catch(e) {{
            window.location.href = '{redirect_url}';
        }}
    </script>
</body>
</html>"""
        return HttpResponse(html, content_type='text/html')


class DisconnectView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        GoogleCalendarCredential.objects.filter(user=request.user).delete()
        return Response({'message': 'Google Calendar disconnected. Existing calendar events were not deleted.'})


class ScheduleMedicationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if not request.data.get('medicine_id'):
            return Response({'error': 'medicine_id is required.'}, status=400)
        medicine = get_object_or_404(
            Medicine.objects.select_related('prescription'),
            pk=request.data.get('medicine_id'),
            prescription__user=request.user,
        )
        credential = GoogleCalendarCredential.objects.filter(user=request.user).first()
        if not credential:
            return Response({'error': 'Connect Google Calendar before scheduling reminders.'},
                            status=400)
        try:
            start = datetime.fromisoformat(str(request.data['start_time']).replace('Z', '+00:00'))
            tz_name = request.data.get('timezone') or settings.TIME_ZONE
            from zoneinfo import ZoneInfo
            zone = ZoneInfo(tz_name)
            if timezone.is_naive(start):
                start = timezone.make_aware(start, zone)
            else:
                start = start.astimezone(zone)
            frequency = str(request.data.get('frequency') or medicine.frequency or 'daily').lower()
            freq = 'WEEKLY' if 'week' in frequency else 'DAILY'
            duration = _duration_days(medicine.duration)
            recurrence = f'RRULE:FREQ={freq}'
            if duration:
                end_date = (start + timedelta(days=duration - 1)).date()
                recurrence += f';UNTIL={end_date.strftime("%Y%m%d")}T235959Z'
            fingerprint_data = f'{medicine.pk}|{start.isoformat()}|{tz_name}|{freq}'
            fingerprint = hashlib.sha256(fingerprint_data.encode()).hexdigest()
            service = _calendar_service(_credentials(credential))
            event = {
                'summary': f'Medication: {medicine.name}',
                'description': (
                    'HealthIntel medication reminder.\n\n'
                    f'Prescribed instruction: {medicine.dosage or "Not extracted"} — '
                    f'{medicine.frequency or "Not extracted"} — {medicine.duration or "Not extracted"}\n\n'
                    'This reminder was created from the uploaded prescription. '
                    'HealthIntel does not modify or prescribe medication.'
                ),
                'start': {'dateTime': start.isoformat(), 'timeZone': tz_name},
                'end': {'dateTime': (start + timedelta(minutes=15)).isoformat(), 'timeZone': tz_name},
                'recurrence': [recurrence],
            }
            existing = MedicationCalendarEvent.objects.filter(user=request.user,
                                                               fingerprint=fingerprint).first()
            if existing:
                try:
                    result = service.events().update(calendarId=existing.calendar_id,
                                                     eventId=existing.event_id, body=event).execute()
                except Exception:
                    result = service.events().insert(calendarId=credential.calendar_id,
                                                     body=event).execute()
                    existing.event_id = result['id']
                    existing.calendar_id = credential.calendar_id
                    existing.save(update_fields=['event_id', 'calendar_id', 'updated_at'])
                return Response({'event_id': result['id'], 'created': False})
            result = service.events().insert(calendarId=credential.calendar_id, body=event).execute()
            MedicationCalendarEvent.objects.create(
                user=request.user, prescription=medicine.prescription, medicine=medicine,
                event_id=result['id'], calendar_id=credential.calendar_id, fingerprint=fingerprint,
            )
            return Response({'event_id': result['id'], 'created': True}, status=201)
        except KeyError:
            return Response({'error': 'start_time is required.'}, status=400)
        except ValueError:
            return Response({'error': 'start_time or timezone is invalid.'}, status=400)
        except Exception:
            return Response({'error': 'Unable to create Google Calendar reminder.'}, status=502)


def _calendar_service(credentials):
    try:
        from googleapiclient.discovery import build
    except ImportError:
        raise RuntimeError('Google Calendar dependencies are not installed.')
    return build('calendar', 'v3', credentials=credentials, cache_discovery=False)


def _duration_days(value):
    match = re.search(r'(\d+)\s*(day|days|week|weeks)', str(value or ''), re.IGNORECASE)
    if not match:
        return None
    count = int(match.group(1))
    return count * (7 if match.group(2).lower().startswith('week') else 1)
