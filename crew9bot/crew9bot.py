"""Main module."""
import configparser

from telethon import TelegramClient, events  # type: ignore


def default_config():
    config = configparser.ConfigParser()
    config["crew9bot"] = {"api_id": "ADD_APP_ID"}
    config["crew9bot"] = {"api_hash": "ADD_APP_HASH"}
    config["crew9bot"] = {"token": "ADD_TOKEN_HERE"}
    return config


def load_config():
    config = default_config()
    config.read("crew9bot.ini")
    return config


class Crew9Bot:
    def __init__(self):
        config = load_config()["crew9bot"]
        api_id = config["api_id"]
        api_hash = config["api_hash"]
        self.token = config["token"]

        self.client = TelegramClient("Crew9Bot", api_id, api_hash)

        @self.client.on(events.NewMessage)
        async def handler(event):
            await event.reply("Hey!")

    def start(self):
        self.client.start(bot_token=self.token)
