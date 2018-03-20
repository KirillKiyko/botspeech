import os
import ast
import json
import requests
import unicodedata

from validators import url
from pymessenger.bot import Bot
from get_transcript import start
from flask import Flask, request
from speech_test import start_recognition
from requests_toolbelt import MultipartEncoder

ACCESS_TOKEN = 'EAALy86BNuZBcBALMGf1rhnd9B8raL1DAXyrwXgKKgc7N8XVOMKz00eCywZAF6GYgPzLmLmTx0n40KbXA1QA6fIYrth4D5srJRhlYmFFbpp65oFVVBYVgDuF70SlIqLcoqr0K8awZCEdZBRQG1S5wsS0n50yMw1DctjNjKsThZCLx6Hlrpvs6p'
VERIFY_TOKEN = 'YoutubeTranscript'

NOT_FOUND_ERROR = 'ERROR: No transcript found. This can mean one of several things:\n- There is no ' \
                  'human-created transcript for this video.\n- The video URL was entered incorrectly.\n' \
                  '- The video has "burned-on" captions, where the captions are part of the video track. ' \
                  'There is no way to extract burned-in captions.'

SPEECH_ERROR = "Speech Recognition could not understand audio"

WELCOME_MESSAGE = '''Hey {}, welcome to Botspeech. I'm here to transcribe your voice messages or send you the captions of Youtube videos. Just hit me up with a voice file or link to vid.'''

app = Flask(__name__)
bot = Bot(ACCESS_TOKEN)

message_ids = []
all_files = {}
all_srt = {}


@app.route("/", methods=['GET', 'POST'])
def receive_message():
    if request.method == 'GET':
        token_sent = request.args.get("hub.verify_token")

        return verify_fb_token(token_sent)
    else:
        output = request.get_json()
        event = output['entry'][0]
        print(event)
        messaging = event['messaging']
        message = messaging[0]
        recipient_id = message['sender']['id']

        try:
            if message['postback'].get('payload') == 'first visiting':
                sender = get_sender_name(recipient_id)
                print(sender)
                send_message(recipient_id, WELCOME_MESSAGE.format(sender))
            if message['postback'].get('payload') == 'Get me txt file':
                file_name = all_files.get(str(recipient_id))

                send_file(recipient_id, file_name, ACCESS_TOKEN)
                del all_files[str(recipient_id)]
            if message['postback'].get('payload') == 'Get me srt file':
                srt_name = all_srt.get(str(recipient_id))

                send_file(recipient_id, srt_name, ACCESS_TOKEN)
                del all_srt[str(recipient_id)]
        except KeyError:
            s = message.get('message')
            print(s)

            try:
                message_id = message['message'].get('mid')
                print(message_id)

                if message_id not in message_ids:
                    if s != None:
                        try:
                            if s.get('attachments')[0].get('type') == 'fallback':
                                send_message(recipient_id, 'Please, wait a minute. Recognition process can take some time.')
                                file_name, srt_name = start(message['message'].get('text'))
                                print(file_name, srt_name)

                                if file_name == NOT_FOUND_ERROR and srt_name == NOT_FOUND_ERROR:
                                    send_message(recipient_id, file_name)
                                elif '.txt' in file_name and '.srt' in srt_name:
                                    all_files[str(recipient_id)] = file_name
                                    all_srt[str(recipient_id)] = srt_name

                                    save_buttons(sender_id=recipient_id, access_token=ACCESS_TOKEN, file_name=file_name, srt_name=srt_name)
                                elif '.txt' not in file_name and srt_name == NOT_FOUND_ERROR and file_name != NOT_FOUND_ERROR:
                                    send_message(recipient_id, file_name)
                                elif srt_name == NOT_FOUND_ERROR:
                                    all_files[str(recipient_id)] = file_name

                                    save_buttons(sender_id=recipient_id, access_token=ACCESS_TOKEN, file_name=file_name)
                                else:
                                    send_message(recipient_id, file_name)
                            elif s.get('attachments')[0].get('type') == 'audio':
                                send_message(recipient_id, 'Please, wait a minute. Recognition process can take some time.')
                                file_name = start_recognition(message['message'].get('attachments')[0].get('payload').get('url'))

                                if file_name == SPEECH_ERROR:
                                    send_message(recipient_id, file_name)
                                elif '.txt' in file_name:
                                    all_files[str(recipient_id)] = file_name

                                    save_buttons(sender_id=recipient_id, access_token=ACCESS_TOKEN, file_name=file_name)
                                else:
                                    send_message(recipient_id, file_name)

                            message_ids.append(message_id)
                        except Exception:
                            if url(message['message'].get('text')) == True:
                                if ('https://www.youtube.com' in message['message'].get('text') and 'watch?v' in message['message'].get('text')) or 'https://youtu.be' in message['message'].get('text'):
                                    send_message(recipient_id, 'Please, wait a minute. Recognition process can take some time.')
                                    file_name, srt_name = start(message['message'].get('text'))

                                    if file_name == NOT_FOUND_ERROR and srt_name == NOT_FOUND_ERROR:
                                        send_message(recipient_id, file_name)
                                    elif '.txt' in file_name and '.srt' in srt_name:
                                        all_files[str(recipient_id)] = file_name
                                        all_srt[str(recipient_id)] = srt_name

                                        save_buttons(sender_id=recipient_id, access_token=ACCESS_TOKEN,
                                                     file_name=file_name, srt_name=srt_name)
                                    elif '.txt' not in file_name and srt_name == NOT_FOUND_ERROR and file_name != NOT_FOUND_ERROR:
                                        send_message(recipient_id, file_name)
                                    elif srt_name == NOT_FOUND_ERROR:
                                        all_files[str(recipient_id)] = file_name

                                        save_buttons(sender_id=recipient_id, access_token=ACCESS_TOKEN,
                                                     file_name=file_name)
                                    else:
                                        send_message(recipient_id, file_name)
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
    if token_sent == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return 'Invalid verification token'


