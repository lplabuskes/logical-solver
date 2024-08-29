import problem

from PySide2.QtCore import Qt, QSize, Signal
from PySide2.QtGui import QMouseEvent, QPainter, QFontMetrics
from PySide2.QtWidgets import QApplication, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout
from PySide2.QtWidgets import QPushButton, QLineEdit, QLabel, QInputDialog

import sys
import itertools
import textwrap
from typing import Tuple, Union


# Credit https://stackoverflow.com/a/67515822
class VerticalLabel(QLabel):
    def __init__(self, *args, **kwargs):
        QLabel.__init__(self, *args, **kwargs)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.translate(0, self.height())
        painter.rotate(-90)
        # calculate the size of the font
        fm = QFontMetrics(painter.font())
        xoffset = int(fm.boundingRect(self.text()).width()/2)
        yoffset = int(fm.boundingRect(self.text()).height()/2)
        x = int(self.width()/2) + yoffset
        y = int(self.height()/2) - xoffset
        # because we rotated the label, x affects the vertical placement, and y affects the horizontal
        painter.drawText(y, x, self.text())
        painter.end()
        
    def minimumSizeHint(self):
        size = QLabel.minimumSizeHint(self)
        return QSize(size.height(), size.width())

    def sizeHint(self):
        size = QLabel.sizeHint(self)
        return QSize(size.height(), size.width())


class RightClickButton(QPushButton):
    rightclicked = Signal()

    def __init__(self, *args, **kwargs) -> None:
        QPushButton.__init__(self, *args, **kwargs)

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if e.button() == Qt.RightButton:
            self.rightclicked.emit()
        else:
            super(RightClickButton, self).mousePressEvent(e)


