from clue import Clue, ClueComprehension
from typing import List, Union, Tuple, Dict
from enum import Enum
import itertools
import re


class RelationState(Enum):
    NEUTRAL = ''
    POSITIVE = '+'
    NEGATIVE = '\u2013'


class Category:
    def __init__(self, items: Union[int, List[str]]) -> None:
        if isinstance(items, int):
            self.n_items = items
            self.items = [""] * items
        else:
            self.n_items = len(items)
            self.items = items

    def set_name(self, idx: int, name: str):
        self.items[idx] = name


class CategoryRelationship:
    def __init__(self, a: Category, b: Category) -> None:
        assert a.n_items == b.n_items
        self.cat_row = a
        self.cat_col = b

        self.n = a.n_items
        self.assignment_table = [[RelationState.NEUTRAL] * self.n for _ in range(self.n)]


class Problem:
    def __init__(self, n_categories: int, n_items: int, clues: Union[List[str], None] = None) -> None:
        self.categories = [Category(n_items) for _ in range(n_categories)]
        self.relationships: Dict[Tuple[int, int], CategoryRelationship] = {}
        self.solved_relationships: Dict[Tuple[int, int], List[List[RelationState]]] = {}
        self.clues = [Clue(c, n_items) for c in clues] if clues is not None else None

        for i, row_key in enumerate(itertools.chain([0], reversed(range(2, n_categories)))):
            for col_key in range(1, n_categories - i):
                self.relationships[(row_key, col_key)] = CategoryRelationship(self.categories[row_key], self.categories[col_key])
                self.solved_relationships[(row_key, col_key)] = [[RelationState.NEUTRAL] * n_items for _ in range(n_items)]

    def update(self, desired: bool, relation_key: Tuple[int, int], item_row: int, item_col: int) -> bool:
        # If currently neutral: desired=True -> Positive, desired=False -> Negative
        # If not neutral, reset to neutral
        relationship: CategoryRelationship = self.relationships[relation_key]
        old_state = relationship.assignment_table[item_row][item_col]
        if old_state == RelationState.NEUTRAL:
            new_state = RelationState.POSITIVE if desired else RelationState.NEGATIVE
        else:
            new_state = RelationState.NEUTRAL
            relationship.assignment_table[item_row][item_col] = new_state
            self.draw_conclusions()
            return True

        solved_state = self.solved_relationships[relation_key][item_row][item_col]
        if solved_state != RelationState.NEUTRAL and new_state != solved_state:
            return False

        relationship.assignment_table[item_row][item_col] = new_state
        self.draw_conclusions()
        return True

    def draw_conclusions(self) -> None:
        n_cat = len(self.categories)
        n_item = self.categories[0].n_items
        combined_tables = [[[[RelationState.NEUTRAL] * n_item for _ in range(n_item)] for __ in range(n_cat)] for ___ in range(n_cat)]

        # Copy over user-defined states (and their transpose)
        for key, relation in self.relationships.items():
            for i in range(n_item):
                for j in range(n_item):
                    if relation.assignment_table[i][j] != RelationState.NEUTRAL:
                        combined_tables[key[0]][key[1]][i][j] = relation.assignment_table[i][j]
                        combined_tables[key[1]][key[0]][j][i] = relation.assignment_table[i][j]

        # Initialize the identity relations
        for i in range(n_cat):
            relation = combined_tables[i][i]
            for j in range(n_item):
                for k in range(n_item):
                    if j == k:
                        relation[j][k] = RelationState.POSITIVE
                    else:
                        relation[j][k] = RelationState.NEGATIVE

        # Do logic
        any_changed = self.do_all_logic(combined_tables)
        while any_changed:
            any_changed = self.do_all_logic(combined_tables)

        # Copy results to internal saved state
        for key in self.relationships:
            self.solved_relationships[key] = combined_tables[key[0]][key[1]]

    def count_types(self, line) -> Tuple[int, int, int]:
        n_pos = 0
        n_neg = 0
        n_neu = 0
        for state in line:
            if state == RelationState.NEUTRAL:
                n_neu += 1
            elif state == RelationState.NEGATIVE:
                n_neg += 1
            else:
                n_pos += 1
        return n_pos, n_neg, n_neu

    def step_apply_exactly_one_logic(self, table) -> bool:
        n_item = len(table)
        subtable_changed = False
        for row in table:
            n_pos, n_neg, _ = self.count_types(row)
            if n_pos + n_neg == n_item or (n_pos < 1 and n_neg < n_item - 1):
                continue
            subtable_changed = True
            for i, item in enumerate(row):
                if item != RelationState.NEUTRAL:
                    continue
                elif n_pos == 1:
                    row[i] = RelationState.NEGATIVE
                elif n_neg == n_item - 1:
                    row[i] = RelationState.POSITIVE
        for j, col in enumerate(zip(*table)):
            n_pos, n_neg, _ = self.count_types(col)
            if n_pos + n_neg == n_item or (n_pos < 1 and n_neg < n_item - 1):
                continue
            subtable_changed = True
            for i, item in enumerate(col):
                if item != RelationState.NEUTRAL:
                    continue
                elif n_pos == 1:
                    table[i][j] = RelationState.NEGATIVE
                elif n_neg == n_item - 1:
                    table[i][j] = RelationState.POSITIVE
        return subtable_changed

    def apply_exactly_one_logic(self, combined_table) -> bool:
        any_changed = False
        n_cat = len(combined_table)
        n_item = len(combined_table[0][0])

        for row in combined_table:
            for table in row:
                table_changed = self.step_apply_exactly_one_logic(table)
                while table_changed:
                    any_changed = True
                    table_changed = self.step_apply_exactly_one_logic(table)
        return any_changed

    def step_apply_transposition_logic(self, combined_table, match) -> bool:
        any_changed = False
        for i, row in enumerate(combined_table):
            if i == match[0]:
                for j, table in enumerate(row):
                    if i == j or j == match[1]:
                        continue
                    for k, relation in enumerate(table[match[2]]):
                        if relation == RelationState.NEUTRAL:
                            continue
                        if combined_table[match[1]][j][match[3]][k] == RelationState.NEUTRAL:
                            any_changed = True
                            combined_table[match[1]][j][match[3]][k] = relation
                        if combined_table[j][match[1]][k][match[3]] == RelationState.NEUTRAL:
                            any_changed = True
                            combined_table[j][match[1]][k][match[3]] = relation
            elif i == match[1]:
                for j, table in enumerate(row):
                    if i == j or j == match[0]:
                        continue
                    for k, relation in enumerate(table[match[3]]):
                        if relation == RelationState.NEUTRAL:
                            continue
                        if combined_table[match[0]][j][match[2]][k] == RelationState.NEUTRAL:
                            any_changed = True
                            combined_table[match[0]][j][match[2]][k] = relation
                        if combined_table[j][match[0]][k][match[2]] == RelationState.NEUTRAL:
                            any_changed = True
                            combined_table[j][match[0]][k][match[2]] = relation
            else:
                continue
        return any_changed

    def apply_transposition_logic(self, combined_table) -> bool:
        any_changed = False
        positive_relations = []
        
        for i, row in enumerate(combined_table):
            for j, table in enumerate(row):
                if j >= i:
                    break  # Ignore upper diagonal, we'll handle it with symmetry
                for k, subrow in enumerate(table):
                    for l, item in enumerate(subrow):
                        if item == RelationState.POSITIVE:
                            positive_relations.append((i, j, k, l))

        # If we have a positive relationship categories (0, 1)
        # We can apply (0, 2/3) reltaionships as (1, 2/3) and vice versa
        for match in positive_relations:
            match_changed = self.step_apply_transposition_logic(combined_table, match)
            while match_changed:
                any_changed = True
                match_changed = self.step_apply_transposition_logic(combined_table, match)
        return any_changed

    def step_apply_pseudo_true(self, table) -> bool:
        n_item = len(table)

        # Find all rows with limited numbers of openings in hopes of a pseudo true group
        candidates = [[] for _ in range(int(n_item / 2)-1)]
        for i, row in enumerate(table):
            n_pos, n_neg, n_neu = self.count_types(row)
            if n_pos == 1 or n_neu <= 1 or n_neu > n_item / 2:
                continue
            openings = []
            for j, item in enumerate(row):
                if item == RelationState.NEUTRAL:
                    openings.append(j)
            candidates[n_neu - 2].append((i, openings))

        cum_rows = []
        row_search_hit = False
        for idx, rows in enumerate(candidates):
            if row_search_hit:
                break
            cum_rows += rows
            n_open = idx + 2
            if len(cum_rows) < n_open:
                continue
            # In practice, there are few enough rows that we can brute force search
            for combo in itertools.combinations(cum_rows, n_open):
                combo_idxs = []
                combo_cols = set()
                for i, cols in combo:
                    combo_idxs.append(i)
                    combo_cols.update(set(cols))
                if len(combo_cols) > n_open:
                    continue  # Need too many columns to cover this group
                
                for i in range(n_item):
                    if i in combo_idxs:
                        continue
                    for j in combo_cols:
                        if table[i][j] == RelationState.NEUTRAL:
                            row_search_hit = True
                            table[i][j] = RelationState.NEGATIVE

        # Do it all again for columns
        candidates = [[] for _ in range(int(n_item / 2)-1)]
        for i, col in enumerate(zip(*table)):
            n_pos, n_neg, n_neu = self.count_types(col)
            if n_pos == 1 or n_neu <= 1 or n_neu > n_item / 2:
                continue
            openings = []
            for j, item in enumerate(col):
                if item == RelationState.NEUTRAL:
                    openings.append(j)
            candidates[n_neu - 2].append((i, openings))

        cum_cols = []
        col_search_hit = False
        for idx, cols in enumerate(candidates):
            if col_search_hit:
                break
            cum_cols += cols
            n_open = idx + 2
            if len(cum_cols) < n_open:
                continue
            # In practice, there are few enough cols that we can brute force search
            for combo in itertools.combinations(cum_cols, n_open):
                combo_idxs = []
                combo_rows = set()
                for i, rows in combo:
                    combo_idxs.append(i)
                    combo_rows.update(set(rows))
                if len(combo_rows) > n_open:
                    continue  # Need too many rows to cover this group
                
                for i in range(n_item):
                    if i in combo_idxs:
                        continue
                    for j in combo_rows:
                        if table[j][i] == RelationState.NEUTRAL:
                            col_search_hit = True
                            table[j][i] = RelationState.NEGATIVE

        return row_search_hit or col_search_hit
    
    def apply_pseudo_true(self, combined_table) -> bool:
        any_changed = False
        for row in combined_table:
            for table in row:
                any_changed |= self.step_apply_pseudo_true(table)
        return any_changed

    def step_apply_cross_elimination(self, table_a, table_b) -> List[Tuple[int, int]]:
        n_item = len(table_a)
        cross_elims = []
        for col_a_idx, col_a in enumerate(zip(*table_a)):
            neg_idxs = []
            has_pos = False
            for i, item in enumerate(col_a):
                if item == RelationState.POSITIVE:
                    has_pos = True
                    break
                elif item == RelationState.NEGATIVE:
                    neg_idxs.append(i)
            if has_pos:
                continue
            neg_idxs = set(neg_idxs)

            for col_b_idx, col_b in enumerate(zip(*table_b)):
                b_neg_idxs = []
                b_has_pos = False
                for i, item in enumerate(col_b):
                    if item == RelationState.POSITIVE:
                        b_has_pos = True
                        break
                    elif item == RelationState.NEGATIVE:
                        b_neg_idxs.append(i)
                if b_has_pos:
                    continue
                b_neg_idxs = set(b_neg_idxs)
                combined = neg_idxs.union(b_neg_idxs)
                if len(combined) == n_item:
                    cross_elims.append((col_a_idx, col_b_idx))
        return cross_elims
    
    def apply_cross_elimination(self, combined_table) -> bool:
        any_changed = False
        n_cat = len(combined_table)
        
        for i, row in enumerate(combined_table):
            for j, k in itertools.combinations(range(n_cat), 2):
                if i==j or i==k:
                    continue
                cross_elim_idxs = self.step_apply_cross_elimination(row[j], row[k])
                for pair in cross_elim_idxs:
                    if combined_table[j][k][pair[0]][pair[1]] == RelationState.NEUTRAL:
                        any_changed = True
                        combined_table[j][k][pair[0]][pair[1]] = RelationState.NEGATIVE
                    if combined_table[k][j][pair[1]][pair[0]] == RelationState.NEUTRAL:
                        any_changed = True
                        combined_table[k][j][pair[1]][pair[0]] = RelationState.NEGATIVE
        
        return any_changed
    
    def do_all_logic(self, combined_table) -> bool:
        any_changed = False
        any_changed |= self.apply_exactly_one_logic(combined_table)
        any_changed |= self.apply_transposition_logic(combined_table)
        any_changed |= self.apply_pseudo_true(combined_table)
        any_changed |= self.apply_cross_elimination(combined_table)
        any_changed |= self.process_all_clues(combined_table)
        return any_changed
    
    def update_relation(self, item1, item2, val) -> bool:
        table_key = (item1[0], item2[0])
        item_order = (item1[1], item2[1])
        if table_key not in self.relationships:
            table_key = (item2[0], item1[0])
            item_order = (item2[1], item1[1])
        table = self.relationships[table_key].assignment_table
        if table[item_order[0]][item_order[1]].value == val:
            return False  # nothing to change
        else:
            table[item_order[0]][item_order[1]] = RelationState(val)
            print(item1, item2, val)
            return True

    def process_clue(self, clue: Clue, combined_table) -> bool:
        relations_to_check = clue.solver.relation_queries()
        results = []
        for item1, item2 in relations_to_check:
            val = combined_table[item1[0]][item2[0]][item1[1]][item2[1]].value
            results.append((item1, item2, val))
        
        updates = clue.solver.draw_clue_conclusions(results)
        any_changed = False
        no_neutral = True
        for item1, item2, val in updates:
            if val == '':
                no_neutral = False
                continue
            if combined_table[item1[0]][item2[0]][item1[1]][item2[1]].value != val:
                any_changed = True
                combined_table[item1[0]][item2[0]][item1[1]][item2[1]] = RelationState(val)
            if combined_table[item2[0]][item1[0]][item2[1]][item1[1]].value != val:
                any_changed = True
                combined_table[item2[0]][item1[0]][item2[1]][item1[1]] = RelationState(val)

        if len(updates) > 0 and no_neutral:
            clue.active = False  # Made all conclusions possible
        
        return any_changed

    def process_all_clues(self, combined_table) -> bool:
        any_changed = False
        for clue in self.clues:
            any_changed |= self.process_clue(clue, combined_table)
        return any_changed

    def parse_clues(self) -> None:
        item_to_key = {}

        for i, category in enumerate(self.categories):
            for j, item in enumerate(category.items):
                key = chr(i+65) + str(j+1)
                item_to_key[item] = key

        for clue in self.clues:
            new_clue_text = clue.text
            for name, key in item_to_key.items():
                new_clue_text = re.sub(f" {re.escape(name)}([\., '])", f" {key}\2", new_clue_text)
            new_clue_text = re.sub("\A\d+\. ", "", new_clue_text)

            _, parsed_text = ClueComprehension.do_comprehension(new_clue_text)
            clue.update_solver(parsed_text)
            