from abc import ABC, abstractmethod
from typing import Tuple
import itertools
import re


# Don't want circular imports and too lazy to move stae enum to a different file
POSITIVE = '+'
NEGATIVE = '\u2013'
NEUTRAL = ''

NUMERALS = ["two", "three", "four", "five", "six", "seven", "eight", "nine"]


class Clue:
    def __init__(self, text: str, n_item: int) -> None:
        self.text = text
        self.n_item = n_item
        self.active = True
        self.parsed_text = "Unknown"
        self.solver: ClueSolver = UnknownClue()

    def update_solver(self, parsed_clue: str) -> None:
        # Supported clues and their syntax
        # Equal(A1,B2)  i.e. A1 is B2
        # Unique(A1,B2,C3...) i.e. A1, B2, and C3 are all different
        # Either(A1,B2,C3) i.e. A1 is either B2 or C3
        # PairEqual(A1,B2,C3,D4) i.e. A1 is either C3 or D4, B2 is the other one
        # VagueGreater(B2,C3,A) means that B2 is greater than C3 along A (higher index)
        # ExactGreater(B2,C3,A,2) means B2 is exactly 2 steps higher than C3 along A
        self.parsed_text = parsed_clue
        self.active = True
        if parsed_clue.startswith("Equal"):
            items = parsed_clue.split("(")[1][:-1].split(",")
            items = [(ord(item[0])-65, int(item[1:])-1) for item in items]
            self.solver = EquivalenceClue(items[0], items[1])
        elif parsed_clue.startswith("Unique"):
            items = parsed_clue.split("(")[1][:-1].split(",")
            items = [(ord(item[0])-65, int(item[1:])-1) for item in items]
            self.solver = UniquenessClue(*items)
        elif parsed_clue.startswith("Either"):
            items = parsed_clue.split("(")[1][:-1].split(",")
            items = [(ord(item[0])-65, int(item[1:])-1) for item in items]
            self.solver = EitherClue(items[0], items[1], items[2], self.n_item)
        elif parsed_clue.startswith("PairEqual"):
            items = parsed_clue.split("(")[1][:-1].split(",")
            items = [(ord(item[0])-65, int(item[1:])-1) for item in items]
            self.solver = PairEqualClue(items[0], items[1], items[2], items[3], self.n_item)
        elif parsed_clue.startswith("VagueGreater"):
            parts = parsed_clue.split("(")[1][:-1].split(",")
            item_more = (ord(parts[0][0])-65, int(parts[0][1:])-1)
            item_less = (ord(parts[1][0])-65, int(parts[1][1:])-1)
            cat = ord(parts[2]) - 65
            self.solver = VagueGreaterClue(item_more, item_less, cat, self.n_item)
        elif parsed_clue.startswith("ExactGreater"):
            parts = parsed_clue.split("(")[1][:-1].split(",")
            item_more = (ord(parts[0][0])-65, int(parts[0][1:])-1)
            item_less = (ord(parts[1][0])-65, int(parts[1][1:])-1)
            cat = ord(parts[2]) - 65
            diff = int(parts[3])
            self.solver = ExactGreaterClue(item_more, item_less, cat, diff, self.n_item)
        else:
            self.solver = UnknownClue()


class ClueSolver(ABC):
    @abstractmethod
    def relation_queries(self):
        pass

    @abstractmethod
    def draw_clue_conclusions(self, query_response):
        pass


class UnknownClue(ClueSolver):
    def __init__(self) -> None:
        return

    def relation_queries(self):
        return []

    def draw_clue_conclusions(self, query_response):
        return []
    

class EquivalenceClue(ClueSolver):
    def __init__(self, item1: Tuple[int, int], item2: Tuple[int, int]):
        self.item1 = item1
        self.item2 = item2

    def relation_queries(self):
        return []

    def draw_clue_conclusions(self, query_response):
        return [(self.item1, self.item2, POSITIVE)]
    

