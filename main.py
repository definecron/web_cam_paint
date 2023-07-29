
import sys

from PyQt5.QtWidgets import QApplication

from threads import MyMainWindow


def main():
    app=QApplication([])
    window=MyMainWindow()
    window.show()
    sys.exit(app.exec_())

main()






