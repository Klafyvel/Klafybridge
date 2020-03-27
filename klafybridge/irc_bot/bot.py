import re
import random
import importlib
import datetime
import logging
import os
import pathlib

import toml

import irc.bot
import irc.strings

from ..messages import Message


class User(irc.bot.SingleServerIRCBot):
    def __init__(self, nickname, server, logger, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.waiting = []
        self.waiting = []
        self.nickname = nickname
        self.logger = logger

    def on_nicknameinuse(self, c, e):
        self.nickname = c.get_nickname() + "_"
        c.nick(self.nickname)

    def privmsg(self, c, e):
        self.logger.debug("%s : channels looks like %s", self.nickname, self.channels)
        if c in self.channels:
            for line in e.split("\n"):
                self.connection.privmsg(c, line)
        else:
            self.waiting.append(("p", c, e))
            self.connection.join(c)

    def action(self, c, e):
        if c in self.channels:
            self.connection.action(c, e)
        else:
            self.waiting.append(("a", c, e))
            self.connection.join(c)

    def process_once(self):
        done = []
        self.logger.debug(
            "%s: Processing once, waiting is %r", self.nickname, self.waiting
        )
        for x, (t, c, e) in enumerate(self.waiting):
            if c not in self.channels:
                self.connection.join(c)
                continue
            done.append(x)
            if t == "a":
                self.action(c, e)
            else:
                self.privmsg(c, e)
        for c in reversed(done):
            self.logger.debug("%s: Removing %r", self.nickname, c)
            self.waiting.pop(x)
        self.reactor.process_once()


class Bot(irc.bot.SingleServerIRCBot):
    def __init__(self, config_dir, pipe):
        """Initialize a bot object

        Args:
            filename: config file for the bot
        """
        self.tg_conn = pipe
        filename = pathlib.Path(config_dir) / "klafybridge.toml"
        self.config = toml.load(filename)
        self.logger = logging.getLogger(self.config["irc"]["logger"])
        self.logger.info("Loading irc configuration from %s.", filename)
        self.server = self.config["irc"]["server"]
        self.nickname = self.config["irc"]["nickname"]
        self.port = self.config["irc"]["port"]
        irc.bot.SingleServerIRCBot.__init__(
            self, [(self.server, self.port)], self.nickname, self.nickname
        )
        self.tg_users = {}

        self.channels_table = {}
        for irc_chan, tg_chan in self.config["channels"].items():
            self.channels_table[irc_chan] = tg_chan

    def add_tg_user(self, username):
        self.logger.debug("Adding user %s", username[1:])
        self.tg_users[username] = User(
            username[1:], self.server, self.logger, port=self.port
        )
        user = self.tg_users[username]
        user._connect()

    def tg_message(self, username, s, chan):
        self.tg_conn.send(
            Message(
                Message.Type.USER_MESSAGE,
                text=s,
                username=username,
                channel=self.channels_table[chan],
                content_type=Message.ContentType.TEXT,
            )
        )

    def tg_action(self, username, s, chan):
        self.tg_conn.send(
            Message(
                Message.Type.USER_ACTION,
                text=s,
                username=username,
                channel=self.channels_table[chan],
                content_type=Message.ContentType.TEXT,
            )
        )

    def on_nicknameinuse(self, c, e):
        self.nickname = c.get_nickname() + "_"
        c.nick(self.nickname)

    def on_welcome(self, c, e):
        for chan in self.channels_table.keys():
            self.connection.join(chan)

    def on_pubmsg(self, c, e):
        self.logger.debug("IRC received c = %s, e = %s", c, e)
        message = e.arguments[0]
        username = e.source.split("!")[0]
        check_username = lambda x: x.nickname == username
        chan = e.target
        if any(map(check_username, self.tg_users.values())):
            return
        self.tg_message(username, message, chan)

    def on_action(self, c, e):
        self.logger.debug("IRC received c = %s, e = %s", c, e)
        message = e.arguments[0]
        username = e.source.split("!")[0]
        check_username = lambda x: x.nickname == username
        chan = e.target
        if any(map(check_username, self.tg_users.values())):
            return
        self.tg_action(username, message, chan)

    def relay_message(self, msg):
        self.logger.debug("Relaying message %r", msg)
        chan = msg.channel
        if msg.username not in self.tg_users:
            self.add_tg_user(msg.username)

        user = self.tg_users[msg.username]

        if msg.text:
            self.logger.debug("Sending %s message via %r", msg.text, user)
            user.privmsg(chan, msg.text)

        if msg.content_type == Message.ContentType.MEDIA:
            user.action(
                chan,
                "sent a media available at %s (%sB)" % (msg.media_url, msg.media_size),
            )

    def relay_action(self, msg):
        self.logger.debug("Relaying action %r", msg)
        chan = msg.channel
        if msg.username not in self.tg_users:
            self.add_tg_user(msg.username)

        user = self.tg_users[msg.username]

        if msg.text:
            self.logger.debug("Sending %s message via %r", msg.text, user)
            user.action(chan, msg.text)

    def dispatch_message(self, msg):
        self.logger.debug("Dispatching message %r", msg)
        if msg.msgtype == Message.Type.USER_MESSAGE:
            self.relay_message(msg)
        elif msg.msgtype == Message.Type.USER_ACTION:
            self.relay_action(msg)
        elif msg.msgtype == Message.Type.REQUEST:
            getattr(self, "on_request_" + Message.request)(msg)
        else:
            getattr(self, "response_" + Message.response)(msg)

    def start(self):
        self._connect()
        while True:
            available = self.tg_conn.poll()
            if available:
                res = self.tg_conn.recv()
                self.dispatch_message(res)
            self.reactor.process_once(0.2)
            for user in self.tg_users.values():
                user.process_once()