class UniquenessClue(ClueSolver):
    def __init__(self, *items):
        self.items = list(items)

    def relation_queries(self):
        return []
    
    def draw_clue_conclusions(self, query_response):
        conclusions = []
        for a, b in itertools.combinations(self.items, 2):
            conclusions.append((a, b, NEGATIVE))
        return conclusions


class EitherClue(ClueSolver):
    def __init__(self, primary_item, option1, option2, n_item) -> None:
        self.primary = primary_item
        self.option1 = option1
        self.option2 = option2
        self.n_item = n_item

    def relation_queries(self):
        return [
            (self.primary, self.option1),
            (self.primary, self.option2)
        ]

    def draw_clue_conclusions(self, query_response):
        conclusions = []
        if self.option1[0] == self.option2[0]:
            # Our two options are from the same category
            # is_option1 = (query_response[0][2] == POSITIVE) or (query_response[1][2] == NEGATIVE)
            # is_option2 = (query_response[1][2] == POSITIVE) or (query_response[0][2] == NEGATIVE)
            for i in range(self.n_item):
                # if i == self.option1[1]:
                #     val = POSITIVE if is_option1 else (NEGATIVE if is_option2 else NEUTRAL)
                #     conclusions.append((self.primary, self.option1, val))
                # elif i == self.option2[1]:
                #     val = POSITIVE if is_option2 else (NEGATIVE if is_option1 else NEUTRAL)
                #     conclusions.append((self.primary, self.option2, val))
                # else:
                #     conclusions.append((self.primary, (self.option1[0], i), NEGATIVE))
                # Any other conclusions (like in commented out code) can be handled by grid only logic
                if i == self.option1[1] or i == self.option2[1]:
                    continue
                conclusions.append((self.primary, (self.option1[0], i), NEGATIVE))
        else:
            is_option1 = (query_response[0][2] == POSITIVE) or (query_response[1][2] == NEGATIVE)
            is_option2 = (query_response[1][2] == POSITIVE) or (query_response[0][2] == NEGATIVE)
            val1 = POSITIVE if is_option1 else (NEGATIVE if is_option2 else NEUTRAL)
            val2 = POSITIVE if is_option2 else (NEGATIVE if is_option1 else NEUTRAL)
            conclusions.append((self.primary, self.option1, val1))
            conclusions.append((self.primary, self.option2, val2))
            conclusions.append((self.option1, self.option2, NEGATIVE))
        return conclusions


class PairEqualClue(ClueSolver):
    def __init__(self, item1, item2, item3, item4, n_item) -> None:
        self.pair1 = (item1, item2)
        self.pair2 = (item3, item4)
        self.n_item = n_item

    def relation_queries(self):
        return [
            (self.pair1[0], self.pair2[0]),
            (self.pair1[0], self.pair2[1]),
            (self.pair1[1], self.pair2[0]),
            (self.pair1[1], self.pair2[1])
        ]

    def draw_clue_conclusions(self, query_response):
        if self.pair1[0][0] == self.pair1[1][0]:
            conclusions = [(self.pair2[0], self.pair2[1], NEGATIVE)]
            for i in range(self.n_item):
                if i == self.pair1[0][1] or i == self.pair1[1][1]:
                    continue
                conclusions.append((self.pair2[0], (self.pair1[0][0], i), NEGATIVE))
                conclusions.append((self.pair2[1], (self.pair1[0][0], i), NEGATIVE))
        elif self.pair2[0][0] == self.pair2[1][0]:
            conclusions = [(self.pair1[0], self.pair1[1], NEGATIVE)]
            for i in range(self.n_item):
                if i == self.pair2[0][1] or i == self.pair2[1][1]:
                    continue
                conclusions.append((self.pair1[0], (self.pair2[0][0], i), NEGATIVE))
                conclusions.append((self.pair1[1], (self.pair2[0][0], i), NEGATIVE))
        else:
            conclusions = [
                (self.pair1[0], self.pair1[1], NEGATIVE),
                (self.pair2[0], self.pair2[1], NEGATIVE)
            ]

            straight_match = query_response[0][2] == POSITIVE or query_response[1][2] == NEGATIVE \
                            or query_response[2][2] == NEGATIVE or query_response[3][2] == POSITIVE
            cross_match = query_response[0][2] == NEGATIVE or query_response[1][2] == POSITIVE \
                        or query_response[2][2] == POSITIVE or query_response[3][2] == NEGATIVE
            
            if straight_match:
                vals = [POSITIVE, NEGATIVE, NEGATIVE, POSITIVE]
            elif cross_match:
                vals = [NEGATIVE, POSITIVE, POSITIVE, NEGATIVE]
            else:
                vals = [NEUTRAL, NEUTRAL, NEUTRAL, NEUTRAL]

            conclusions.append((self.pair1[0], self.pair2[0], vals[0]))
            conclusions.append((self.pair1[0], self.pair2[1], vals[1]))
            conclusions.append((self.pair1[1], self.pair2[0], vals[2]))
            conclusions.append((self.pair1[1], self.pair2[1], vals[3]))

        return conclusions


