import pathlib
import multiprocessing as mp

import logging
import logging.config

import toml

from .tg_bot import main as tg_bot_main
from .irc_bot import main as irc_bot_main

CONF_DIR = pathlib.Path("/home/klafyvel/dev/klafybridge/etc/klafybridge/")


def main():
    irc_conn, tg_conn = mp.Pipe()
    tg_bot = mp.Process(target=tg_bot_main, args=(CONF_DIR, tg_conn,))
    irc_bot = mp.Process(target=irc_bot_main, args=(CONF_DIR, irc_conn,))

    logging.config.fileConfig(CONF_DIR / "logging.toml")

    logging.info("Starting telegram bot.")
    tg_bot.start()
    logging.info("Starting irc bot.")
    irc_bot.start()
    logging.info("Done.")


def install():
    logging.config.fileConfig(CONF_DIR / "logging.toml")
    configuration = toml.load(pathlib.Path(CONF_DIR) / "klafybridge.toml")
    pathlib.Path(configuration["files"]["storage"]).mkdir(
        mode=0o744, parents=True, exist_ok=True
    )


main()
