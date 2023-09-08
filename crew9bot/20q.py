# type: ignore

"""Telegram bot to play 20 questions given a fixed decision tree."""
import asyncio
import configparser
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Dict, Union

from telethon import Button, TelegramClient, events  # type: ignore

from .game import Game
from .player import TelegramPlayer

if TYPE_CHECKING:
    from telethon.types import Peer  # type: ignore


def default_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    config["crew9bot"] = {"api_id": "ADD_APP_ID"}
    config["crew9bot"] = {"api_hash": "ADD_APP_HASH"}
    config["crew9bot"] = {"token": "ADD_TOKEN_HERE"}
    return config


def load_config() -> configparser.ConfigParser:
    config = default_config()
    config.read("crew9bot.ini")
    return config


class QuestionTree:
    n: int
    question: str
    answers: Dict[str, Union["QuestionTree", "Answer"]]

    def __init__(
        self, n: int, question: str, answers: Dict[str, Union["QuestionTree", "Answer"]]
    ) -> None:
        self.n = 1
        self.question = question
        self.answers = answers

    def guess(self, answer: str) -> None:
        pass


@dataclass
class Answer(QuestionTree):
    def __init__(self, answer: str) -> None:
        super().__init__(f"Is it a {answer}?", {"Yes", "No"})


def initial_tree() -> QuestionTree:
    return QuestionTree(
        "Is it animal, mineral, or vegetable?",
        {
            "Animal": Answer("dog"),
            "Mineral": Answer("rock"),
            "Vegetable": Answer("corn"),
        },
    )


class Q20Bot:
    _games: Dict[int, Game] = {}  # map game ids to Game
    _players: Dict["Peer", "TelegramPlayer"] = {}  # map peers to Players

    def __init__(self) -> None:
        config = load_config()["crew9bot"]
        api_id = config["api_id"]
        api_hash = config["api_hash"]
        self.token = config["token"]

        self.client = TelegramClient("crew9bot", api_id, api_hash)

        # Public commands
        @self.client.on(events.NewMessage(pattern=r"/start"))
        async def start_cmd(event):
            logging.info(f"Received {event.message.message}")
            fields = event.message.message.strip().split()

            # keyboard = ReplyKeyboardMarkup()
            await event.respond(
                textwrap.dedent(
                    """Welcome to *20 Questions!*

                Please think of an object. I will try to guess it within 20 guesses!
                But I don't know many objects yet, so please go easy on me!
                """,
                    buttons=[[Button.inline("Animal", "Mineral", "Vegetable")]],
                )
            )

            if len(fields) > 1:
                try:
                    logging.info(f"Auto-joining game {fields[1]}")
                    game = self.get_game(fields[1])
                    player = self.get_player(event.peer_id)
                    await game.join(player)
                except Exception:
                    await event.respond(f"Error: I can't find game `{fields[1]}`")

        @self.client.on(events.NewMessage(pattern="/new"))
        async def new_cmd(event):
            logging.info(f"Received {event.message.message}")

            player = self.get_player(event.peer_id)
            game = self.new_game()

            await game.join(player)

        @self.client.on(events.NewMessage(pattern="/join"))
        async def join_cmd(event):
            logging.info(f"Received {event.message.message}")
            fields = event.message.message.strip().split()
            if len(fields) != 2:
                await event.respond(
                    "Error: Please provide a game ID.\n\nExample: `/join XXXXXXXX`"
                )
            else:
                try:
                    game = self.get_game(fields[1])
                    player = self.get_player(event.peer_id)
                    await game.join(player)
                except Exception:
                    await event.respond(f"Error: I can't find game `{fields[1]}`")

        # Private commands
        @self.client.on(events.NewMessage(pattern="/clear"))
        async def clear_cmd(event):
            logging.info(f"Received {event.message.message}")

            m = await event.respond("Clearing keyboard", buttons=Button.clear())
            await self.client.delete_messages(event.chat_id, [event.id, m.id])

        # Tests & easter eggs
        @self.client.on(events.NewMessage(pattern="!ping"))
        async def ping_cmd(event):
            # Say "!pong" whenever you send "!ping", then delete both messages
            m = await event.respond("!pong")
            await asyncio.sleep(5)
            await self.client.delete_messages(event.chat_id, [event.id, m.id])

        @self.client.on(events.NewMessage(pattern="hello|hi|hey"))
        async def greeting(event):
            logging.info(f"Received {event.message.message}")

            you = await self.client.get_entity(event.peer_id)

            await event.reply(f"Hey, {you.first_name}!")

        @self.client.on(events.NewMessage(pattern="/info"))
        async def info_cmd(event):
            logging.info(f"Received {event.message.message}")
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
        async def list_cmd(event):
            logging.info(f"Received {event.message.message}")
            msg = "Running games:\n\n"

            game_descriptions = await asyncio.gather(
                *(game.get_description() for game in self.get_games())
            )

            msg += "\n".join(f"- {game}" for game in game_descriptions)

            await event.respond(msg)

        @self.client.on(events.NewMessage(pattern="/begin"))
        async def begin_cmd(event):
            logging.info(f"Received {event.message.message}")
            player = self.get_player(event.peer_id)
            if player.game:
                game = player.game

                await game.begin()
            else:
                event.respond(
                    "Sorry, you're not in any games now! Use [/new](/new) "
                    "or [/join](/join) to play."
                )

        @self.client.on(events.NewMessage(pattern="/mission"))
        async def mission_cmd(event):
            fields = event.message.message.strip().split()

            player = self.get_player(event.peer_id)
            if not player.game:
                await event.respond(
                    "Sorry, you're not in any games now! Use [/new](/new) "
                    "or [/join](/join) to play."
                )
            game = player.game

            if len(fields) < 2:
                await event.respond(
                    f"You are on **Mission {game.mission.mission_id}**:"
                    f"{game.mission.description}"
                )
            elif len(fields) == 2:
                mission = int(fields[1])
                await game.set_mission(mission)
            else:
                await event.respond("usage: [/mission](/mission) [mission number]")

    def start(self) -> None:
        self.client.start(bot_token=self.token)

    def get_game(self, game_id: Union[int, str]) -> Game:
        "Get game by id. Works with either string or numeric ids."
        if isinstance(game_id, str):
            game_id = Game.decode_game_id(game_id)
        return self._games[game_id]

    def new_game(self) -> Game:
        game = Game()
        self._games[game.game_id] = game
        return game

    def get_games(self):
        "Get all active games"
        return self._games.values()

    @classmethod
    def get_peer_id(cls, peer: "Peer"):
        if hasattr(peer, "chat_id"):
            return peer.chat_id
        return peer.user_id

    def get_player(self, peer: "Peer") -> TelegramPlayer:
        "Get TelegramPlayer, or construct a new one if needed"
        peer_id = self.get_peer_id(peer)
        if peer_id not in self._players:
            self._players[peer_id] = TelegramPlayer(peer, self.client)

        return self._players[peer_id]
