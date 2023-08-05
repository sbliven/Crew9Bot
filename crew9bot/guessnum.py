"""Telegram bot to guess a number"""
import asyncio
import configparser
import logging
import random
from typing import TYPE_CHECKING, Dict, Union

from telethon import Button, TelegramClient, events  # type: ignore

from .game import Game
from .player import TelegramPlayer

if TYPE_CHECKING:
    from telethon.types import Peer  # type: ignore


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


class State:
    async def new_message(self, event) -> "State":
        await event.reply("I'm not sure what that means.")
        return self


class NewGame(State):
    async def new_message(self, event):
        # keyboard = ReplyKeyboardMarkup()
        await event.respond(
            "Think of an integer between 0 and 1000!",
            buttons=[[Button.text("OK, got one!")]],
        )
        return BoundedGuess(0, 1000)


class BoundedGuess(State):
    lower: int
    upper: int
    guess: int

    def __init__(self, lower, upper):
        self.lower = lower
        self.upper = upper
        self.guess = (lower + upper) // 2

    async def new_message(self, event):
        if event.message.message == "Yes":
            self.lower = self.guess
            self.guess = (self.lower + self.upper) // 2
        elif event.message.message == "No":
            self.upper = self.guess
            self.guess = (self.lower + self.upper) // 2
        elif event.message.message == "You guessed it":
            await event.respond("Yay, I guessed it! 🎉\n\nPlay again?")
            start = NewGame()
            nextstate = await start.new_message(event)
            return nextstate
        elif event.message.message == "Ok, got one!":
            pass
        else:
            logging.warning(
                f"Unexpected message from {self!r}: {event.message.message}"
            )
            await event.reply("I'm not sure what that means.")

        if self.lower == self.upper:
            await event.respond(
                f"Is it {self.lower}",
                buttons=[[Button.text("Yes"), Button.text("No")]],
            )
            return FinalGuess(self.lower)
        else:
            await event.respond(
                f"Is it greater than {self.guess}",
                buttons=[
                    [
                        Button.text("Yes"),
                        Button.text("You guessed it"),
                        Button.text("No"),
                    ]
                ],
            )
            return self

    def __repr__(self):
        return f"BoundedGuess({self.lower},{self.upper})"


class FinalGuess(State):
    def __init__(self, guess):
        self.guess = guess

    async def new_message(self, event):
        if event.message.message == "Yes":
            await event.respond("Yay, I guessed it! 🎉\n\nPlay again?")
        elif event.message.message == "No":
            await event.respond(
                "Hmm, something doesn't seem right there. Are you sure "
                "you answered correctly?\n\nPlay again?"
            )
        else:
            await event.reply("I'm not sure what that means.")

        start = NewGame()
        nextstate = await start.new_message(event)
        return nextstate


class GuessNumBot:
    _games: Dict["Peer", State] = {}  # map game ids to Game

    def __init__(self):
        config = load_config()["crew9bot"]
        api_id = config["api_id"]
        api_hash = config["api_hash"]
        self.token = config["token"]

        self.client = TelegramClient("guessnumbot", api_id, api_hash)

        # Public commands
        @self.client.on(events.NewMessage(pattern=r"/start"))
        async def start_cmd(event):
            peer = event.peer_id
            logging.info(
                f"Received {event.message.message} from {self.get_peer_id(peer)}"
            )
            existing = self.get_game(peer)
            if existing:
                # TODO handle this
                pass
            game = self.new_game(peer)

            self.set_game(peer, await game.new_message(event))

        @self.client.on(events.NewMessage())
        async def transition(event):
            if event.message.message.startswith("/start"):
                return  # handled already
            peer = event.peer_id
            logging.info(
                f"Received {event.message.message} from {self.get_peer_id(peer)}"
            )
            existing = self.get_game(peer)
            if not existing:
                await event.reply("Type /start to begin a game!")
            else:
                newstate = await existing.new_message(event)
                self.set_game(peer, newstate)

        # Private commands

        @self.client.on(events.NewMessage(pattern="/inline"))
        async def greeting(event):
            logging.info(f"Received {event.message.message}")

            btns = [
                Button.inline("*Clear*", data="/clear"),
                Button.inline("Custom 🍰", data="/custom"),
                Button.inline("Inline", data="/inline"),
            ]
            random.shuffle(btns)
            await event.respond(f"This is an inline keyboard!", buttons=[btns])

        @self.client.on(events.CallbackQuery())
        async def btnPush(event):
            logging.info(f"Callback {event.stringify()}")
            data = event.query.data
            await event.reply(data.decode())

        @self.client.on(events.NewMessage(pattern="/custom"))
        async def custom(event):
            logging.info(f"Received {event.message.message}")

            btns = [
                Button.text("/clear *Bold*"),
                Button.text("/custom"),
                Button.text("/inline"),
            ]
            random.shuffle(btns)
            await event.respond(f"This is an inline keyboard!", buttons=[btns])

        @self.client.on(events.NewMessage(pattern="/clear"))
        async def clear_cmd(event):
            logging.info(f"Received {event.message.message}")

            m = await event.respond("Clearing keyboard", buttons=Button.clear())
            # await self.client.delete_messages(event.chat_id, [event.id, m.id])

    def start(self):
        self.client.start(bot_token=self.token)

    def get_game(self, peer: "Peer"):
        "Get or create game by peer"
        peer_id = self.get_peer_id(peer)
        return self._games.get(peer_id)

    def new_game(self, peer: "Peer"):
        "Creates a new game. Call new_message to start it!"
        peer_id = self.get_peer_id(peer)
        game = NewGame()
        self._games[peer_id] = game
        return game

    def set_game(self, peer: "Peer", game: State):
        peer_id = self.get_peer_id(peer)
        self._games[peer_id] = game

    @classmethod
    def get_peer_id(cls, peer: "Peer"):
        if hasattr(peer, "chat_id"):
            return peer.chat_id
        return peer.user_id


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    bot = GuessNumBot()
    bot.start()
    bot.client.run_until_disconnected()
