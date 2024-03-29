import asyncio
import random
import itertools
import collections
from player_status import PlayerStatus


class PokerServer(asyncio.Protocol):
    # スタティック変数
    players_address = []                # 全プレイヤーのアドレス
    players_name = {}                   # 全プレイヤーの名前
    players_money = {}                  # 全プレイヤーの所持金
    players_hand = {}                   # 全プレイヤーの手札
    players_changed_card_flags = {}     # 全プレイヤーの手札が山札と交換したカードかどうか
    players_status = {}                 # 全プレイヤーの状態
    player_dealer = None                # ディーラー（最後に手番が来るプレイヤー）のアドレス
    player_in_turn = None               # 手番のプレイヤーのアドレス
    player_next_turn = None             # 次に手番が来るプレイヤーのアドレス
    max_num_players = 3                 # 参加できるプレイヤー数の上限
    cur_num_players = 0                 # 現在参加しているプレイヤー数
    deck = None                         # 山札
    winners = None                      # 勝利したプレイヤーのアドレスのリスト


    def judge_hand(self, hand):
        """手札の役を判定する関数"""
        # handの数字だけを取り出したリスト
        hand_nums = [x[0] for x in hand]
        hand_nums.sort()
        # handのマークだけを取り出したリスト
        hand_marks = [x[1] for x in hand]

        # 要素の重複をカウントした辞書
        count_num = collections.Counter(hand_nums)
        count_mark = collections.Counter(hand_marks)

        # ストレートフラッシュ判定
        if (len(count_mark) == 1 and (hand_nums == list(range(hand_nums[0], hand_nums[0]+5)) or hand_nums == [1, 10, 11, 12, 13])):
            return [1, "ストレートフラッシュ"]

        # フォーカード判定
        if (max(count_num.values()) == 4):
            return [2, "フォーカード"]

        # フルハウス判定
        if (max(count_num.values()) == 3 and min(count_num.values()) == 2):
            return [3, "フルハウス"]

        # フラッシュ判定
        if (len(count_mark) == 1):
            return [4, "フラッシュ"]

        # ストレート判定
        if (hand_nums == list(range(hand_nums[0], hand_nums[0]+5)) or hand_nums == [1, 10, 11, 12, 13]):
            return [5, "ストレート"]

        # スリーカード判定
        if (max(count_num.values()) == 3):
            return [6, "スリーカード"]

        # ツーペア判定
        if (len(count_num) == 3):
            return [7, "ツーペア"]

        # ワンペア判定
        if (len(count_num) == 4):
            return [8, "ワンペア"]

        # ハイカード判定
        return [9, "ハイカード"]


    def judge_winner(self):
        """プレイヤーのハンドから勝敗を判定する"""
        hands = PokerServer.players_hand

        # 各プレイヤーハンドの役のリスト
        player_judge_hand = [self.judge_hand(hand) for hand in hands.values()]

        # 各プレイヤーハンドの役のランク（強さ）のみを抜き出したリスト
        player_hand_ranks = [x[0] for x in player_judge_hand]

        # 勝者のindex
        winner_player = [i for i, x in enumerate(player_hand_ranks) if x == min(player_hand_ranks)]

        # 勝者のアドレスのリスト
        winners = [list(hands.keys())[x] for x in winner_player]
        return winners


    def _initialize_deck(self):
        """山札を初期化する関数"""
        suits = ['spade', 'heart', 'diamond', 'club']
        PokerServer.deck = list(itertools.product(range(1, 14), suits))


    def _draw_card(self, num_cards, address):
        """カードを山札から引く関数"""
        PokerServer.players_hand[address] = PokerServer.deck[:num_cards]
        del PokerServer.deck[:num_cards]


    def _change_card(self, card):
        """カードを捨てて，山札から引く関数"""
        # player_hand = PokerServer.players_hand[(self.client_address, self.client_port)]
        card_idx = PokerServer.players_hand[(self.client_address, self.client_port)].index(card)
        del PokerServer.players_hand[(self.client_address, self.client_port)][card_idx]
        del PokerServer.players_changed_card_flags[(self.client_address, self.client_port)][card_idx]
        # del self.changed_card_flags[card_idx]
        PokerServer.players_hand[(self.client_address, self.client_port)].append(PokerServer.deck[0])
        del PokerServer.deck[0]
        PokerServer.players_changed_card_flags[(self.client_address, self.client_port)].append(True)
        # self.changed_card_flags.append(True)


    def _card_number_and_suit_to_str(self, card):
        """カードの情報を文字列として返す関数"""
        convert_number = {
            1: 'A', 2: '2', 3: '3', 4: '4', 5: '5',
            6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
            11: 'J', 12: 'Q', 13: 'K'}
        convert_suit = {'spade': '♤', 'heart': '♡', 'diamond': '♢', 'club': '♧'}

        number, suit = card
        return convert_suit[suit] + convert_number[number]


    def _hand_to_str(self, hand):
        """手札の情報を文字列として返す関数"""
        string = ''
        for card in hand:
            string += self._card_number_and_suit_to_str(card) + ' '
        return string


    def _result_to_str(self):
        """ゲームの結果を文字列として返す関数"""
        string = ''
        for address in PokerServer.players_address:
            player_name = PokerServer.players_name[address]
            hand = PokerServer.players_hand[address]

            if address in PokerServer.winners:
                win_or_lose = 'Win!'
            else:
                win_or_lose = 'Lose...'

            string += player_name + ': '
            string += self._hand_to_str(hand)
            string += win_or_lose + '\n'
        return string


    def connection_made(self, transport):
        """クライアントからの接続があったときに呼ばれるイベントハンドラ"""
        # 接続をインスタンス変数として保存する
        self.transport = transport

        # 接続元の情報を取得する
        client_address, client_port = self.transport.get_extra_info('peername')
        self.client_address = client_address
        self.client_port = client_port

        # 接続元の情報を出力する
        print('New client: {0}:{1}'.format(client_address, client_port))

        if PokerServer.cur_num_players < PokerServer.max_num_players:
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.REGIST_NAME
            PokerServer.cur_num_players += 1
            PokerServer.players_address.append((client_address, client_port))

            send_msg = '0あなたの名前を入力してください。'
            self.transport.write(send_msg.encode())
        else:
            self.transport.write('1参加人数の上限を超えているので，参加できませんでした'.encode())
            self.transport.close()


    def data_received(self, data):
        """クライアントからデータを受信したときに呼ばれるイベントハンドラ"""
        # 接続元の情報を取得する
        client_address = self.client_address
        client_port = self.client_port

        # 接続元プレイヤーの現在の状態によって処理を変える
        player_status = PokerServer.players_status[(client_address, client_port)]
        if player_status == PlayerStatus.REGIST_NAME:
            player_name = data.decode()
            PokerServer.players_name[(client_address, client_port)] = player_name
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.WAIT_PLAYER

            send_msg = 'ポーカーの世界へようこそ！' + player_name + 'さん'
            self.transport.write(send_msg.encode())
        elif player_status == PlayerStatus.WAIT_PLAYER:
            # 誰かが名前を登録している途中か調べる
            ragisting_name_flag = False
            for player_status in PokerServer.players_status.values():
                if player_status == PlayerStatus.REGIST_NAME:
                    ragisting_name_flag = True

            if PokerServer.cur_num_players < PokerServer.max_num_players or ragisting_name_flag:
                self.transport.write('0プレイヤーが集まるのを待っています。'.encode())
            else:
                self.transport.write('1プレイヤーが揃いました！'.encode())
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_PREPARE
        elif player_status == PlayerStatus.GAME_PREPARE:
            # すべてのプレイヤーのうち、少なくとも1人がゲームを開始していないときは処理を終了する
            for player_status in PokerServer.players_status.values():
                if player_status in (PlayerStatus.REGIST_NAME, PlayerStatus.WAIT_PLAYER, PlayerStatus.GAME_RESULT):
                    self.transport.write('0'.encode())
                    return

            # 以下の処理を１回だけ行うための条件
            if (client_address, client_port) == PokerServer.players_address[0]:
                print('ゲームを始めるよ！！')
                # プレイヤーの順番を決める
                PokerServer.player_in_turn = PokerServer.players_address[0]
                PokerServer.player_next_turn = None
                PokerServer.player_dealer = PokerServer.players_address[-1]

                # 山札を初期化する
                self._initialize_deck()

                # 山札をシャッフルする
                random.shuffle(PokerServer.deck)

                # 手札を初期化する
                PokerServer.players_hand = {}
                PokerServer.players_changed_card_flags = {}

                # 全プレイヤーが順番に山札からカードを引く
                for address in PokerServer.players_address:
                    self._draw_card(5, address)
                    PokerServer.players_changed_card_flags[address] = [False] * 5

                # 勝利したプレイヤーのリストをNoneにする
                PokerServer.winners = None

            # プレイヤーの状態を変更する
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_LOOK_FIRST_HAND

            self.transport.write('1ゲームを開始します！'.encode())
        elif player_status == PlayerStatus.GAME_LOOK_FIRST_HAND:
            # すべてのプレイヤーのうち、少なくとも1人が手札を見ていないときは処理を終了する
            for player_status in PokerServer.players_status.values():
                if PlayerStatus == PlayerStatus.GAME_PREPARE:
                    self.transport.write('0'.encode())
                    return

            send_msg = ''
            send_msg += '山札からカードを5枚引きます。\n'
            send_msg += '手札: '
            try: # TODO: たまにここでキーエラーが起きるので原因を解明する
                for card in PokerServer.players_hand[(client_address, client_port)]:
                    send_msg += self._card_number_and_suit_to_str(card) + ' '
            except KeyError:
                print('players_hand:', PokerServer.players_hand)
                raise KeyError
            self.transport.write(send_msg.encode())

            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_BEGINNING_OF_TURN
        elif player_status == PlayerStatus.GAME_BEGINNING_OF_TURN:
            # すべてのプレイヤーのうち、少なくとも1人が手札を見ている最中のときは処理を終了する
            for player_status in PokerServer.players_status.values():
                if player_status in (PlayerStatus.GAME_LOOK_FIRST_HAND, PlayerStatus.GAME_END_OF_TURN):
                    self.transport.write('0'.encode())
                    return

            # 手番のプレイヤーを決める
            if PokerServer.player_next_turn is not None:
                PokerServer.player_in_turn = PokerServer.player_next_turn

            # プレイヤーの状態を変更する
            if (client_address, client_port) == PokerServer.player_in_turn:
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_MY_TURN
                self.transport.write('1'.encode())
            else:
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_OTHER_PLAYER_TURN
                self.transport.write('2'.encode())
        elif player_status == PlayerStatus.GAME_MY_TURN:
            # 手番のプレイヤーの処理を行う
            send_msg = ''
            send_msg += 'あなたの番です。\n'
            self.transport.write(send_msg.encode())
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_START_CHANGE_CARD
        elif player_status == PlayerStatus.GAME_OTHER_PLAYER_TURN:
            # 手番ではないプレイヤーの処理を行う
            if PokerServer.players_status[PokerServer.player_in_turn] in (
                PlayerStatus.GAME_BEGINNING_OF_TURN, PlayerStatus.GAME_MY_TURN,
                PlayerStatus.GAME_START_CHANGE_CARD, PlayerStatus.GAME_SELECT_CHANGE_CARD):
                # 他のプレイヤーの手番のとき
                send_msg = '0'
                send_msg += PokerServer.players_name[PokerServer.player_in_turn]
                send_msg += 'さんの番です。'
                self.transport.write(send_msg.encode())
            elif PokerServer.players_status[PokerServer.player_in_turn] == PlayerStatus.GAME_END_OF_TURN:
                # 他のプレイヤーの手番が終了したとき
                self.transport.write('1'.encode())
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_END_OF_TURN
            else:
                raise ValueError
        elif player_status == PlayerStatus.GAME_START_CHANGE_CARD:
            # 手番のプレイヤーのカード交換処理を行う
            send_msg = '\n交換するカードの番号を選んでください。\n'
            send_msg += '0. 交換しない\n'
            idx = 1

            player_hand = PokerServer.players_hand[(client_address, client_port)]
            player_changed_card_flags = PokerServer.players_changed_card_flags[(client_address, client_port)]
            for card_idx, card in enumerate(player_hand):
                if not player_changed_card_flags[card_idx]:
                    send_msg += str(idx) + '. '
                    send_msg += self._card_number_and_suit_to_str(card) + '\n'
                    # self.can_change_cards[idx] = card
                    idx += 1

            self.transport.write(send_msg.encode())
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_SELECT_CHANGE_CARD
        elif player_status == PlayerStatus.GAME_SELECT_CHANGE_CARD:
            # 手番のプレイヤーのカード交換後の処理を行う

            # プレイヤーから交換するカードの番号を受け取る
            select_idx = int(data.decode())

            # プレイヤーの手札を取得する
            player_hand = PokerServer.players_hand[(client_address, client_port)]

            # 交換可能なカードの個数を取得する
            num_can_change_cards = PokerServer.players_changed_card_flags[(client_address, client_port)].count(False)

            if select_idx == 0 or num_can_change_cards == 0:
                # カードの交換が終了したときの処理
                send_msg = '1手札の交換を終了します。\n手札: '
                for card in player_hand:
                    send_msg += self._card_number_and_suit_to_str(card) + ' '

                self.transport.write(send_msg.encode())

                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_END_OF_TURN
            elif select_idx <= num_can_change_cards:
                # カードの交換を行うときの処理
                # 交換するカードを取得する
                change_card = player_hand[select_idx - 1]

                # 選択したカードを捨て、山札からカードを引く
                self._change_card(change_card)

                self.transport.write('0'.encode())
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_START_CHANGE_CARD
            else:
                # プレイヤーの入力が正しくないときの処理
                raise NotImplementedError
        elif player_status == PlayerStatus.GAME_END_OF_TURN:
            # プレイヤーの手番が終了したときの処理
            # 全プレイヤーのターン中の処理が終了するのを待つ

            # TODO: この時点で誰かがGAME_BIGINNING_OF_TURNステータスである可能性はゼロじゃないかも。その場合の対処をしてない
            for player_status in PokerServer.players_status.values():
                if player_status in (PlayerStatus.GAME_MY_TURN, PlayerStatus.GAME_OTHER_PLAYER_TURN,
                                     PlayerStatus.GAME_START_CHANGE_CARD, PlayerStatus.GAME_SELECT_CHANGE_CARD):
                    self.transport.write('0'.encode())
                    return

            if PokerServer.player_in_turn == PokerServer.player_dealer:
                if (client_address, client_port) == PokerServer.player_in_turn:
                    PokerServer.winners = self.judge_winner()
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_RESULT
                self.transport.write('2'.encode())
            else:
                if (client_address, client_port) == PokerServer.player_in_turn:
                    # 手番を次のプレイヤーにする
                    player_idx = PokerServer.players_address.index((client_address, client_port))
                    PokerServer.player_next_turn = PokerServer.players_address[
                        (player_idx + 1) % PokerServer.max_num_players]

                self.transport.write('1'.encode())
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_BEGINNING_OF_TURN
        elif player_status == PlayerStatus.GAME_RESULT:
            for player_status in PokerServer.players_status.values():
                if player_status == PlayerStatus.GAME_END_OF_TURN:
                    self.transport.write('0'.encode())
                    return

            send_msg = '1結果を表示します\n'
            send_msg += self._result_to_str()
            self.transport.write(send_msg.encode())
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_PREPARE


    def connection_lost(self, exc):
        """クライアントとの接続が切れたときに呼ばれるイベントハンドラ"""
        # 接続が切れたら後始末をする
        client_address, client_port = self.transport.get_extra_info('peername')
        print('Bye-Bye: {0}:{1}'.format(client_address, client_port))
        self.transport.close()


def main():
    host = 'localhost'
    port = 50000

    # イベントループを用意する
    ev_loop = asyncio.get_event_loop()
    # 指定したアドレスとポートでサーバを作る
    factory = ev_loop.create_server(PokerServer, host, port)
    # サーバを起動する
    server = ev_loop.run_until_complete(factory)

    try:
        # イベントループを起動する
        ev_loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        # 後始末
        server.close()
        ev_loop.run_until_complete(server.wait_closed())
        ev_loop.close()
        print('\nServer Closed')


if __name__ == '__main__':
    main()
