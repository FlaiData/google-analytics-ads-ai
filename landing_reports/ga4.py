"""Read-only Google Analytics Data API client."""
import google.auth
from google.auth.transport.requests import AuthorizedSession

SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'


def client():
    credentials, _ = google.auth.default(scopes=[SCOPE])
    session = AuthorizedSession(credentials)
    def post(property_id, body):
        response = session.post(f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport',json=body,timeout=60)
        response.raise_for_status()
        return response.json()
    return post
