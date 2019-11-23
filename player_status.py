class PlayerStatus():
    WAIT_PLAYER = 1
    GAME_PREPARE = 9
    GAME_LOOK_FIRST_HAND = 2
    GAME_BEGINNING_OF_TURN = 10
    # GAME_READY = 2
    GAME_MY_TURN = 3
    GAME_OTHER_PLAYER_TURN = 4
    GAME_END_OF_TURN = 5
    GAME_START_CHANGE_CARD = 6
    GAME_SELECT_CHANGE_CARD = 7
    GAME_JUDGE_HAND = 8

    @staticmethod
    def is_game_status(player_status):
        """ゲーム中のステータスかどうか調べる関数"""
        return player_status in (
            PlayerStatus.GAME_READY, PlayerStatus.GAME_MY_TURN,
            PlayerStatus.GAME_OTHER_PLAYER_TURN,
            PlayerStatus.GAME_START_CHANGE_CARD, PlayerStatus.GAME_SELECT_CHANGE_CARD)