class MainWindow(QWidget):
    def __init__(self, parent: QWidget | None = None, problem_: Union[problem.Problem, None] = None) -> None:
        super().__init__(parent)

        if problem_ is None:
            self.n_categories = 4
            self.n_items = 5
            self.problem = problem.Problem(self.n_categories, self.n_items)
        else:
            self.problem = problem_
            self.n_categories = len(self.problem.categories)
            self.n_items = self.problem.categories[0].n_items

        self.setup_gui()
        self.problem.draw_conclusions()
        self.update_buttons()
        self.update_clues()

    def le_callback(self, name: str, cat_idx: int, item_idx: int) -> None:
        self.problem.categories[cat_idx].set_name(item_idx, name)
        self.lo_category_labels[cat_idx].itemAt(item_idx).widget().setText(name)
        self.update()

    def update_buttons(self):
        for key, relation in self.problem.relationships.items():
            for i, row in enumerate(relation.assignment_table):
                for j, item in enumerate(row):
                    btn = self.lo_relation_grids[key].itemAtPosition(i, j).widget()
                    btn.setText(item.value)
                    if item != problem.RelationState.NEUTRAL:
                        btn.setStyleSheet("color: Black; font-size: 18pt;")
                    elif self.problem.solved_relationships[key][i][j] != problem.RelationState.NEUTRAL:
                        btn.setText(self.problem.solved_relationships[key][i][j].value)
                        btn.setStyleSheet("color: Gray; font-size: 18pt;")

    def update_clues(self):
        for idx, clue in enumerate(self.problem.clues):
            btn = self.lo_clues.itemAt(idx).widget()
            if clue.active:
                btn.setStyleSheet("border: none; text-align: left; color: Black; text-decoration: none;")
            else:
                btn.setStyleSheet("border: none; text-align: left; color: Gray; text-decoration: line-through;")
                    
    def bn_callback(self, desired: bool, key: Tuple[int, int], item_row: int, item_col: int) -> None:
        success = self.problem.update(desired, key, item_row, item_col)
        if success:
            self.update_buttons()
            self.update_clues()
            self.update()
        else:
            print("Contradiction!")

    def clue_callback(self, idx: int, trick_qt1, trick_qt2):
        btn: QPushButton = self.lo_clues.itemAt(idx).widget()
        old_state = self.problem.clues[idx].active
        self.problem.clues[idx].active = not old_state
        if old_state:
            btn.setStyleSheet("border: none; text-align: left; color: Gray; text-decoration: line-through;")
        else:
            btn.setStyleSheet("border: none; text-align: left; color: Black; text-decoration: none;")

    def edit_clue_callback(self, idx: int):
        text, ok = QInputDialog().getText(self, f"Update Clue {idx+1} Parsing",
                                          f"Current Parsing: {self.problem.clues[idx].parsed_text}\nNew Parsing:")
        if ok and text:
            self.problem.clues[idx].update_solver(text)
            self.problem.draw_conclusions()
            self.update_buttons()
            self.update_clues()

    def setup_gui(self) -> None:
        self.lo_main_grid = QGridLayout()

        self.lo_relation_grids = {}
        for key, relation in self.problem.relationships.items():
            lo_relation = QGridLayout()
            lo_relation.setSpacing(0)
            for i, row in enumerate(relation.assignment_table):
                for j, state in enumerate(row):
                    state_button = RightClickButton(text=state.value)
                    state_button.setFixedSize(30, 30)
                    state_button.clicked.connect(lambda k=key, i=i, j=j: self.bn_callback(False, k, i, j))
                    state_button.rightclicked.connect(lambda k=key, i=i, j=j: self.bn_callback(True, k, i, j))
                    lo_relation.addWidget(state_button, i, j)
            self.lo_relation_grids[key] = lo_relation
        
        self.lo_category_edits = []
        self.lo_category_labels = []
        for cat_idx, category in enumerate(self.problem.categories):
            lo_edits = QVBoxLayout()
            lo_labels = QHBoxLayout()
            for item_idx, item in enumerate(category.items):
                le = QLineEdit()
                le.setText(item)
                le.textChanged.connect(lambda s, cat=cat_idx, item=item_idx: self.le_callback(s, cat, item))
                lo_edits.addWidget(le)
                lbl = VerticalLabel(text=item)
                lo_labels.addWidget(lbl)
            self.lo_category_edits.append(lo_edits)
            self.lo_category_labels.append(lo_labels)

        assert self.n_categories >= 2
        self.lo_main_grid.addLayout(self.lo_category_edits[1], 0, 0)
        self.lo_main_grid.addLayout(self.lo_category_edits[0], 1, 0)
        for gui_idx, cat_idx in enumerate(reversed(range(2, self.n_categories))):
            self.lo_main_grid.addLayout(self.lo_category_edits[cat_idx], gui_idx + 2, 0)

        for cat_idx in range(1, self.n_categories):
            self.lo_main_grid.addLayout(self.lo_category_labels[cat_idx], 0, cat_idx)

        for gui_row, cat_row in enumerate(itertools.chain([0], reversed(range(2, self.n_categories)))):
            for col_idx in range(1, self.n_categories - gui_row):
                if (cat_row, col_idx) in self.lo_relation_grids:
                    key = (cat_row, col_idx)
                else:
                    key = (col_idx, cat_row) 
                self.lo_main_grid.addLayout(self.lo_relation_grids[key], gui_row + 1, col_idx)

        self.lo_clues = QVBoxLayout()
        if self.problem.clues is not None:
            for idx, clue in enumerate(self.problem.clues):
                text = '\n'.join(textwrap.wrap(clue.text, 40))
                btn_clue = RightClickButton(text=text)
                btn_clue.setStyleSheet("border: none; text-align: left; color: Black; text-decoration: none;")
                # Need a lambda to get the right arguments to callback, need dumb shenanigans to get the right signal
                btn_clue.clicked.connect(lambda arg=idx, tmp1=None, tmp2=None: self.clue_callback(arg, tmp1, tmp2))
                btn_clue.rightclicked.connect(lambda arg=idx: self.edit_clue_callback(arg))
                self.lo_clues.addWidget(btn_clue)
            self.lo_main_grid.addLayout(self.lo_clues, 0, self.n_categories, self.n_categories, 1)
        
        self.setLayout(self.lo_main_grid)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()