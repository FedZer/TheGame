import csv
import random
from abc import ABC, abstractmethod
from enum import Enum


def get_cards_per_player(n_players):
    cards_mapping = {1: 8, 2: 7}
    return cards_mapping.get(n_players, 6)


class Deck:
    def __init__(self):
        self.deck = list(range(2, 99))
        self.__shuffle()

    def __shuffle(self):
        random.shuffle(self.deck)

    def draw(self, n=1):
        if len(self.deck) > n:
            drawn_cards = [self.deck.pop() for _ in range(n)]
        else:
            drawn_cards = self.deck
            self.deck = []
        return drawn_cards

    def is_empty(self):
        return len(self.deck) == 0


class Player(ABC):
    def __init__(self, handler, player_id):
        self.cards = []
        self.handler = handler
        self.id = player_id

    def draw(self, cards_drawn):
        self.cards += cards_drawn

    def _get_legal_moves(self, stacks):
        moves = []
        for n_c, card in enumerate(self.cards):
            for n_s, stack in enumerate(stacks):
                if stack.check_valid(card):
                    moves.append((n_c, n_s, stack.calc_distance(card)))
        return moves

    @abstractmethod
    def play(self, stacks, forced_one_card):
        pass

    @abstractmethod
    def end_turn_logic(self, stacks):
        pass

    @abstractmethod
    def personal_end_turn_logic(self, stacks):
        pass


class PlayerRandom(Player):
    def __init__(self, handler, player_id):
        super().__init__(handler, player_id)

    def play(self, stacks, forced_one_card):
        blocked = self.__play_one_random(stacks)
        if not forced_one_card:
            blocked = blocked or self.__play_one_random(stacks)
        # n_played_cards, blocked
        return 1 if forced_one_card else 2, blocked

    def __play_one_random(self, stacks):
        moves = self._get_legal_moves(stacks)
        if len(moves) == 0:
            return True
        index = random.randrange(len(moves))
        if SHOW_GAME:
            print("Played: " + str(self.cards[moves[index][0]]))
        stacks[moves[index][1]].add(self.cards.pop(moves[index][0]))
        return False

    def end_turn_logic(self, stacks):
        pass

    def personal_end_turn_logic(self, stacks):
        pass


class PlayerNaive(Player):
    def __init__(self, handler, player_id):
        super().__init__(handler, player_id)

    def play(self, stacks, forced_one_card):
        blocked = self.__play_one_naive(stacks)
        if not forced_one_card:
            blocked = blocked or self.__play_one_naive(stacks)
        # n_played_cards, blocked
        return 1 if forced_one_card else 2, blocked

    def __play_one_naive(self, stacks):
        moves = self._get_legal_moves(stacks)
        if len(moves) == 0:
            return True
        min_move = min(moves, key=lambda x: x[2])
        if SHOW_GAME:
            print("Played: " + str(self.cards[min_move[0]]))
        stacks[min_move[1]].add(self.cards.pop(min_move[0]))
        return False

    def end_turn_logic(self, stacks):
        pass

    def personal_end_turn_logic(self, stacks):
        pass


class AbstractPlayerPriority(Player, ABC):
    def __init__(self, handler, player_id):
        super().__init__(handler, player_id)

    def play(self, stacks, forced_one_card):
        blocked = self.__play_one_priority(stacks)
        if not forced_one_card:
            blocked = blocked or self.__play_one_priority(stacks)
        # n_played_cards, blocked
        return 1 if forced_one_card else 2, blocked

    def __play_one_priority(self, stacks):
        moves = self._get_legal_moves(stacks)
        if len(moves) == 0:
            return True
        sorted_moves = sorted(moves, key=lambda x: x[2])
        if sorted_moves[0][2] == -1:
            stacks[sorted_moves[0][1]].add(self.cards.pop(sorted_moves[0][0]))
            return False
        for move in sorted_moves:
            if not self.handler.check_asked_priority(move[1], self.id):
                stacks[move[1]].add(self.cards.pop(move[0]))
                return False
        stacks[sorted_moves[0][1]].add(self.cards.pop(sorted_moves[0][0]))
        return False

    def _ask_priority(self, stacks):
        self.handler.clean_old_priorities(self.id)
        moves = self._get_legal_moves(stacks)
        sorted_moves = sorted(moves, key=lambda x: x[2])
        priority_moves = [move for move in sorted_moves if move[2] == -1]
        for move in priority_moves:
            self.handler.ask_priority(move[1], self.id)
        if SHOW_GAME:
            print(self.handler)

    def end_turn_logic(self, stacks):
        pass

    def personal_end_turn_logic(self, stacks):
        pass


class PlayerSleepPriority(AbstractPlayerPriority):
    def __init__(self, handler, player_id):
        super().__init__(handler, player_id)

    def end_turn_logic(self, stacks):
        pass

    def personal_end_turn_logic(self, stacks):
        self._ask_priority(stacks)


class PlayerPriority(AbstractPlayerPriority):
    def __init__(self, handler, player_id):
        super().__init__(handler, player_id)

    def end_turn_logic(self, stacks):
        self._ask_priority(stacks)

    def personal_end_turn_logic(self, stacks):
        pass


