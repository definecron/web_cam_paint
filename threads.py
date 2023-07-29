import cv2

from PyQt5 import QtCore
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import QMainWindow


from ui import Ui_MainWindow
from classes import WindowManager, Display, TouchScreen


class MyThread(QtCore.QThread):
    my_signal = QtCore.pyqtSignal(QImage)
    
    def __init__(self):
        super().__init__()
        
        self.props=None

        self.cap=None
        self.w_manager=None
        self.display=None
        self.touch_screen=None
        
        self.init()
        
    def init(self):
        self.cap = cv2.VideoCapture(1)

        frame = self.get_frame()
        self.w_manager = WindowManager(frame.shape[0], frame.shape[1])
        
        
        self.display=Display(frame.shape[0], frame.shape[1])
        self.display.do_resize(1200, 1200)
        self.touch_screen=TouchScreen()
        
        
        
    def run(self):
        while True:
            frame = self.get_frame()
            
            coords, mode=self.touch_screen.get_cursor_params(frame) # возвращает кортеж coords, mode
            # если курсор "нажат", то передаём его параметры диспетчеру окна, который диспетчирует их своим элементам
            if mode:
                self.w_manager.dispatch_cursor_click(coords)
            frame=self.display.draw_display(frame, self.w_manager, (coords, mode))
            self.emit_frame(frame)
            
        

    def get_frame(self):
        success, frame = self.cap.read()
        frame = cv2.flip(frame, -1)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.flip(frame, 3)
        return frame
    
    def emit_frame(self, frame):
        height1, width1, channel1 = frame.shape
        step1 = channel1 * width1
        img_pixmap = QImage(frame.data, width1, height1, step1, QImage.Format_RGB888)
        self.set_cam_props()
        # передача frame через сигнал в главнй поток
        self.my_signal.emit(img_pixmap)
    
    def set_cam_props(self):
        if self.props:
            if self.cap:
                self.cap.set(10, self.props['br'])
                self.cap.set(11, self.props['contr'])
                self.cap.set(12, self.props['satur'])
                self.cap.set(13, self.props['hue'])


class MyMainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.my_thread = MyThread()

        self.my_thread.my_signal.connect(self.on_change_thread, QtCore.Qt.QueuedConnection)
        
        self.setupUi(self)
        
        self.brightSlider.valueChanged.connect(self.on_change_props)
        self.contrastSlider.valueChanged.connect(self.on_change_props)
        self.hueSlider.valueChanged.connect(self.on_change_props)
        self.saturationSlider.valueChanged.connect(self.on_change_props)
        
        self.my_thread.start()
    
    def on_change_props(self):
        br=self.brightSlider.value()
        contr=self.contrastSlider.value()
        hue=self.hueSlider.value()
        satur = self.saturationSlider.value()
        
        self.brValueLabel.setText(str(br))
        self.contValueLabel.setText(str(contr))
        self.hueValueLabel.setText(str(hue))
        self.satValueLabel.setText((str(satur)))
        
        
        d={'br':br, 'contr':contr, 'hue':hue,'satur': satur}
        self.my_thread.props=d
        

    def on_change_thread(self, imgQImage):
        self.imgHolstLabel.setPixmap(QPixmap.fromImage(imgQImage))




