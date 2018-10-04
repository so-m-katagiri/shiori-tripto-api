# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import sys
import logging
from argparse import ArgumentParser

import redis
import psycopg2

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    SourceUser, SourceGroup, SourceRoom,
    TemplateSendMessage, ConfirmTemplate, MessageAction,
    ButtonsTemplate, ImageCarouselTemplate, ImageCarouselColumn, URIAction,
    PostbackAction, DatetimePickerAction,
    CameraAction, CameraRollAction, LocationAction,
    CarouselTemplate, CarouselColumn, PostbackEvent,
    StickerMessage, StickerSendMessage, LocationMessage, LocationSendMessage,
    ImageMessage, VideoMessage, AudioMessage, FileMessage,
    UnfollowEvent, FollowEvent, JoinEvent, LeaveEvent, BeaconEvent,
    FlexSendMessage, BubbleContainer, ImageComponent, BoxComponent,
    TextComponent, SpacerComponent, IconComponent, ButtonComponent,
    SeparatorComponent, QuickReply, QuickReplyButton
)

command_char = os.getenv('COMMAND_CHAR', ".")

app = Flask(__name__)
logger = logging.getLogger(__name__)
redis = redis.from_url(os.environ['REDIS_URL'])
conn = psycopg2.connect(os.environ['DATABASE_URL'], sslmode='require')

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    text = event.message.text
    
    if isinstance(event.source, SourceUser):
        logger.info('SourceUser')
        profile = line_bot_api.get_profile(event.source.user_id)
        logger.info('profile:' + profile.display_name)
        Key = event.source.user_id + '_shiori_state'
        state = redis.get(Key) or''
        logger.info('current state:' + state)

        if text == '新しい旅のしおり':
            logger.info('Start shiori')
            if state != '':
                redis.delete(Key)
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text='旅のしおりの作成: ' + profile.display_name) +'さん、今回の目的地はどこですか？')
            redis.set(Key, 'ask-destination')
        elif text == 'やめる':
            logger.info('Terminate shiori')
            if state != '':
                redis.delete(Key)
            line_bot_api.reply_message(
                event.reply_token, 
                TextSendMessage(text='旅のしおりの作成: ' + profile.display_name) +'さん、破棄しました')
        else:
            if state == 'ask-destination':
                logger.info('shiori:ask-destination')
                line_bot_api.reply_message(
                    event.reply_token, 
                    TextSendMessage(text='旅のしおりの作成: ' + profile.display_name) +'さん、出発日はいつですか？')
                redis.set(Key, 'ask-startdate')
            elif state == 'ask-startdate':
                logger.info('shiori:ask-startdate')
                line_bot_api.reply_message(
                    event.reply_token, 
                    TextSendMessage(text='旅のしおりの作成: ' + profile.display_name) +'さん、作成しました')
                redis.delete(Key)
            else:
                logger.info('shiori:unknown-state')
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=event.message.text)
                )    
    #elif isinstance(event.source, SourceGroup):
    #elif isinstance(event.source, SourceRoom):
    else:
        logger.info('Echo')
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=event.message.text)
        )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


#if __name__ == "__main__":
#    arg_parser = ArgumentParser(
#        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
#    )
#    arg_parser.add_argument('-p', '--port', default=8000, help='port')
#    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
#    options = arg_parser.parse_args()
#
#    app.run(debug=options.debug, port=options.port)