class Stack:
    def __init__(self, goes_up):
        self.goes_up = goes_up
        self.current = 1 if goes_up else 99

    def add(self, card):
        if not self.check_valid(card):
            raise NameError("Wrong Card on Stack")
        self.current = card

    def check_valid(self, card):
        valid_condition = (
                (self.goes_up and (self.current < card or self.current - 10 == card)) or
                (not self.goes_up and (self.current > card or self.current + 10 == card))
        )
        return valid_condition

    def calc_distance(self, card):
        if self.goes_up:
            if self.current - 10 == card:
                return -1
            return card - self.current
        else:
            if self.current + 10 == card:
                return -1
            return self.current - card

    def get_state(self):
        return self.current, self.goes_up


class Handler:
    def __init__(self, n_players, stacks):
        self.n_players = n_players
        self.stacks = stacks
        self.priority = [[0 for _ in range(n_players)] for _ in range(len(self.stacks))]
        self.players = []

    def set_players(self, players):
        self.players = players

    def ask_priority(self, to_reserve, player_id):
        self.priority[to_reserve][player_id] = 1

    def clean_old_priorities(self, player_id):
        for stack_pr in self.priority:
            stack_pr[player_id] = 0

    def check_asked_priority(self, stack_n, player_id):
        for i, val in enumerate(self.priority[stack_n]):
            if i != player_id:
                if val == 1:
                    return True
        return False

    def end_turn_logic(self):
        for player in self.players:
            player.end_turn_logic(self.stacks)

    def __str__(self):
        output = ""
        for stack_pr in self.priority:
            output += f"{stack_pr} - "
        return output[:-3]


class Game:
    def __init__(self, n_players):
        self.stacks = []
        self.deck = None
        self.cards_per_player = None
        self.handler = None
        self.players = []

        self.__initialize_game(n_players)

    def reset(self, n_players):
        self.__initialize_game(n_players)

    def __initialize_game(self, n_players):
        self.stacks = [Stack(True) for _ in range(2)] + [Stack(False) for _ in range(2)]
        self.deck = Deck()
        self.cards_per_player = get_cards_per_player(n_players)
        self.handler = Handler(n_players, self.stacks)
        match PLAYER_TYPE:
            case PlayerType.RANDOM:
                self.players = [PlayerRandom(self.handler, i) for i in range(n_players)]
            case PlayerType.NAIVE:
                self.players = [PlayerNaive(self.handler, i) for i in range(n_players)]
            case PlayerType.SLEEP_PRIORITY:
                self.players = [PlayerSleepPriority(self.handler, i) for i in range(n_players)]
            case PlayerType.PRIORITY:
                self.players = [PlayerPriority(self.handler, i) for i in range(n_players)]
        self.handler.set_players(self.players)

        self.__distribute_cards()

    def __distribute_cards(self):
        for player in self.players:
            drawn = self.deck.draw(self.cards_per_player)
            player.draw(drawn)

    def play(self):
        lost = False
        while not lost:
            for player in self.players:
                if SHOW_GAME:
                    self.__show_turn(player)
                n_played_cards, blocked = player.play(self.stacks, self.deck.is_empty())
                if blocked:
                    lost = True
                    break
                if not self.deck.is_empty():
                    drawn = self.deck.draw(n_played_cards)
                    player.draw(drawn)
                player.personal_end_turn_logic(self.stacks)
                self.handler.end_turn_logic()

    def get_result(self):
        n_cards = len(self.deck.deck)
        for player in self.players:
            n_cards += len(player.cards)
        return n_cards

    def __show_turn(self, player):
        up = u'\u2191'
        down = u'\u2193'
        for stack in self.stacks:
            val, goes_up = stack.get_state()
            print(str(val) + (up if goes_up else down), end="  ")
        print("")
        print(player.cards)


# FLAGS:
class PlayerType(Enum):
    RANDOM = 0
    NAIVE = 1
    SLEEP_PRIORITY = 2
    PRIORITY = 3


PLAYER_TYPE = PlayerType.PRIORITY
SHOW_GAME = False

results = []


def main():
    # play_one()
    play_many(1000)
    # save_results_to_file()


def play_one():
    game = Game(5)
    game.play()
    results.append(game.get_result())
    game.reset(5)
    game.play()
    results.append(game.get_result())
    print(results)


def play_many(n_games=500):
    win = 0
    index = 0
    game = Game(5)
    while index < n_games:
        index += 1
        print(index)
        game.reset(5)
        game.play()
        result = game.get_result()
        if result == 0:
            win += 1
        results.append(result)
    print_win_rate()


def print_win_rate():
    num_wins = results.count(0)
    win_rate = (num_wins / len(results)) * 100
    print("Win rate:", win_rate, "%")


def save_results_to_file():
    with open("results.csv", 'w', newline='') as file_csv:
        writer = csv.writer(file_csv)
        writer.writerow(["cards"])
        for val in results:
            writer.writerow([val])


if __name__ == '__main__':
    main()
