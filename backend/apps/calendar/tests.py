from unittest.mock import Mock, patch

from django.core import signing
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.prescriptions.models import Medicine, Prescription
from apps.users.models import User
from .models import GoogleCalendarCredential, MedicationCalendarEvent


@override_settings(GOOGLE_CLIENT_ID='client', GOOGLE_CLIENT_SECRET='secret')
class ScheduleMedicationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='patient@example.com', username='patient', password='password123',
        )
        prescription = Prescription.objects.create(user=self.user)
        self.medicine = Medicine.objects.create(
            prescription=prescription, name='Vitamin D', frequency='daily',
        )
        GoogleCalendarCredential.objects.create(
            user=self.user,
            token_data=signing.dumps({'token': 'opaque-token'}, salt='google-calendar-token'),
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch('apps.calendar.views._credentials')
    @patch('apps.calendar.views._calendar_service')
    def test_creates_recurring_event_and_is_idempotent(self, service_factory, credentials):
        events = Mock()
        events.insert.return_value.execute.return_value = {'id': 'event-1'}
        events.update.return_value.execute.return_value = {'id': 'event-1'}
        service_factory.return_value.events.return_value = events
        payload = {
            'medicine_id': self.medicine.id,
            'start_time': '2026-09-23T08:00:00+05:30',
            'timezone': 'Asia/Kolkata',
        }
        first = self.client.post('/api/calendar/schedule/', payload, format='json')
        second = self.client.post('/api/calendar/schedule/', payload, format='json')
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(MedicationCalendarEvent.objects.count(), 1)
        body = events.insert.call_args.kwargs['body']
        self.assertEqual(body['recurrence'], ['RRULE:FREQ=DAILY'])

    def test_status_endpoint_returns_connected_state_and_scheduled_ids(self):
        # Connected with no events
        response = self.client.get('/api/calendar/status/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['connected'])
        self.assertEqual(response.data['scheduled_medicine_ids'], [])

        # Create an event record
        MedicationCalendarEvent.objects.create(
            user=self.user,
            prescription=self.medicine.prescription,
            medicine=self.medicine,
            event_id='event-test-123',
            calendar_id='primary',
            fingerprint='fingerprint-xyz',
        )

        response = self.client.get('/api/calendar/status/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['connected'])
        self.assertEqual(response.data['scheduled_medicine_ids'], [self.medicine.id])

    def test_disconnect_deletes_credentials_without_deleting_events(self):
        # Create event
        MedicationCalendarEvent.objects.create(
            user=self.user,
            prescription=self.medicine.prescription,
            medicine=self.medicine,
            event_id='event-keep-123',
            calendar_id='primary',
            fingerprint='fingerprint-keep',
        )
        self.assertEqual(GoogleCalendarCredential.objects.filter(user=self.user).count(), 1)
        self.assertEqual(MedicationCalendarEvent.objects.filter(user=self.user).count(), 1)

        response = self.client.post('/api/calendar/oauth/disconnect/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(GoogleCalendarCredential.objects.filter(user=self.user).count(), 0)
        self.assertEqual(MedicationCalendarEvent.objects.filter(user=self.user).count(), 1)

        # Status now reports disconnected
        status_res = self.client.get('/api/calendar/status/')
        self.assertFalse(status_res.data['connected'])

    @patch('apps.calendar.views._oauth_flow')
    def test_authorize_endpoint(self, mock_flow_func):
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ('https://accounts.google.com/o/oauth2/auth?mock=1', 'state-val')
        mock_flow_func.return_value = mock_flow

        response = self.client.get('/api/calendar/oauth/authorize/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('authorization_url', response.data)
        self.assertEqual(response.data['authorization_url'], 'https://accounts.google.com/o/oauth2/auth?mock=1')

    @patch('apps.calendar.views._credentials')
    @patch('apps.calendar.views._calendar_service')
    def test_prescription_schedule_flow_azithromycin_and_cetirizine(self, service_factory, credentials):
        """Test scheduling Azithromycin 500 mg and Cetirizine 10 mg (at night) with idempotency."""
        mock_events = Mock()
        mock_events.insert.return_value.execute.side_effect = [{'id': 'azith-event-1'}, {'id': 'cetir-event-2'}]
        mock_events.update.return_value.execute.return_value = {'id': 'azith-event-1'}
        service_factory.return_value.events.return_value = mock_events

        prescription = Prescription.objects.create(user=self.user)
        azithromycin = Medicine.objects.create(
            prescription=prescription,
            name='Azithromycin',
            dosage='500 mg',
            frequency='once daily',
            duration='5 days',
        )
        cetirizine = Medicine.objects.create(
            prescription=prescription,
            name='Cetirizine',
            dosage='10 mg',
            frequency='once daily',
            duration='5 days',
            notes='{"timing": "at night"}',
        )

        # 1. Schedule Azithromycin 500 mg at 09:00
        azith_res = self.client.post('/api/calendar/schedule/', {
            'medicine_id': azithromycin.id,
            'start_time': '2026-09-23T09:00:00',
            'timezone': 'Asia/Kolkata',
            'frequency': 'once daily',
        }, format='json')
        self.assertEqual(azith_res.status_code, 201)
        self.assertTrue(azith_res.data['created'])
        self.assertEqual(azith_res.data['event_id'], 'azith-event-1')

        # 2. Duplicate click on Azithromycin -> idempotent (status 200, created=False)
        azith_dup = self.client.post('/api/calendar/schedule/', {
            'medicine_id': azithromycin.id,
            'start_time': '2026-09-23T09:00:00',
            'timezone': 'Asia/Kolkata',
            'frequency': 'once daily',
        }, format='json')
        self.assertEqual(azith_dup.status_code, 200)
        self.assertFalse(azith_dup.data['created'])
        self.assertEqual(azith_dup.data['event_id'], 'azith-event-1')

        # 3. Schedule Cetirizine 10 mg at 21:00 (user-selected "at night" time)
        cetir_res = self.client.post('/api/calendar/schedule/', {
            'medicine_id': cetirizine.id,
            'start_time': '2026-09-23T21:00:00',
            'timezone': 'Asia/Kolkata',
            'frequency': 'once daily',
        }, format='json')
        self.assertEqual(cetir_res.status_code, 201)
        self.assertTrue(cetir_res.data['created'])
        self.assertEqual(cetir_res.data['event_id'], 'cetir-event-2')

        # 4. Check status reports both scheduled medicine IDs
        status_res = self.client.get('/api/calendar/status/')
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(status_res.data['connected'])
        self.assertIn(azithromycin.id, status_res.data['scheduled_medicine_ids'])
        self.assertIn(cetirizine.id, status_res.data['scheduled_medicine_ids'])

        # 5. Disconnect removes credential but retains the 2 scheduled event records
        disc_res = self.client.post('/api/calendar/oauth/disconnect/')
        self.assertEqual(disc_res.status_code, 200)
        self.assertFalse(GoogleCalendarCredential.objects.filter(user=self.user).exists())
        self.assertEqual(MedicationCalendarEvent.objects.filter(user=self.user).count(), 2)

