# Klafybridge

A bridge between IRC and telegram.

## Usage

Create the right configuration files (see next section). The program runs two processes : one for the telegram bot, one for the irc bot. The telegram bot sends the message to the irc bot. Telegram users appear as regular irc users. The telegram bot saves the medias sent on telegram on disk. You can setup a small http server to serve them.

## Example configuration

### /etc/klafybridge/klafybridge.toml

```toml
[files]
storage = "/var/www/klafybridge"
[telebot]
token = "TGBOTTOKEN" # fetched in environment
logger = "tg" # defined in logging.toml
[http]
url="https://example.org/"
[irc]
nickname = "bridge"
server = "irc.example.org"
port = 6667
logger = "irc" # defined in logging.toml
[channels]
# "#irc_channel" = telegramchanid
"#test" = -66666
```


### /etc/klafybridge/logging.conf

```toml
[loggers]
keys=root

[handlers]
keys=consoleHandler

[formatters]
keys=simpleFormatter

[logger_root]
level=INFO
handlers=consoleHandler

[logger_irc]
level=INFO
handlers=consoleHandler

[logger_tg]
level=INFO
handlers=consoleHandler

[handler_consoleHandler]
class=StreamHandler
level=INFO
formatter=simpleFormatter
args=(sys.stdout,)

[formatter_simpleFormatter]
format=%(asctime)s - %(name)s - %(levelname)s - %(message)s
datefmt=

```
