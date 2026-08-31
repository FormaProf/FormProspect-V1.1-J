from services.note_service import NoteService
from services.activity_service import ActivityService


class ExplodingResolver:
    def resolve(self):
        raise AssertionError('resolver must not be used when mode is explicit')


class FakeApi:
    def __init__(self):
        self.created = []

    def list_activities(self, prospect_id):
        return [
            {
                'id': 'n1',
                'activity_type': 'note',
                'description': 'Note cloud',
                'subject': 'Note CRM',
                'created_at': '2026-08-24T05:00:00Z',
            },
            {
                'id': 'a1',
                'activity_type': 'call',
                'description': 'Appel',
                'subject': 'Relance',
                'created_at': '2026-08-24T05:05:00Z',
            },
        ]

    def create_activity(self, prospect_id, payload):
        self.created.append((prospect_id, payload))
        return {'id': 'created'}


def test_note_service_cloud_override_works_without_workspace():
    api = FakeApi()
    service = NoteService(
        resolver=ExplodingResolver(),
        cloud_api_client=api,
        is_cloud_mode=True,
    )
    notes = service.get_notes(None, 'prospect-1')
    assert len(notes) == 1
    assert notes[0][2] == 'Note cloud'


def test_activity_service_cloud_override_works_without_workspace():
    api = FakeApi()
    service = ActivityService(
        resolver=ExplodingResolver(),
        cloud_api_client=api,
        is_cloud_mode=True,
    )
    activities = service.get_activities(None, 'prospect-1')
    assert len(activities) == 2
    assert activities[1][2] == 'call'


def test_cloud_override_is_used_for_writes_too():
    api = FakeApi()
    note_service = NoteService(
        resolver=ExplodingResolver(),
        cloud_api_client=api,
        is_cloud_mode=True,
    )
    activity_service = ActivityService(
        resolver=ExplodingResolver(),
        cloud_api_client=api,
        is_cloud_mode=True,
    )
    note_service.add_note(None, 'p1', 'Bonjour')
    activity_service.add_activity(None, 'p1', 'Appel', 'Relance')
    assert len(api.created) == 2
