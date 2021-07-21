import asyncio
import random
import time

from db import DuckDB
from db import DuckEvent
from db import DuckStats

from irctokens import build, Line
from ircrobots import Bot as BaseBot
from ircrobots import Server as BaseServer
from ircrobots import ConnectionParams

lang = {
    "noduck": "there was no duck! you missed by {} seconds!",
    "noduckstart": "there was no duck!",
    "duckcought": "duck has been cought by {} in channel {} in {} seconds!",
    "duck": "・゜゜・。。・゜゜\_o< QUACK!",
    "stats": "{} has befriended {} ducks in {} different channels, having a befriend/loss ratio of {}.",
}

class DuckLogic:
    async def new_duck(self):
        self.messages = 0
        self.duckactive = True
        self.duckactivetime = time.time()
        await self.msgall(lang["duck"])

    async def duck_test(self):
        if self.messages > 1 and random.randint(0, 99) < 10: await self.new_duck()

    async def misstime(self):
        return format(time.time() - self.lastduck, '.2f')

    async def coughttime(self):
        return format(self.lastduck - self.duckactivetime, '.2f')

    async def duck_action(self, user, chan):
        db = DuckDB(self.db)
        if self.duckactive:
            self.duckactive = False
            self.messages = 0
            self.lastduck = time.time()
            await self.msgall(lang["duckcought"].format(user, chan, await self.coughttime()))
            db.add("B", user, time.time(), float(await self.coughttime()), chan)
        elif self.lastduck != 0:
            await self.msg(chan, lang["noduck"].format(await self.misstime()), user)
            db.add("M", user, time.time(), float(await self.misstime()), chan)
        else:
            await self.msg(chan, lang["noduckstart"], user)
            db.add("M", user, time.time(), -1, chan)
        db.write(self.db)

class Server(BaseServer, DuckLogic):
    messages = 0
    duckactive = False
    duckactivetime = 0
    lastduck = 0
    db = "duckdb"

    async def msg(self, chan, msg, usr=None):
        if usr != None:
            await self.send(build("PRIVMSG", [chan, usr + ": " + msg]))
        else: await self.send(build("PRIVMSG", [chan, msg]))

    async def msgall(self, msg):
        [await self.msg(channel, msg) for channel in self.channels]

    async def line_read(self, line: Line):
        print(f"{self.name} < {line.format()}")
        if line.command == "001":
            await self.send(build("JOIN", ["#testchannel"]))
        elif line.command == "PRIVMSG":
            print(line.params)
            print(line.hostmask.nickname)
            if line.params[1][0] == '%':
                cmd = line.params[1].split(' ')[0][1:]
                chan = line.params[0]
                user = line.hostmask.nickname
                args = line.params[1].split(' ')[1:]
                if cmd == "bef": await self.duck_action(user, chan)
                elif cmd == "trigger": await self.new_duck()
                elif cmd == "stats":
                    db = DuckDB(self.db)
                    stats = DuckStats(db)
                    await self.msg(chan, lang["stats"].format(
                        args[0],
                        stats.cought(args[0]),
                        stats.channels(args[0]),
                        format(stats.ratio(args[0]), ".3f")
                    ), user)
                return

            self.messages += 1
            await self.duck_test()
        elif line.command == "INVITE":
            await self.send(build("JOIN", [line.params[1]]))

    async def line_send(self, line: Line):
        print(f"{self.name} > {line.format()}")

class Bot(BaseBot):
    def create_server(self, name: str):
        return Server(self, name)

async def main():
    bot = Bot()
    params = ConnectionParams("test", "beepboop.systems", 6667, False)
    await bot.add_server("beep", params)
    await bot.run()

if __name__ == "__main__":
    asyncio.run(main())
