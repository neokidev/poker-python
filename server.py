import asyncio
import random
import itertools
from player_status import PlayerStatus


class PokerServer(asyncio.Protocol):
    # 変数
    player_name = None          # プレイヤーのアドレス情報
    player_status = None        # プレイヤーの状態
    player_money = 10000        # プレイヤーの所持金
    changed_card_flags = None   # プレイヤーの手札のそれぞれが山札のカードと交換したものかどうか
    can_change_cards = {}       # プレイヤーの手札のうち交換可能なカード
    is_first_turn = True        # プレイヤーの最初の手番かどうか

    # スタティック変数
    players_hand = {}           # プレイヤーの手札
    players_address = []        # 全プレイヤーのアドレス
    players_status = {}         # 全プレイヤーの状態
    player_dealer = None        # ディーラー（最後に手番が来るプレイヤー）のアドレス
    player_in_turn = None       # 手番のプレイヤーのアドレス
    player_next_turn = None     # 次に手番が来るプレイヤーのアドレス
    max_num_players = 3         # 参加できるプレイヤー数の上限
    cur_num_players = 0         # 現在参加しているプレイヤー数
    # is_game_started = False     # ゲームが開始しているかどうか
    numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]           # 使用するカードナンバー
    suits = ['spade', 'heart', 'diamond', 'club']                   # 使用するマーク
    deck = list(itertools.product(range(1, 14), suits))             # 山札


    def _draw_card(self, num_cards, address):
        """カードを山札から引く関数"""
        PokerServer.players_hand[address] = PokerServer.deck[:num_cards]
        # self.player_hand = PokerServer.deck[:num_cards]
        del PokerServer.deck[:num_cards]


    def _change_card(self, card):
        """カードを捨てて，山札から引く関数"""
        # player_hand = PokerServer.players_hand[(self.client_address, self.client_port)]
        card_idx = PokerServer.players_hand[(self.client_address, self.client_port)].index(card)
        del PokerServer.players_hand[(self.client_address, self.client_port)][card_idx]
        del self.changed_card_flags[card_idx]
        PokerServer.players_hand[(self.client_address, self.client_port)].append(PokerServer.deck[0])
        del PokerServer.deck[0]
        self.changed_card_flags.append(True)


    def _card_number_and_suit_to_str(self, card):
        """カードの情報を文字列として返す関数"""
        convert_number = {
            1: 'A', 2: '2', 3: '3', 4: '4', 5: '5',
            6: '6', 7: '7', 8: '8', 9: '9', 10: '10',
            11: 'J', 12: 'Q', 13: 'K'}
        convert_suit = {'spade': '♤', 'heart': '♡', 'diamond': '♢', 'club': '♧'}

        number, suit = card
        return convert_suit[suit] + convert_number[number]


    def _define_player_name(self):
        """プレイヤーの名前を自動的に決める関数"""
        self.player_name = chr(ord('A') + PokerServer.cur_num_players)


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
            self._define_player_name()
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.WAIT_PLAYER
            PokerServer.cur_num_players += 1
            PokerServer.players_address.append((client_address, client_port))
            self.transport.write(('ポーカーの世界へようこそ！あなたは' + self.player_name + 'さんです。').encode())
        else:
            self.transport.write('参加人数の上限を超えているので，参加できませんでした'.encode())
            self.transport.close()


    def data_received(self, data):
        '''
        if self.player_name == 'A':
            print('Aさん: ', self.changed_card_flags)
        '''
        # print('ステータス:', PokerServer.players_status)
        """クライアントからデータを受信したときに呼ばれるイベントハンドラ"""
        # 接続元の情報を取得する
        client_address = self.client_address
        client_port = self.client_port

        # 接続元プレイヤーの現在の状態によって処理を変える
        player_status = PokerServer.players_status[(client_address, client_port)]
        if player_status == PlayerStatus.WAIT_PLAYER:
            if PokerServer.cur_num_players < PokerServer.max_num_players:
                self.transport.write('0プレイヤーが集まるのを待っています。'.encode())
            else:
                self.transport.write('1プレイヤーが揃いました！'.encode())
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_PREPARE
        elif player_status == PlayerStatus.GAME_PREPARE:
            # すべてのプレイヤーのうち、少なくとも1人がゲームを開始していないときは処理を終了する
            for player_status in PokerServer.players_status.values():
                if player_status in (PlayerStatus.WAIT_PLAYER, PlayerStatus.GAME_JUDGE_HAND):
                    self.transport.write('0'.encode())
                    return

            # 以下の処理を１回だけ行うための条件
            if (client_address, client_port) == PokerServer.players_address[0]:
                # 山札をシャッフルする
                random.shuffle(PokerServer.deck)

                # プレイヤーの順番を決める
                PokerServer.player_in_turn = PokerServer.players_address[0]
                PokerServer.player_dealer = PokerServer.players_address[-1]

                # 全プレイヤーが順番に山札からカードを引く
                for address in PokerServer.players_address:
                    self._draw_card(5, address)

            self.changed_card_flags = [False] * 5

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
                print(PokerServer.players_hand)
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
                self.transport.write('0他のプレイヤーの番です。'.encode())
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
            for card_idx, card in enumerate(PokerServer.players_hand[(client_address, client_port)]):
                if not self.changed_card_flags[card_idx]:
                    send_msg += str(idx) + '. '
                    send_msg += self._card_number_and_suit_to_str(card) + '\n'
                    self.can_change_cards[idx] = card
                    idx += 1
            self.transport.write(send_msg.encode())
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_SELECT_CHANGE_CARD
        elif player_status == PlayerStatus.GAME_SELECT_CHANGE_CARD:
            # 手番のプレイヤーのカード交換後の処理を行う

            # プレイヤーから交換するカードの番号を受け取る
            select_idx = int(data.decode())

            # 交換可能なカードの個数を取得する
            num_can_change_cards = len(self.can_change_cards)

            if select_idx == 0 or num_can_change_cards == 0:
                # カードの交換が終了したときの処理
                send_msg = '1手札の交換を終了します。\n手札: '
                for card in PokerServer.players_hand[(client_address, client_port)]:
                    send_msg += self._card_number_and_suit_to_str(card) + ' '

                # 最初の手番かどうかのフラグをFalseにする
                if self.is_first_turn:
                    self.is_first_turn = False

                self.transport.write(send_msg.encode())

                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_END_OF_TURN
            elif select_idx <= num_can_change_cards:
                # カードの交換を行うときの処理
                # 交換するカードを取得する
                change_card = self.can_change_cards[select_idx]

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
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_JUDGE_HAND
                self.transport.write('2'.encode())
            else:
                if (client_address, client_port) == PokerServer.player_in_turn:
                    # 手番を次のプレイヤーにする
                    player_idx = PokerServer.players_address.index((client_address, client_port))
                    PokerServer.player_next_turn = PokerServer.players_address[
                        (player_idx + 1) % PokerServer.max_num_players]

                self.transport.write('1'.encode())
                PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_BEGINNING_OF_TURN
        elif player_status == PlayerStatus.GAME_JUDGE_HAND:
            for player_status in PokerServer.players_status.values():
                if player_status == PlayerStatus.GAME_END_OF_TURN:
                    self.transport.write('0'.encode())
                    return

            self.transport.write('1Aの勝ち！！'.encode())
            PokerServer.players_status[(client_address, client_port)] = PlayerStatus.GAME_PREPARE


    def connection_lost(self, exc):
        """クライアントとの接続が切れたときに呼ばれるイベントハンドラ"""
        # 接続が切れたら後始末をする
        client_address, client_port = self.transport.get_extra_info('peername')
        print('Bye-Bye: {0}:{1}'.format(client_address, client_port))
        self.transport.close()


class EchoServer(asyncio.Protocol):
    def connection_made(self, transport):
        """クライアントからの接続があったときに呼ばれるイベントハンドラ"""
        # 接続をインスタンス変数として保存する
        self.transport = transport

        # 接続元の情報を出力する
        client_address, client_port = self.transport.get_extra_info('peername')
        print('New client: {0}:{1}'.format(client_address, client_port))

    def data_received(self, data):
        """クライアントからデータを受信したときに呼ばれるイベントハンドラ"""
        # 受信した内容を出力する
        client_address, client_port = self.transport.get_extra_info('peername')
        print('Recv: {0} to {1}:{2}'.format(data,
                                            client_address,
                                            client_port))

        # 受信したのと同じ内容を返信する
        self.transport.write(data)
        print('Send: {0} to {1}:{2}'.format(data,
                                            client_address,
                                            client_port))

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
