from puzzle_io import problem_from_path
from gui import MainWindow

import sys
import argparse
import os
from PySide2.QtWidgets import QApplication


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--number", "-n", type=int, default=0)
    args = parser.parse_args()
    html_path = os.path.join(".", "sample_problems", f"problem_{args.number:02}.html")
    prob = problem_from_path(html_path)

    app = QApplication(sys.argv)
    window = MainWindow(problem_=prob)
    window.show()
    app.exec_()