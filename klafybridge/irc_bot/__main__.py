from .bot import Bot


def main(config_dir, pipe):
    bot = Bot(config_dir, pipe)
    bot.start()
