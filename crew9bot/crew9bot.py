"""Main module."""
import asyncio
import configparser
import logging
from .game import Game, get_games, get_player

from telethon import TelegramClient, events, Button  # type: ignore


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

        # Public commands
        @self.client.on(events.NewMessage(pattern=r"/start"))
        async def handler(event):
            logging.info("Received /start")
            # keyboard = ReplyKeyboardMarkup()
            await event.respond(
                """Welcome to *Crew9Bot!* Here are some available commands:

                [/new](/new) Start a new game
                [/join _game_id_](/join) Join an existing game
                """,
                # buttons=[[Button.inline("/new")]],
            )

        @self.client.on(events.NewMessage(pattern="/new"))
        async def handler(event):
            logging.info("Received /new")

            player = get_player(event.peer_id, self.client)
            game = Game()
            await game.join(player)

        # Private commands
        @self.client.on(events.NewMessage(pattern="/clear"))
        async def handler(event):
            m = await event.respond("Clearing keyboard", buttons=Button.clear())
            await self.client.delete_messages(event.chat_id, [event.id, m.id])

        # Tests & easter eggs
        @self.client.on(events.NewMessage(pattern="!ping"))
        async def handler(event):
            # Say "!pong" whenever you send "!ping", then delete both messages
            m = await event.respond("!pong")
            await asyncio.sleep(5)
            await self.client.delete_messages(event.chat_id, [event.id, m.id])

        @self.client.on(events.NewMessage(pattern="hello"))
        async def handler(event):
            print("handled hello event")
            peer_id = event.peer_id

            you = await self.client.get_entity(event.peer_id)

            await event.reply(f"Hey, {you.first_name}!")

        @self.client.on(events.NewMessage(pattern="/info"))
        async def handler(event):
            logging.info("Received /info")
            me = await self.client.get_me()
            await event.respond(f"```\nget_me -> {me.stringify()}\n```")

            try:
                dialogs = await self.client.get_dialogs()
                await event.respond(f"```\nget_dialogs -> {dialogs.stringify()}\n```")
            except Exception as ex:
                await event.respond(f"```\nget_dialogs -> {ex}\n```")

            you = await self.client.get_entity(event.peer_id)
            await event.respond(f"```\nyou -> {you.stringify()}\n```")

        @self.client.on(events.NewMessage(pattern="/list"))
        async def handler(event):
            logging.info("Received /list")
            msg = "Running games:\n\n"

            game_descriptions = await asyncio.gather(*(game.get_description() for game in get_games()))

            msg += "\n".join(f"- {game}" for game in game_descriptions)

            await event.respond(msg)


    def start(self):
        self.client.start(bot_token=self.token)
