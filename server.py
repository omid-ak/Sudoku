from client import deserializer, serializer
import socket
from threading import Thread
from sys import argv
import pickle
from enum import Enum


class GameStates(Enum):
    READY = "ready"
    WAITINGFORPLAYERS = "waitingforplayers"
    PLAYERLEFT = "playerleft"
    FINISHED = "finished"


class Server:
    def __init__(self, port, number_of_clients):
        self.port = int(port)
        self.number_of_clients = number_of_clients
        self.client_counter = 0
        self.main_board = [[0, 0, 0, 0],
                           [0, 0, 0, 2],
                           [0, 0, 0, 0],
                           [0, 0, 3, 0],
                          ]
        self.db = {"game_state": "", "players": {}, "main_board": self.main_board, "turn_player": ""}
        self.db_file = "sudoku_db.json"
        self.db_write()

    @staticmethod
    def serializer(**kwargs):
        return pickle.dumps(kwargs)


    @staticmethod
    def deserializer(obj):
        return pickle.loads(obj)


    def db_write(self):
        pickle.dump(self.db, open(self.db_file, "wb"))


    def db_read(self):
        self.db = pickle.load(open(self.db_file, "rb"))


    def get_players_score(self):
        data = {}
        self.db_read()
        for item in self.db["players"].keys():
            data[item] = self.db["players"][item]["score"]
        return data

    def increase_score(self, username):
        self.db_read()
        self.db["players"][username]["score"] += 1
        self.db_write()


    def decrease_score(self, username):
        self.db_read()
        self.db["players"][username]["score"] -= 1
        self.db_write()


    def get_main_board(self):
        self.db_read()
        self.main_board = self.db.get("main_board")
        
    def board_is_full(self):
        self.get_main_board()
        counter = 0
        board_is_full = False
        for row in self.main_board:
            if 0 in row:
                break
            else:
                counter += 1
        if counter == len(self.main_board):
            board_is_full = True

        return board_is_full
        
    def update_main_board(self, new_data):
        self.get_main_board()
        # x-1 and y-1 --> zero based
        x, y, number = new_data[0]-1, new_data[1]-1, new_data[2]
        self.main_board[x][y] = number
        self.db["main_board"] = self.main_board
        self.db_write()
        # check if there are no any 0 in the board game finished
        if self.board_is_full():
            self.db["game_state"] = GameStates.FINISHED.value
            
        self.db_write()



    def validate_action(self, username, action):
        self.db_read()
        action_is_valid = False
        # check input
        x, y, number = action[0]-1, action[1]-1, action[2]
        if self.main_board[x][y] == 0 and 1 <= number <= 4:
            # check row
            row = self.main_board[x]
            if number not in row:
                # check column
                column = [i[y] for i in self.main_board]
                if number not in column:                
                    #check square
                    square = []
                    if 0 <= x < 2:
                        if 0 <= y < 2:
                            square = self.main_board[0][0:2] + self.main_board[1][0:2]
                        if 2 <= y < 4:
                            square = self.main_board[0][2:4] + self.main_board[1][2:4]

                    if 2 <= x < 4:
                        if 0 <= y < 2:
                            square = self.main_board[2][0:2] + self.main_board[3][0:2]
                        if 2 <= y < 4:
                            square = self.main_board[2][2:4] + self.main_board[3][2:4]

                    if number not in square:
                        action_is_valid = True


        # update score and main board
        if action_is_valid:
            # update main board
            self.update_main_board(new_data=action)
            self.increase_score(username=username)

        else:
            self.decrease_score(username=username)


    def handler(self, main_socket, client, addr):
        try:
            # in the case of username not be duplicate add first 4 chars of uuid
            username = deserializer(client.recv(4096)).get("username")
            self.db["players"][username] = {}
            self.db["players"][username]["score"] = 0
            if self.db["turn_player"] == "":
                self.db["turn_player"] = username

            if len(list(self.db.get("players").keys())) == 2:
                self.db["game_state"] = GameStates.READY.value

            elif len(list(self.db.get("players").keys())) == 1:
                self.db["game_state"] = GameStates.WAITINGFORPLAYERS.value

            self.db_write()
            print(self.db)

        except (OSError, EOFError):
            client.close()

        while True:
            try: 
                cycle_data = deserializer(client.recv(4096))

                print(cycle_data)
                # show board
                if cycle_data.get("choice") == '1':
                    self.get_main_board()
                    client.sendall(serializer(main_board=self.main_board,
                        state=self.db.get("game_state"),
                        scores=self.get_players_score(),
                        turn=self.db.get("turn_player")))

                    print(self.main_board, self.db)


                # put action
                elif cycle_data.get("choice") == '2':
                    print("read db")
                    self.db_read()
                    print(self.db)
                    game_state =self.db.get("game_state")
                    players = list(self.db.get("players").keys())
                    username = cycle_data.get("username")
                    players.remove(username)
                    if len(players) > 0:
                        another_player = players[0]
                    else:
                        another_player = ""
                    if self.db.get("turn_player") == username:
                        client.sendall(serializer(turn_player=username, state=game_state))
                        action = deserializer(client.recv(4096)).get("action")
                        print(action)
                        self.validate_action(username=username, action=action)
                        self.db["turn_player"] = another_player
                        self.db_write()
                    else:
                        client.sendall(serializer(turn_player=another_player, state=game_state))

                # exit
                elif cycle_data.get("choice") == '3':
                    self.db_read()
                    self.db["game_state"] = GameStates.PLAYERLEFT.value
                    self.db_write()
                    self.client_counter -= 1
                    client.close()


            except (OSError, EOFError, KeyboardInterrupt):
                client.close()
                main_socket.close()
                break


    def main(self):
        # connection

        main_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        main_socket.bind(('0.0.0.0', self.port))

        main_socket.listen()
        print("Waiting For connection...")

        try:
            while True:
                client, addr = main_socket.accept()
                if self.client_counter >= self.number_of_clients:
                    client.close()
                else:
                    thread = Thread(target=self.handler, args=(main_socket, client, addr))
                    thread.setDaemon(True)
                    thread.start()
                    self.client_counter += 1
        except OSError:
            print('closed')

if __name__ == "__main__":
    server = Server(port=argv[1], number_of_clients=2)
    server.main()