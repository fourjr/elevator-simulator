from enum import IntEnum
import multiprocessing
import selectors
import sys
import threading
import random
import websockets
from websockets.sync import server as ws
from utils import load_algorithms

from web.backend.manager import ManagerPool, WebManager


ALGORITHMS = load_algorithms()


class OpCode(IntEnum):
    NEW_SIMULATION = 100  # USER_ID
    ADD_LOAD = 101  # INITIAL_FLOOR,DESTINATION_FLOOR, WEIGHT
    REMOVE_LOAD = 102  # LOAD_ID
    CREATE_ELEVATOR = 103  # CURRENT_FLOOR
    REMOVE_ELEVATOR = 104  # ELEVATOR_ID
    ADD_PASSENGER = 105  # INITIAL_FLOOR,DESTINATION_FLOOR
    SET_SEED = 106  # SEED
    SET_ALGORITHM = 108  # ALGORITHM_NAME
    START = 109
    END = 110
    PING = 111

    UPDATE = 201
    LOG = 202
    ERROR = 203
    ACK = 204
    MOVE_ELEVATOR = 205  # ELEVATOR_ID, FLOOR
    MOVE_LOAD = 206  # LOAD_ID, FLOOR
    REMOVE_PASSENGER = 207  # PASSENGER_ID


class Server:
    def __init__(self, port: int):
        max_processes = multiprocessing.cpu_count()
        mp_manager = multiprocessing.Manager()
        self.manager_pool = ManagerPool(mp_manager)
        for _ in range(max_processes):
            self.manager_pool.append(WebManager())
        self.port = port
        self.server = None
        self.close_event = threading.Event()

    def serve_timeout(self, server):
        poller = selectors.DefaultSelector()
        poller.register(server.socket, selectors.EVENT_READ)
        if sys.platform != 'win32':
            poller.register(server.shutdown_watcher, selectors.EVENT_READ)

        while not self.close_event.is_set():
            try:
                self.poll_socket(poller, server)
            except TimeoutError:
                continue
            except OSError:
                break

    def poll_socket(self, poller, server):
        val = poller.select(timeout=0.1)
        if val == []:
            raise TimeoutError
        # If the socket is closed, this will raise an exception and exit
        # the loop. So we don't need to check the return value of select().
        sock, addr = server.socket.accept()
        thread = threading.Thread(target=server.handler, args=(sock, addr))
        thread.start()

    def start(self):
        with ws.serve(self.handler, 'localhost', port=self.port) as server:
            self.server = server
            try:
                self.serve_timeout(server)
            except KeyboardInterrupt:
                print('KI')
                self.close()

    def close(self):
        self.manager_pool.close()
        self.close_event.set()

    def send(self, websocket: ws.ServerConnection, opcode: OpCode, message: str = ''):
        if opcode.value < 200:
            raise ValueError('Invalid opcode for server send, must begin with 2')

        websocket.send(f'{opcode:03d}{message}')

    def log(self, websocket: ws.ServerConnection, message: str):
        self.send(websocket, OpCode.LOG, message)

    def ack(self, websocket: ws.ServerConnection):
        self.send(websocket, OpCode.ACK)

    def handler(self, websocket: ws.ServerConnection):
        while not self.close_event.is_set():
            try:
                message = websocket.recv(1)
                if message is None:
                    break
            except (websockets.exceptions.ConnectionClosed, websockets.exceptions.ConnectionClosedOK):
                print('shutdown')
                self.server.shutdown()
                break
            except TimeoutError:
                continue
            else:
                for m in message.split('\n'):
                    self.process_message(websocket, m)

    def process_message(self, websocket: ws.ServerConnection, message: str):
        if message == '':
            return

        try:
            opcode = OpCode(int(message[0:3]))
        except ValueError:
            return self.send(websocket, OpCode.ERROR, 'Invalid opcode')

        try:
            match opcode:
                case OpCode.PING:
                    pass
                case OpCode.NEW_SIMULATION:
                    if getattr(websocket, 'manager', None) is None:
                        websocket.manager = self.manager_pool.get()
                        websocket.manager.ws_info = (self, websocket)
                case OpCode.ADD_LOAD:
                    try:
                        arguments = list(map(int, message[3:].split(',')))
                    except ValueError:
                        return self.send(websocket, OpCode.ERROR, 'Invalid arguments')

                    websocket.manager.algorithm.add_load(*arguments)
                case OpCode.REMOVE_LOAD:
                    try:
                        load_id = int(message[3:])
                    except ValueError:
                        return self.send(websocket, OpCode.ERROR, 'Invalid arguments')

                    websocket.manager.algorithm.remove_load(load_id)
                case OpCode.CREATE_ELEVATOR:
                    try:
                        current_floor = int(message[3:])
                    except ValueError:
                        return self.send(websocket, OpCode.ERROR, 'Invalid arguments')

                    websocket.manager.algorithm.create_elevator(current_floor)
                case OpCode.REMOVE_ELEVATOR:
                    try:
                        elevator_id = int(message[3:])
                    except ValueError:
                        return self.send(websocket, OpCode.ERROR, 'Invalid arguments')

                    websocket.manager.algorithm.remove_elevator(elevator_id)
                case OpCode.ADD_PASSENGER:
                    try:
                        arguments = list(map(int, message[3:].split(',')))
                    except ValueError:
                        return self.send(websocket, OpCode.ERROR, 'Invalid arguments')

                    websocket.manager.algorithm.add_passenger(*arguments)
                case OpCode.SET_SEED:
                    try:
                        seed = int(message[3:])
                    except ValueError:
                        return self.send(websocket, OpCode.ERROR, 'Invalid arguments')

                    websocket.manager.algorithm.rnd = random.Random(seed % 2 ** 32)
                case OpCode.SET_ALGORITHM:
                    try:
                        algorithm = ALGORITHMS[message[3:]]
                    except (ValueError, KeyError):
                        return self.send(websocket, OpCode.ERROR, 'Invalid arguments')

                    websocket.manager.reset(algorithm)

                case OpCode.START:
                    websocket.manager.set_active(True)
                    websocket.manager.start_simulation()
                case OpCode.END:
                    websocket.manager.set_active(False)
        except Exception:
            raise
            return self.send(websocket, OpCode.ERROR, 'Exception occurred in parsing message')
        else:
            self.ack(websocket)


if __name__ == '__main__':
    Server(8899).start()