class VagueGreaterClue(ClueSolver):
    def __init__(self, item_more, item_less, cat_axis, n_item) -> None:
        self.item_less = item_less
        self.item_more = item_more
        self.cat_axis = cat_axis
        self.n_item = n_item

    def relation_queries(self):
        less_queries = []
        more_queries = []
        for i in range(self.n_item):
            less_queries.append((self.item_less, (self.cat_axis, i)))
            more_queries.append((self.item_more, (self.cat_axis, i)))
        return less_queries + more_queries

    def draw_clue_conclusions(self, query_response):
        conclusions = []
        # If the two items are in different categories, we know they are different
        if self.item_less[0] != self.item_more[0]:
            conclusions.append((self.item_less, self.item_more, NEGATIVE))

        less_min_possible = None
        less_positive_relation = None
        more_max_possible = None
        more_positive_relation = None
        for i in range(self.n_item):
            less_relation = query_response[i][2]
            if less_relation == POSITIVE:
                less_positive_relation = i
            elif less_relation == NEUTRAL and (less_min_possible is None or i < less_min_possible):
                less_min_possible = i

            more_relation = query_response[i + self.n_item][2]
            if more_relation == POSITIVE:
                more_positive_relation = i
            elif more_relation == NEUTRAL and (more_max_possible is None or i > more_max_possible):
                more_max_possible = i

        if less_positive_relation is not None and more_positive_relation is not None:
            # These items are already solved in the axis this clue is about
            pass
        elif less_positive_relation is not None:
            # Can finish out this clue so don't leave neutrals
            for i in range(less_positive_relation + 1):
                conclusions.append((self.item_more, (self.cat_axis, i), NEGATIVE))
        elif more_positive_relation is not None:
            # Can finish out this clue so don't leave neutrals
            for i in range(more_positive_relation, self.n_item):
                conclusions.append((self.item_less, (self.cat_axis, i), NEGATIVE))
        else:
            for i in range(self.n_item):
                less_relation = NEGATIVE if i >= more_max_possible else NEUTRAL
                more_relation = NEGATIVE if i <= less_min_possible else NEUTRAL
                target_item = (self.cat_axis, i)
                conclusions.append((self.item_less, target_item, less_relation))
                conclusions.append((self.item_more, target_item, more_relation))

        return conclusions


