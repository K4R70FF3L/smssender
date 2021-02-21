from __future__ import print_function
import pickle
import os.path
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from googleapiclient import errors
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


class Gmail:

    def __init__(self):
        """Shows basic usage of the Gmail API.
        Lists the user's Gmail labels.
        """
        creds = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        self.service = build('gmail', 'v1', credentials=creds)
        # pylint: disable=maybe-no-member
        self.email = self.service.users().getProfile()['emailAddress']

    def sendEmail(self, subject, to, message_text):
        message = MIMEText(message_text)
        message['from'] = self.email
        message['subject'] = subject
        message['to'] = to
        message = {'raw': base64.urlsafe_b64encode(message.as_string())}
        try:
            # pylint: disable=maybe-no-member
            self.service.users().messages().send(userId='me', body=message).execute()
        except errors.HttpError as error:
            # TODO let the error be thrown and handle it in the server
            print('An error occured: {}'.format(error))
