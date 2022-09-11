from datetime import datetime
import itertools
import json
import asyncio
import websockets
from websockets.legacy.client import WebSocketClientProtocol
from websockets.exceptions import ConnectionClosedError
import sqlite3
import uuid


class SQL:
    PATH = "attacks.sqlite"
    def __init__(self):
        self.conn = sqlite3.connect(self.PATH)

    def create(self):
        sql = "CREATE TABLE IF NOT EXISTS attacks(\n" \
              "    id VARCAHR(50) NOT NULL," \
              "    attacker VARCHAR(25) NOT NULL," \
              "    defender VARCHAR(25) NOT NULL," \
              "    time DATETIME NOT NULL," \
              "    PRIMARY KEY(id)" \
              ")"
        self.conn.execute(sql)

    def insert(self, attacker: str, defender: str):
        sql = "insert into " \
              "    attacks(id, attacker, defender, time)" \
              "    values(?, ?, ?, ?)"
        try:
            self.conn.execute(sql, [uuid.uuid4().hex, attacker, defender, datetime.now()])
            self.conn.commit()
        except:
            self.conn = sqlite3.connect(self.PATH)

    def insert_many(self, *ad):
        sql = "insert into \n" \
              "    attacks(id, attacker, defender, time)" \
              "    values " + ",\n".join(["(?, ?, ?, ?)" for _ in range(len(ad))])
        now = datetime.now()
        try:
            self.conn.execute(sql, list(itertools.chain(*[[uuid.uuid4().hex, _[0], _[1], now] for _ in ad])))
            self.conn.commit()
        except:
            self.conn = sqlite3.connect(self.PATH)

    def recreate(self):
        sql = "DROP TABLE IF EXISTS attacks"
        self.conn.execute(sql)
        self.create()

    def connect(self):
        self.conn = sqlite3.connect(self.PATH)

unknown = 'unknown'
db = SQL()
db.create()

async def RecordAttacks():
    while True:
    # for iii in range(1):
        try:
            async with websockets.connect("wss://ws-centrifugo.torncity.com/connection/websocket") as websocket:
                websocket: WebSocketClientProtocol
                await websocket.send(json.dumps({"id": 1, "params": {"token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIyMDI1ODMyIn0.VVXJHKv0UY_PAqIXmdVHC-2366oGyeaALjcJOfjm88E"}}))
                await websocket.recv()
                await websocket.send(json.dumps({"id": 2, "method": 1, "params": {"channel": "elimination_score_channel"}}))
                start = datetime.now()
                try:
                    while True:
                    # for ii in range(3):
                        print(f"[{datetime.now()}] ~")
                        try:
                            resp = json.loads(await websocket.recv())['result']['data']['data']['message']['data']
                            # print(*[{'team': _['team'], 'diff': _['diff']} for _ in resp], sep="\n")

                            if len(resp) > 3:
                                for attack in resp:
                                    if attack["diff"] > 0:
                                        for i in range(abs(attack["diff"])):
                                            db.insert(attack['team'], unknown)
                                    elif attack["diff"] < 0:
                                        for i in range(abs(attack["diff"])):
                                            db.insert(unknown, attack['team'])
                                    else:
                                        for i in range(abs(attack["diff"])):
                                            db.insert_many(
                                                [attack['team'], unknown],
                                                [unknown, attack['team']])
                            else:
                                x = sorted(resp, key=lambda _: _["diff"])
                                if x[0]["diff"] == 0:
                                    db.insert_many(
                                        [x[1]['team'], x[0]['team']],
                                        [x[0]['team'], x[1]['team']])
                                else:
                                    for i in range(len(resp) - 1):
                                        db.insert(x[i + 1]['team'], x[i]['team'])
                        except KeyError as e:
                            print(e)
                            pass
                except ConnectionClosedError:
                    print((datetime.now() - start).total_seconds())
                    continue
        except:
            print("BIG ERROR")

asyncio.run(RecordAttacks())

# 488.17599
# 179.005406
# 730.973279