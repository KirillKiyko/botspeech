#!/usr/bin/env python

# -*- coding: utf-8 -*-

# import urllib2
import re
import os
# import urlparse
import youtube_dl
import warnings

import speech_recognition as sr
from urllib.request import urlopen
from urllib.request import HTTPError
from urllib.parse import parse_qs

from pydub import AudioSegment
from math import ceil


NOT_FOUND_ERROR = 'ERROR: No transcript found. This can mean one of several things:\n- There is no ' \
                      'human-created transcript for this video.\n- The video URL was entered incorrectly.\n' \
                      '- The video has "burned-on" captions, where the captions are part of the video track. ' \
                      'There is no way to extract burned-in captions.'

# GET VIDEO ID
def parse_url(vid_url):
    """
    Take video URL, perform basic sanity check, then filter out video ID.
    @param vid_url: URL of the video to get transcript from.
    @type vid_url: str
    """
    if 'watch?v' in vid_url:
        vid_code = re.findall(r'^[^=]+=([^&]+)', vid_url)
    elif 'youtu.be/' in vid_url:
        vid_code = re.findall(r'youtu\.be/([^&]+)', vid_url)

    else:
        raise ValueError()
    return vid_code[0]



#GET VIDEO TITLE
def get_title(vid_id):
    """
    Get title of video from ID.
    @param vid_id: YouTube ID for the video.
    @type vid_id: str
    """
    video_info = urlopen('http://youtube.com/get_video_info?video_id=' + vid_id)
    video_info = video_info.read()
    if parse_qs(video_info.decode('utf8'))['status'][0] == 'fail':
        return None
    else:
        title = """{}""".format(parse_qs(video_info.decode('utf8'))['title'][0])
        return title


def get_transcript(id):
    """Retrieve XML transcript from video ID. Works for human-created transcripts only."""

    try:
        transcript = urlopen('http://video.google.com/timedtext?lang=en&v=' + id)
        transcript_xml = transcript.read()
        print(transcript_xml, type(transcript_xml))
    except HTTPError as error:
        if '404' in str(error):
            return NOT_FOUND_ERROR
        else:
            return NOT_FOUND_ERROR

    if '<transcript>' not in transcript_xml.decode('utf-8'):
        return NOT_FOUND_ERROR

    return transcript_xml


def download_video(url):
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

# download_video('https://www.youtube.com/watch?v=KL2T0XRzWUI')


def audio_recognition(path):
    AUDIO_FILE = path
    name = AUDIO_FILE.split('.')[0]

    r = sr.Recognizer()
    text = ''

    audio_file = AudioSegment.from_file(AUDIO_FILE, "wma")
    print(audio_file.duration_seconds, type(audio_file.duration_seconds))
    if 10 < audio_file.duration_seconds:
        parts = int(ceil(audio_file.duration_seconds / 10))
        seconds = 10 * 1000


        part = 0
        while part < parts:
            audio_part = audio_file[seconds * part:seconds * (part + 1)]

            audio_part.export('{}{}.wav'.format(name, part), format='wav')

            with sr.AudioFile('{}{}.wav'.format(name, part)) as source:
                audio = r.record(source)

            try:
                print('All is good {}'.format(part))
                result = r.recognize_google(audio)
                os.remove('{}{}.wav'.format(name, part))
                print('Removed {}'.format(part))
            except Exception:
                print('Problem Detected {}'.format(part))
                result = ''
                os.remove('{}{}.wav'.format(name, part))
                break

            text = text + ' ' + result
            print(text)
            part += 1

        os.remove(path)
        return text
    elif audio_file.duration_seconds < 10:
        with sr.AudioFile(path) as source:
            audio = r.record(source)  # read the entire audio file

        try:
            os.remove(path)
            return r.recognize_google(audio)
        except sr.UnknownValueError:
            return NOT_FOUND_ERROR
        except sr.RequestError as e:
            return NOT_FOUND_ERROR
    # else:
    #     os.remove(path)
    #     return NOT_FOUND_ERROR

# audio_recognition('Go all the way - Charles Bukowski Poem-KL2T0XRzWUI.wav')


def remove_extra_linebreaks(string):
    """
    Remove extraneous linebreaks from text.
    If line ends with a period, insert a linebreak.
    @param string: The transcript to remove breaks from.
    @type string: str
    @return: Formatted text.
    """
    string_by_line = string.split('\n')
    new_string = str()
    for line in string_by_line:
        if line.endswith('.'):
            new_string += line + '\n'
        else:
            new_string += line + ' '
    return new_string


def format_transcript(transcript):
    """
    Receives the full XML transcript as plain text.
    @param transcript: Transcript as XML file.
    @type transcript: str
    """
    # Remove XML tags.
    transcript = re.sub("</text>", "\n", transcript)
    transcript = re.sub("<[^>]+>", "", transcript)

    # Remove encoded HTML tags.
    transcript = re.sub("&lt;.*?&gt;", "", transcript)

    # Replace ASCII character codes with the actual character.
    rep = {"&amp;#39;": "'", "&amp;gt;": ">", "&amp;quot;": '"', "&amp;lt;": "<"}

    # Slick single-pass regex replacement.
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    transcript = pattern.sub(lambda m: rep[re.escape(m.group(0))], transcript)

    # If text is more than 75% capitalized, we make it all lowercase for easier reading.
    num_upper_chars = len((re.findall("[A-Z]", transcript)))
    num_chars = len((re.findall("[a-zA-Z]", transcript)))
    percent_upper = (float(num_upper_chars) / float(num_chars)) * 100
    if percent_upper >= 75:
        transcript = transcript.lower()

    return transcript


# EXECUTION START HERE.
# Collect the video, ID, transcript and title.
def start(url):
    video_id = parse_url(url)
    title = get_title(video_id)
    transcript_xml = get_transcript(video_id)

    if transcript_xml == NOT_FOUND_ERROR:
        try:
            warnings.filterwarnings("ignore")
            download_video(url)
            transcript_text = audio_recognition('{}-{}.wav'.format(title, video_id))

            if transcript_text == NOT_FOUND_ERROR:
                return NOT_FOUND_ERROR
            else:
                outfile = os.path.expanduser(title + '.txt')

                # If user has not specified a filename, use the video title.
                if os.path.isdir(outfile):
                    outfile = os.path.join(outfile, title + '.txt')

                try:
                    print('save file')
                    with open(outfile, 'w') as output_file:
                        output_file.write('Title: ' + title + '\n\n')
                        output_file.write(transcript_text)

                    return outfile
                except IOError as errtext:
                    if 'No such file or directory' in str(errtext):
                        return NOT_FOUND_ERROR
                    else:
                        return NOT_FOUND_ERROR
        except Exception:
            return NOT_FOUND_ERROR
    else:
        transcript_text = format_transcript(transcript_xml.decode('utf-8'))
        transcript_text = remove_extra_linebreaks(transcript_text)

        # Validate output path.
        outfile = os.path.expanduser(title + '.txt')

        # If user has not specified a filename, use the video title.
        if os.path.isdir(outfile):
            outfile = os.path.join(outfile, title + '.txt')

        try:
            with open(outfile, 'w') as output_file:
                output_file.write('Title: ' + title + '\n\n')
                output_file.write(transcript_text)

            return outfile
        except IOError as errtext:
            if 'No such file or directory' in str(errtext):
                return NOT_FOUND_ERROR
            else:
                return NOT_FOUND_ERROR


# start('https://www.youtube.com/watch?v=KL2T0XRzWUI')
