import importlib
import datetime
import logging
import os
import pathlib
import toml
import telegram
from telegram.ext import MessageHandler, Filters
from telegram.ext import Updater, Handler
from telegram.ext import CommandHandler

import toml

from ..messages import Message


def only_allowed(callback):
    def func(self, update, context, *args, **kwargs):
        if not self.is_allowed(update, context):
            return
        callback(self, update, context, *args, **kwargs)

    return func


MEDIA_TYPES = (
    "text",
    "animation",
    "audio",
    "contact",
    "game",
    "invoice",
    "location",
    "passport_data",
    "photo",
    "poll",
    "sticker",
    "venue",
    "video",
    "voice",
)


class Bot:
    def __init__(self, config_dir, pipe):
        """Initialize a bot object

        Args:
            config_dir: config directory for the bot
            pipe: connection to the irc bot
        """

        filename = pathlib.Path(config_dir) / "klafybridge.toml"
        self.config = toml.load(filename)
        self.logger = logging.getLogger(self.config["telebot"]["logger"])
        self.logger.info("Loading telegram configuration from %s.", filename)

        self.url = self.config["http"]["url"]

        self.file_storage = pathlib.Path(self.config["files"]["storage"])

        self.channels_table = {}
        for irc_chan, tg_chan in self.config["channels"].items():
            self.channels_table[tg_chan] = irc_chan

        self.irc_conn = pipe

        self.updater = Updater(
            token=os.environ[self.config["telebot"]["token"]], use_context=True
        )
        self.dispatcher = self.updater.dispatcher

        self.action_handler = CommandHandler("me", self.on_action)
        self.dispatcher.add_handler(self.action_handler)

        for t in MEDIA_TYPES:
            setattr(
                self,
                t + "_handler",
                MessageHandler(getattr(Filters, t), getattr(self, "on_" + t)),
            )
            self.dispatcher.add_handler(getattr(self, t + "_handler"))

    def __getattr__(self, name):
        if "on_" in name:
            self.logger.debug("Creating %s.", name)

            def f(update, context):
                if not self.is_allowed(update, context):
                    return
                self.logger.debug(
                    "Hello from %s, I'll pass arguments %s.", name, name[3:]
                )
                return self.generic_on_media(name[3:], update, context)

            return f

    def on_unimplemented(self, update, context):
        t = repr(update.effective_message.effective_attachment)
        s = "*recieved an unsupported message with content %s*" % t
        self.irc_message(update.effective_user.name, s)

    def irc_message(self, username, s, chan):
        self.irc_conn.send(
            Message(
                Message.Type.USER_MESSAGE,
                text=s,
                username=username,
                content_type=Message.ContentType.TEXT,
                channel=self.channels_table[chan],
            )
        )

    def register_media(self, file, user="@Unknown", x=None):
        d = datetime.datetime.now()
        if x is not None:
            filename = "_".join(map(str, [user[1:], d.minute, d.second, x]))
        else:
            filename = "_".join(map(str, [user[1:], d.minute, d.second]))
        dir_path = (
            self.file_storage / str(d.year) / str(d.month) / str(d.day) / str(d.hour)
        )
        dir_path.mkdir(mode=0o755, parents=True, exist_ok=True)
        self.logger.debug("Saving %s", dir_path / filename)
        try:
            file.download(dir_path / filename)
        except Exception as e:
            self.logger.error("Could not download file, because : %s", e)
            raise e
        self.logger.debug("done")
        return self.url + "/".join(
            map(str, [str(d.year), str(d.month), str(d.day), str(d.hour), filename])
        )

    def is_allowed(self, update, context):
        return update.effective_chat.id in self.channels_table

    def relay_message(self, msg):
        self.logger.debug("Relaying message to channel %s.", msg.channel)
        self.updater.bot.send_message(msg.channel, "<%s> %s" % (msg.username, msg.text))

    def relay_action(self, msg):
        self.logger.debug("Relaying action to channel %s : .", msg.channel, msg.text)
        self.updater.bot.send_message(
            msg.channel,
            "*%s: %s*" % (msg.username, msg.text),
            parse_mode=telegram.ParseMode.MARKDOWN,
        )

    def dispatch_message(self, msg):
        if msg.msgtype == Message.Type.USER_MESSAGE:
            self.relay_message(msg)
        elif msg.msgtype == Message.Type.USER_ACTION:
            self.relay_action(msg)
        elif msg.msgtype == Message.Type.REQUEST:
            getattr(self, "on_request_" + Message.request)(msg)
        else:
            getattr(self, "response_" + Message.response)(msg)

    def start(self):
        self.updater.start_polling()
        while True:
            available = self.irc_conn.poll(1)
            if available:
                res = self.irc_conn.recv()
                self.dispatch_message(res)

    @only_allowed
    def on_action(self, update, context):
        username = update.effective_user.name
        message = update.effective_message.text
        chan = update.effective_chat.id
        self.logger.debug("Received action from %s.", username)
        self.irc_conn.send(
            Message(
                Message.Type.USER_ACTION,
                text=message[3:],
                username=username,
                content_type=Message.ContentType.TEXT,
                channel=self.channels_table[chan],
            )
        )

    @only_allowed
    def on_text(self, update, context):
        self.logger.debug("Received a text !")
        user = update.effective_user.name
        message = update.effective_message.text
        chan = update.effective_chat.id
        if update.effective_message.forward_from:
            f = update.effective_message.forward_from.name
            message = "Forwarded from %s :\n" % f + message
        elif update.effective_message.reply_to_message:
            reply = update.effective_message.reply_to_message
            f = reply.from_user.name
            message = (
                "Re %s :\n>" % f + "\n>".join(reply.text.split("\n")) + "\n" + message
            )
        self.irc_message(user, message, chan)

    @only_allowed
    def on_photo(self, update, context):
        self.logger.debug("Received a photo !")
        user = update.effective_user.name
        message = getattr(update.effective_message, "text", "")
        for x, p in enumerate(update.effective_message.photo):
            url = self.register_media(p.get_file(), user, x)
            chan = self.channels_table[update.effective_chat.id]
            self.irc_conn.send(
                Message(
                    Message.Type.USER_MESSAGE,
                    text=message,
                    username=user,
                    content_type=Message.ContentType.MEDIA,
                    media_url=url,
                    media_size=p.file_size,
                    channel=chan,
                )
            )

    def generic_on_media(self, media_name, update, context):
        self.logger.debug("Received a %s !", media_name)
        user = update.effective_user.name
        message = getattr(update.effective_message, "text", "")
        try:
            media = getattr(update.effective_message, media_name)
        except Exception as e:
            self.logger.error(
                "Could not retrieve media type %s in message.", media_name
            )
            self.on_unimplemented(update, context)
            raise e
        url = self.register_media(media.get_file(), user)
        chan = self.channels_table[update.effective_chat.id]
        self.irc_conn.send(
            Message(
                Message.Type.USER_MESSAGE,
                text=message,
                username=user,
                content_type=Message.ContentType.MEDIA,
                media_url=url,
                media_size=media.file_size,
                channel=chan,
            )
        )
