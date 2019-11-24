import sys
import socket
from time import sleep
from player_status import PlayerStatus


def client(host, port):
    def enter_process():
        """入室処理"""
        sock.connect((host, port))
        msg = sock.recv(1024).decode()
        print(msg) # ポーカーの世界へようこそ

    def wait_player_process():
        """プレイヤーを待っている間の処理"""
        print_flag = False
        while True:
            sock.send(b'0')
            data = sock.recv(1024).decode()
            flag, msg = data[0], data[1:]
            if flag == '0' and not print_flag:
                # プレイヤーが集まっていないときの処理
                print(msg)
                print_flag = True
            elif flag == '1':
                # プレイヤーが集まったときの処理
                print(msg)
                break
            sleep(0.1)

    def game_process():
        """ゲームの処理"""
        game_prepare_process()
        game_look_first_hand_process()

        while True:
            sock.send(b'0')
            flag = sock.recv(1024).decode()

            if flag == '0':
                continue
            elif flag == '1':
                # 自分の手番の場合の処理
                game_my_turn_process()
                is_game_over = game_end_of_turn_process()
            elif flag == '2':
                # 他のプレイヤーの手番の場合の処理
                game_other_player_turn_process()
                is_game_over = game_end_of_turn_process()
            else:
                raise ValueError

            if is_game_over:
                return

    def game_prepare_process():
        while True:
            sock.send(b'0')
            data = sock.recv(1024).decode()
            flag, msg = data[0], data[1:]

            if flag == '0':
                continue
            elif flag == '1':
                print(msg)
                return
            else:
                raise ValueError

    def game_look_first_hand_process():
        """ゲームの最初に手札を見る処理"""
        sock.send(b'0')
        msg = sock.recv(1024).decode()
        print(msg)

    def game_end_of_turn_process():
        """ターン終わりの処理。ゲームが終了したかどうかを返す"""
        while True:
            sock.send(b'0')
            flag = sock.recv(1024).decode()
            if flag == '0':
                continue
            elif flag == '1':
                return False
            elif flag == '2':
                game_judge_process()
                return True
            else:
                raise ValueError


    def game_judge_process():
        """役判定時の処理"""
        while True:
            sock.send(b'0')
            data = sock.recv(1024).decode()
            flag, msg = data[0], data[1:]
            if flag == '0':
                continue
            elif flag == '1':
                print(msg)
                return
            else:
                raise ValueError


    def game_my_turn_process():
        """自分の手番の場合の処理"""
        sock.send(b'0')
        msg = sock.recv(1024).decode()
        print(msg)
        while True:
            # カード交換処理
            sock.send(b'0')
            # カードの交換を行うメッセージを受け取る
            msg = sock.recv(1024).decode()
            print(msg)
            print('> ', end='')
            change_card = input()
            # 交換するカードの番号を送る
            sock.send(change_card.encode())

            # カード交換後の処理
            data = sock.recv(1024).decode()
            flag, msg = data[0], data[1:]

            if flag == '0':     # さらにカードの交換を行う場合
                print(msg)
            elif flag == '1':   # カードの交換を終了する場合
                print(msg)
                return
            else:
                raise ValueError

    def game_other_player_turn_process():
        """他のプレイヤーの手番の場合の処理"""
        print_flag = False
        while True:
            sock.send(b'0')
            data = sock.recv(1024).decode()
            flag, msg = data[0], data[1:]
            if flag == '0':
                # 他のプレイヤーの手番のとき
                if not print_flag:
                    print(msg)
                    print_flag = True
            elif flag == '1':
                # 他のプレイヤーの手番が終了したとき
                return
            else:
                raise ValueError

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            # 入室処理
            enter_process()

            # プレイヤー待機処理
            wait_player_process()

            # ゲームの処理
            while True:
                game_process()
        except:
            sys.exit(sys.exc_info()[1])


def main():
    host = 'localhost'
    port = 50000
    client(host, port)


if __name__ == '__main__':
    main()
