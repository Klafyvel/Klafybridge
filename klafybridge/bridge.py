import pathlib
import multiprocessing as mp
import time

import logging
import logging.config

import toml

import click

from .tg_bot import main as tg_bot_main
from .irc_bot import main as irc_bot_main

import click

@click.command()
@click.option('--config_dir', default="/etc/klafybridge/", help='Config directory.')
def main(config_dir):
    config_dir = pathlib.Path(config_dir)
    irc_conn, tg_conn = mp.Pipe()
    tg_bot = mp.Process(target=tg_bot_main, args=(config_dir, tg_conn,))
    irc_bot = mp.Process(target=irc_bot_main, args=(config_dir, irc_conn,))

    logging.config.fileConfig(config_dir / "logging.conf")

    logging.info("Starting telegram bot.")
    tg_bot.start()
    logging.info("Starting irc bot.")
    irc_bot.start()
    logging.info("Done.")

    while True:
        if not tg_bot.is_alive():
            logging.error("Tg bot died. Launching it again.")
            tg_bot = mp.Process(target=tg_bot_main, args=(config_dir, tg_conn,))
            tg_bot.start()
        if not irc_bot.is_alive():
            logging.error("IRC bot died. Launching it again.")
            irc_bot = mp.Process(target=irc_bot_main, args=(config_dir, irc_conn,))
            irc_bot.start()

        time.sleep(1)