def save_buttons(sender_id, access_token, file_name, srt_name=None):
    if srt_name == None:
        params = {
            "access_token": access_token
        }

        data = {
            'recipient': json.dumps({
                'id': sender_id
            }),
            "message":json.dumps({
              "attachment":{
                "type":"template",
                "payload":{
                  "template_type":"button",
                  "text":"What do you want to do with file?",
                  "buttons":[
                    {
                      "type":"postback",
                      "title": "Get me txt file",
                      "payload": "Get me txt file"
                    }
                  ]
                }
              }
            })
        }

        multipart_data = data

        multipart_header = {
            'Content-Type': 'application/json'
        }

        r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=multipart_header,
                          data=multipart_data)
    else:
        params = {
            "access_token": access_token
        }

        data = {
            'recipient': json.dumps({
                'id': sender_id
            }),
            "message": json.dumps({
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": "button",
                        "text": "What do you want to do with file?",
                        "buttons": [
                            {
                                "type": "postback",
                                "title": "Get me txt file",
                                "payload": "Get me txt file"
                            },
                            {
                                "type": "postback",
                                "title": "Get me srt file",
                                "payload": "Get me srt file"
                            }
                        ]
                    }
                }
            })
        }

        multipart_data = data

        multipart_header = {
            'Content-Type': 'application/json'
        }

        r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=multipart_header,
                          data=multipart_data)
    return "success"


def get_sender_name(sender_id):
    r = requests.get("https://graph.facebook.com/v2.6/{}?fields=first_name,last_name,profile_pic&access_token={}".format(sender_id, ACCESS_TOKEN))
    r = ast.literal_eval(r.text)

    sender = '{first_name} {last_name}'.format(first_name=r.get('first_name'), last_name=r.get('last_name'))

    return sender


def send_file(recipient_id, file_path, access_token):
    params = {
        "access_token": access_token
    }

    data = {
        'recipient': json.dumps({
            'id': recipient_id
        }),
        'message': json.dumps({
            'attachment': {
                'type': 'file',
                'payload': {}
            }
        }),
        'filedata': (file_path, open(file_path, 'rb'), 'file/txt')
    }

    multipart_data = MultipartEncoder(data)

    multipart_header = {
        'Content-Type': multipart_data.content_type
    }

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=multipart_header,
                      data=multipart_data)
    return "success"


def send_message(recipient_id, response):
    bot.send_text_message(recipient_id, response)
    return "success"


if __name__ == "__main__":
    app.run()
