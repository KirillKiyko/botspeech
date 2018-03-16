import os
import json
import requests

from validators import url
from pymessenger.bot import Bot
from get_transcript import start
from flask import Flask, request
from speech_test import start_recognition
from requests_toolbelt import MultipartEncoder

ACCESS_TOKEN = ''
VERIFY_TOKEN = ''

NOT_FOUND_ERROR = 'ERROR: No transcript found. This can mean one of several things:\n- There is no ' \
                  'human-created transcript for this video.\n- The video URL was entered incorrectly.\n' \
                  '- The video has "burned-on" captions, where the captions are part of the video track. ' \
                  'There is no way to extract burned-in captions.'

SPEECH_ERROR = "Speech Recognition could not understand audio"

app = Flask(__name__)
bot = Bot(ACCESS_TOKEN)

message_ids = []


@app.route("/", methods=['GET', 'POST'])
def receive_message():
    if request.method == 'GET':
        token_sent = request.args.get("hub.verify_token")

        return verify_fb_token(token_sent)
    else:
        output = request.get_json()
        event = output['entry'][0]
        messaging = event['messaging']
        message = messaging[0]

        # print(output)
        # print(event)
        # print(messaging)
        # print(message)
        s = message.get('message')
        print(s)
        recipient_id = message['sender']['id']

        try:
            message_id = message['message'].get('mid')
            print(message_id)

            if message_id not in message_ids:
                if s != None:
                    try:
                        if s.get('attachments')[0].get('type') == 'fallback':
                            send_message(recipient_id, 'Please, wait a minute. Recognition process can take some time.')
                            file_name = start(message['message'].get('text'))

                            if file_name == NOT_FOUND_ERROR:
                                send_message(recipient_id, file_name)
                            else:
                                send_file(recipient_id, file_name, ACCESS_TOKEN)
                                os.remove(file_name)
                        elif s.get('attachments')[0].get('type') == 'audio':
                            send_message(recipient_id, 'Please, wait a minute. Recognition process can take some time.')
                            file_name = start_recognition(message['message'].get('attachments')[0].get('payload').get('url'))

                            if file_name == SPEECH_ERROR:
                                send_message(recipient_id, file_name)
                            else:
                                send_file(recipient_id, file_name, ACCESS_TOKEN)
                                os.remove(file_name)

                        message_ids.append(message_id)
                    except Exception:
                        if url(message['message'].get('text')) == True:
                            if ('https://www.youtube.com' in message['message'].get('text') and 'watch?v' in message['message'].get('text')) or 'https://youtu.be' in message['message'].get('text'):
                                send_message(recipient_id, 'Please, wait a minute. Recognition process can take some time.')
                                file_name = start(message['message'].get('text'))

                                if file_name == NOT_FOUND_ERROR:
                                    send_message(recipient_id, file_name)
                                else:
                                    send_file(recipient_id, file_name, ACCESS_TOKEN)
                                    os.remove(file_name)
                            else:
                                send_message(recipient_id,
                                             'Sorry, but this is not youtube\'s url.')
                        else:
                            send_message(recipient_id,
                                         'Sorry, but now I can work only with youtube\'s urls or audio files.')

                        message_ids.append(message_id)

        except KeyError:
            pass

    return "Message Processed"


def verify_fb_token(token_sent):
    # take token sent by facebook and verify it matches the verify token you sent
    # if they match, allow the request, else return an error
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


# uses PyMessenger to send response to user
def send_file(recipient_id, file_path, access_token):
    '''Send file to the specified recipient.
            https://developers.facebook.com/docs/messenger-platform/send-api-reference/file-attachment
            Input:
                recipient_id: recipient id to send to
                file_path: path to file to be sent
            Output:
                Response from API as <dict>
            '''
    params = {
        "access_token": access_token
    }

    data = {
        # encode nested json to avoid errors during multipart encoding process
        'recipient': json.dumps({
            'id': recipient_id
        }),
        # encode nested json to avoid errors during multipart encoding process
        'message': json.dumps({
            'attachment': {
                'type': 'file',
                'payload': {}
            }
        }),
        'filedata': (file_path, open(file_path, 'rb'), 'file/txt')
    }

    # multipart encode the entire payload
    multipart_data = MultipartEncoder(data)

    # multipart header from multipart_data
    multipart_header = {
        'Content-Type': multipart_data.content_type
    }

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=multipart_header,
                      data=multipart_data)
    return "success"


def send_message(recipient_id, response):
    # sends user the text message provided via input response parameter
    bot.send_text_message(recipient_id, response)
    return "success"


if __name__ == "__main__":
    app.run()

    # https://b8a80731.ngrok.io
