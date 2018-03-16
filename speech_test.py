import os
import subprocess
from urllib.request import urlretrieve
import random
import string

import speech_recognition as sr

from pydub import AudioSegment
from math import ceil


SPEECH_ERROR = "Speech Recognition could not understand audio"


def download_video(file):
    random_name = ''.join([random.choice(string.ascii_letters) for n in range(12)])
    urlretrieve(file, "{}.mp4".format(random_name))

    return random_name



def convert_video_to_audio(name):
    command = "ffmpeg -i {video}.mp4 -ab 160k -ac 2 -ar 44100 -vn {audio}.wav".format(video=name, audio=name)
    subprocess.call(command, shell=True)

    os.remove('{video}.mp4'.format(video=name))

    return "{audio}.wav".format(audio=name)


def audio_recognition(path):
    AUDIO_FILE = path
    name = AUDIO_FILE.split('.')[0]
    r = sr.Recognizer()
    text = ''

    audio_file = AudioSegment.from_file(AUDIO_FILE, "wma")
    if audio_file.duration_seconds > 10:
        parts = int(ceil(audio_file.duration_seconds/10))

        try:
            for part in range(parts+1):
                if part != 0:
                    seconds = 10 * 1000
                    audio_part = audio_file[seconds*(part-1):seconds*part]

                    audio_part.export('{}{}.wav'.format(name, part), format='wav')

                    with sr.AudioFile('{}{}.wav'.format(name, part)) as source:
                        audio = r.record(source)  # read the entire audio file

                    text = text + ' ' + r.recognize_google(audio)
                    os.remove('{}{}.wav'.format(name, part))

            os.remove(path)
            return text
        except Exception:
            return SPEECH_ERROR
    else:
        with sr.AudioFile(path) as source:
            audio = r.record(source)  # read the entire audio file

        try:
            # for testing purposes, we're just using the default API key
            # to use another API key, use `r.recognize_google(audio, key="GOOGLE_SPEECH_RECOGNITION_API_KEY")`
            # instead of `r.recognize_google(audio)`
            os.remove(path)
            return r.recognize_google(audio)
        except sr.UnknownValueError:
            return SPEECH_ERROR
        except sr.RequestError as e:
            return SPEECH_ERROR



def save_speech_to_txt(speech, random_name):
    try:
        with open('{}.txt'.format(random_name), 'w') as output_file:
            output_file.write('Title: Your Speech' + '\n\n')
            output_file.write(speech)

    except IOError as errtext:
        if 'No such file or directory' in str(errtext):
            return SPEECH_ERROR
        else:
            return SPEECH_ERROR


def start_recognition(video_path):
    random_name = download_video(video_path)
    audio = convert_video_to_audio(random_name)
    text = audio_recognition(audio)
    save_speech_to_txt(text, random_name)

    return '{}.txt'.format(random_name)


# start_recognition('https://cdn.fbsbx.com/v/t59.3654-21/28702373_551823458532960_3042901848664047616_n.mp4/audioclip-1520942367000-2183.mp4?oh=213b4226f93f36d6040e21efbf739998&oe=5AAA3139')


# If u need to download ffmpeg
# imageio.plugins.ffmpeg.download()