class ExactGreaterClue(ClueSolver):
    def __init__(self, item_more, item_less, cat_axis, diff, n_item) -> None:
        self.item_less = item_less
        self.item_more = item_more
        self.cat_axis = cat_axis
        self.diff = diff
        self.n_item = n_item

    def relation_queries(self):
        less_queries = []
        more_queries = []
        for i in range(self.n_item):
            less_queries.append((self.item_less, (self.cat_axis, i)))
            more_queries.append((self.item_more, (self.cat_axis, i)))
        return less_queries + more_queries

    def draw_clue_conclusions(self, query_response):
        conclusions = []
        # If the two items are in different categories, we know they are different
        if self.item_less[0] != self.item_more[0]:
            conclusions.append((self.item_less, self.item_more, NEGATIVE))

        less_possibilities = set()
        less_positive_relation = None
        more_possibilities = set()
        more_positive_relation = None
        for i in range(self.n_item):
            less_relation = query_response[i][2]
            if less_relation == POSITIVE:
                less_positive_relation = i
            elif less_relation == NEUTRAL:
                less_possibilities.add(i)

            more_relation = query_response[i + self.n_item][2]
            if more_relation == POSITIVE:
                more_positive_relation = i
            elif more_relation == NEUTRAL:
                more_possibilities.add(i)

        if less_positive_relation is not None and more_positive_relation is not None:
            # These items are already solved in the axis this clue is about
            pass
        elif less_positive_relation is not None:
            conclusions.append((self.item_more, (self.cat_axis, less_positive_relation + self.diff), POSITIVE))
        elif more_positive_relation is not None:
            conclusions.append((self.item_less, (self.cat_axis, more_positive_relation - self.diff), POSITIVE))
        else:
            # TODO logic for matching up blanks
            for i in range(self.n_item):
                less_val = NEUTRAL if (i + self.diff) in more_possibilities else NEGATIVE
                more_val = NEUTRAL if (i - self.diff) in less_possibilities else NEGATIVE
                conclusions.append((self.item_less, (self.cat_axis, i), less_val))
                conclusions.append((self.item_more, (self.cat_axis, i), more_val))

        return conclusions


class ClueComprehension:
    def do_comprehension(text: str) -> Tuple[bool, str]:
        success, parsed_text = ClueComprehension.check_either_or(text)
        if success:
            return True, parsed_text
        success, parsed_text = ClueComprehension.check_neither_nor(text)
        if success:
            return True, parsed_text
        success, parsed_text = ClueComprehension.check_pair_equal(text)
        if success:
            return True, parsed_text
        success, parsed_text = ClueComprehension.check_negation(text)
        if success:
            return True, parsed_text
        success, parsed_text = ClueComprehension.check_many_unique(text)
        if success:
            return True, parsed_text
        return False, text

    def check_either_or(text: str) -> Tuple[bool, str]:
        pattern = re.compile(".*([A-Z]\d+).*(?:is|was) either.*([A-Z]\d+).*or.*([A-Z]\d+).*")
        result = pattern.match(text)
        if result is None:
            return False, ""
        else:
            parsed = f"Either({result.group(1)},{result.group(2)},{result.group(3)})"
            return True, parsed
    
    def check_neither_nor(text: str) -> Tuple[bool, str]:
        pattern = re.compile(".*[nN]either.*([A-Z]\d+).*nor.*([A-Z]\d+).*([A-Z]\d+).*")
        result = pattern.match(text)
        if result is None:
            return False, ""
        else:
            parsed = f"Unique({result.group(1)},{result.group(2)},{result.group(3)})"
            return True, parsed

    def check_pair_equal(text: str) -> Tuple[bool, str]:
        pattern = re.compile(".*[oO]f.*([A-Z]\d+).*and.*([A-Z]\d+).*one.*([A-Z]\d+).*the other.*([A-Z]\d+).*")
        result = pattern.match(text)
        if result is None:
            return False, ""
        else:
            parsed = f"PairEqual({result.group(1)},{result.group(2)},{result.group(3)},{result.group(4)})"
            return True, parsed
        
    def check_negation(text: str) -> Tuple[bool, str]:
        pattern = re.compile(".*([A-Z]\d+).*n't.*([A-Z]\d+).*")
        result = pattern.match(text)
        if result is None:
            return False, ""
        else:
            parsed = f"Unique({result.group(1)},{result.group(2)})"
            return True, parsed
        
    def check_many_unique(text: str) -> Tuple[bool, str]:
        if "different" in text.lower() or "unique" in text.lower():
            pattern = re.compile("[A-Z]\d+")
            results = pattern.findall(text)
            parsed = f"Unique({','.join(results)})"
            return True, parsed
        for num in NUMERALS:
            if f"the {num}" in text.lower():
                pattern = re.compile("[A-Z]\d+")
                results = pattern.findall(text)
                parsed = f"Unique({','.join(results)})"
                return True, parsed
        return False, ""
