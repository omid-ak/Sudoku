import socket
from sys import argv
import pickle
import os
import uuid
from enum import Enum


class GameStates(Enum):
    READY = "ready"
    WAITINGFORPLAYERS = "waitingforplayers"
    PLAYERLEFT = "playerleft"
    FINISHED = "finished"


def serializer(**kwargs):
    return pickle.dumps(kwargs)


def deserializer(obj):
    return pickle.loads(obj)

def show_board_and_scores(data):
    board = data.get("main_board")
    a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p = board[0][0], board[0][1], board[0][2], board[0][3], board[1][0], board[1][1],\
     board[1][2], board[1][3], board[2][0], board[2][1], board[2][2], board[2][3], board[3][0], board[3][1], board[3][2], board[3][3]
    turn = data.get("turn")
    scores = data.get("scores")

    current_board = f"""x-1---2---3---4
y╔═══════╦═══════╗
1║ {a}   {b} ║ {c}   {d} ║
2║ {e}   {f} ║ {g}   {h} ║
|╠═══════╬═══════╣
3║ {i}   {j} ║ {k}   {l} ║
4║ {m}   {n} ║ {o}   {p} ║
 ╚═══════╩═══════╝"""

    print("scores:")
    for item in scores.keys():
        print(f"{item}: {scores[item]}")
    print(f"\nturn: {turn}")
    print(f"\nBoard: \n {current_board}")

def main():
    connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ip = argv[1]
    port = int(argv[2])
    connection.connect((ip, port))

    os.system("clear")
    username = input("Enter your user name: \n") + "#" + str(uuid.uuid1())[0:4]
    connection.sendall(serializer(username=username))
    while True:
        os.system("clear")
        print(f"Welcome:\tUser: {username}\n1)show board\n2)put action\n3)exit")
        s = input('choice: ')
        # show board
        if s == '1':
            connection.sendall(serializer(choice=s, username=username))
            response = deserializer(connection.recv(4096))
            # find max score and won player
            max_score = max(list(response.get("scores").values()))
            won_player = ""
            for player, score in response.get("scores").items():
                if score == max_score:
                    won_player = player
    
            state_response = response.get("state")
            if state_response == GameStates.WAITINGFORPLAYERS.value:
                print("waiting for another player to join the game")
            elif state_response == GameStates.READY.value:
                show_board_and_scores(data=response)

            elif state_response == GameStates.PLAYERLEFT.value:
                print("another player left the game! \n")
                show_board_and_scores(data=response)
            elif state_response == GameStates.FINISHED.value:
                print(f"Game Finished {won_player} Won.")
                show_board_and_scores(data=response)

            c = input("Press Enter to continue: ")
            continue

        # put action
        elif s == '2':
            connection.sendall(serializer(choice=s, username=username))
            response = deserializer(connection.recv(4096))
            turn_response = response.get("turn_player")
            state_response = response.get("state")
            if state_response == GameStates.WAITINGFORPLAYERS.value:
                print("waiting for another player to join the game")
            elif state_response == GameStates.READY.value:
                if turn_response == username:
                    print("its your turn.")
                    x, y, number = map(int, input("Enter x y number\n(put space between each one):\n").split())

                    connection.sendall(serializer(action=[x,y,number]))

                else:
                    print(f"its {turn_response} turn! pleaswe wait")

            elif state_response == GameStates.PLAYERLEFT.value:
                print("another player left the game ")

            elif state_response == GameStates.FINISHED.value:
                print("Game Finished please return to menu and choose 1 to see result!")
    
            c = input("Press Enter to continue: \n")
            continue

        # exit
        elif s == '3':

            connection.sendall(serializer(choice=s))
            print("Bye!")
            break
            sys.exit(0)

        else:
            print('Unknown command!')
            c = input("Press Enter to continue: ")
            continue


if __name__ == "__main__":
    main()
