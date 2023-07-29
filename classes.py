from abc import ABC, abstractmethod

import cv2
import mediapipe as mp
import numpy as np
import math

colorsSet={"red":(255, 0,0), "green":(0,255,0), "blue":(0,0,255)}
toolsSet={"brush":0, "eraser":1}


# интерфейс для обработки "клика" по своей области  и метод определения координат в своей области
class Clickable(ABC):
    # реакция на клик курсора
    @abstractmethod
    def click_update(self, coords):
        ...
    
    # проверка находится ли координаты внутри объекта
    @abstractmethod
    def in_area(self, coords):
        ...

# реализует интерфейс для отдачи параметров для рисования  дисплеем и
class Drawable(ABC):
    @abstractmethod
    def get_params_for_drawing(self):
        ...
   



class Observer(ABC):
    def __init__(self):
        self._observers=[]
    def attach(self, func):
        self._observers.append(func)
    def detach(self, func):
        self._observers.remove(func)
    def notify(self, color):
        for obs in self._observers:
            obs(color)


class Button(Observer, Drawable, Clickable):
    def __init__(self, id, x0, y0, width, height, color):
        super().__init__()
        self.id, self.x0, self.y0, self.width, self.height, self.color = id, x0, y0,width, height, color
        self.state=False # нажата или отпущена
    def get_params_for_drawing(self):
        return {'type':'but','data':{'x0': self.x0,
         'y0': self.y0,
         'width': self.width,
         'height': self.height,
         'color': self.color}}
    # переключение состояния
    def click_update(self, coords):
        self.notify(self.color)
    
    def in_area(self, coords):
        if self.x0 <= coords[0] <= self.x0+self.width and self.y0 <= coords[1] <= self.y0 + self.height:
            return True
    
    def set_pressed_state(self):
        self.state=True
    
    def set_reliesed_state(self):
        self.state = False
    
    def get_state(self):
        return self.state

# диспетчер компоновки холста и органов управления в кадре
class WindowManager:
    def __init__(self, frame_width, frame_height):
        self.frame_width, self.frame_height = frame_width, frame_height
        self.control_elements=[]
        self.brush = Brush()
        
        # добавление холста для рисования
        self.drawing = Drawing((frame_width, frame_height), self.brush)
        self.add_buttons()
    
    # добавление элементов  управления - кнопок
    def add_buttons(self):
        # добавление кнопок
        width=100
        height=40
        for i, color in enumerate(colorsSet):
            control_element = Button(i, i*width,0, width, height, colorsSet[color])
            self.control_elements.append(control_element)
            # назначение кисти в качестве наблюдателя для каждой кнопки
            control_element.attach(self.brush.set_color)
        l=len(self.control_elements)
        eraser=Button(l, l*width, 0, width, height, (255,255,255))
        eraser.attach(self.drawing.clear_draw)
        self.control_elements.append(eraser)
        
    # простой массив  всех элементов для отрисовки на экране
    def get_elements_for_drawing_on_display(self):
        data= [self.drawing]
        data.extend(self.control_elements)
        
        return data
    
    def dispatch_cursor_click(self, coords):
        pass
        for el in self.get_elements_for_drawing_on_display():
            if el.in_area(coords):
                el.click_update(coords)
        # нарисовать на холсте
        # self.drawing.draw_on_holst(coords, self.brush)


# хранит состояние кисти
class Brush:
    def __init__(self):
        super().__init__()
        self. color=colorsSet['red']
        self.radius=6
    def set_color(self, color):
        print('Brush.update:', f'{color=}')
        self.color=color
    
# отвечает за отрисовку всех компонентов на кадре: курсора, кнопок, маски
class Display:
    def __init__(self, d_width, d_height):
        # в данном случае сюда передаются размеры кадра с камеры, поскольку он и будет всем экраном
        self.d_width, self.d_height = d_width, d_height
        self.is_do_resize=False
        self.resize_h_to=0
        self.resize_w_to=0
        
    
    # отрисовка всех элементов
    def draw_display(self, frame, w_manager: WindowManager, cursor_params):

        for el in w_manager.get_elements_for_drawing_on_display():
            pars=el.get_params_for_drawing()
            if pars['type']=='img':
                gray = cv2.cvtColor(pars['data'], cv2.COLOR_BGR2GRAY)
                mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY)[1]
                mask_inv = cv2.bitwise_not(mask)
                
                frame = cv2.bitwise_and(frame, frame, mask=mask_inv)
                frame = cv2.bitwise_or(frame, pars['data'])
                
            elif pars['type']=='but':
                frame = cv2.rectangle(frame, (pars['data']['x0'], pars['data']['y0']),
                                      (pars['data']['x0']+pars['data']['width'],
                                       pars['data']['y0']+pars['data']['height']),
                                      (pars['data']['color']), -1)
        # отрисовка курсора
        coords, mode = cursor_params

        if mode:
            frame = cv2.circle(frame, coords, 10, (255, 255, 255), 3)
        else:
            frame = cv2.circle(frame, coords, 5, (255, 255, 255), -1)
            
        if self.is_do_resize:
            frame = self.resize_frame(frame)
        return frame
    def do_resize(self, h, w):
        self.is_do_resize=True
        self.resize_h_to=h
        self.resize_w_to=w
        
        
    def resize_frame(self, frame):
        h,w=self.resize_h_to, self.resize_w_to
        fh, fw, fz = frame.shape
        if w < fw or h < fh:
            return frame
        g = fw / fh
        
        if w / h > g:  # значит нужно ресайзить до высоты h, потому что ширина окна будет больше
            frame = cv2.resize(frame, (int(fw * h / fh), h),
                               interpolation=cv2.INTER_AREA)  # (width, height), interpolation=cv2.INTER_AREA
        else:  # ресайзить до ширины
            frame = cv2.resize(frame, (w, int(fh * (w / fw))), interpolation=cv2.INTER_AREA)
        return frame
# отвечает за определение координат и режима курсора.
class TouchScreen:
    def __init__(self):
        self.cursor = Cursor()
    def get_cursor_params(self, frame):
        return self.cursor.get_cursor_params(frame)
    
# содержит функциональность определения координат и режима курсора. Здесь инкапсулирована процедура поиска при помощи нейросети
class Cursor(Drawable):
    def __init__(self):
        super().__init__()
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.5, min_tracking_confidence=0.5)
        self.coords=None
        self.mode=False
        
    def get_params_for_drawing(self):
        return {'type':'cur', 'data':{'coords':self.coords,'mode':self.mode}}
        pass
   
    # распознаётся рука и возвращается координаты указательного пальца
    def get_cursor_params(self, frame):
        results = self.hands.process(frame)
        # требуется для масштабирования координат пальцев
        ih, iw, ic = frame.shape
        

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # эта строчка отвечает за рисование руки. можно комментировать или раскомментировать
                # self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                for id, lm in enumerate(hand_landmarks.landmark):
                    if id == 8:
                        # print("id=8")
                        self.coords = coords8 = (int(lm.x * iw), int(lm.y * ih))
                        # print((int(lm.x * iw), int(lm.y * ih)))
                    if id == 12:
                        coords12 = (int(lm.x * iw), int(lm.y * ih))
                    if id == 16:
                        coords16 = (int(lm.x * iw), int(lm.y * ih))
                    if id == 20:
                        coords20 = (int(lm.x * iw), int(lm.y * ih))
                # вычисление mode. Если расстояние между 8 и 12 больше, чем между 12 и 16 и 16 и 20, то mode true
                dis_8_12 = self.distance(coords12, coords8)
                dis_12_16 = self.distance(coords16, coords12)
                dis_16_20 = self.distance(coords20, coords16)
                if dis_8_12 > dis_12_16 * 3 and dis_8_12 > dis_16_20 * 3:
                    self.mode = True
                # print(f"dis_8_12={dis_8_12}, dis_12_16={dis_12_16}")
        else:
            self.coords=self.mode=None
        return self.coords, self.mode
    
    # определяет, сжата ладонь или открыта
    @staticmethod
    def distance(coords1, coords2):
        # return int(math.sqrt((coords2[0] - coords1[0]) ** 2 + (coords2[1] - coords1[1]) ** 2))
        return int(math.hypot(coords2[0] - coords1[0], coords2[1] - coords1[1]))

# отвечает за сохранение нарисованного в виде отдельного холста и
class Drawing(Drawable, Clickable):
    def __init__(self, resolution, brush):
        super().__init__()
        self.brush=brush
        self.resolution = resolution
        self.holst = np.zeros(self.resolution + (3,), np.uint8)
    
    def get_params_for_drawing(self):
        return {'type':'img', "data":self.holst}
    
    def click_update(self,coords):
        self.draw_on_holst(coords, self.brush)
        
    
    def in_area(self, coords):
        # в данном случае холст совпадае тс размером экрана, поэтому всегд True
        return True
        
   


    def draw_on_holst(self, coords, brush):
        # добавление контура к маске
        # обязательно значение 255, так как потом требуется инверсия, чтобы 255 превратилось в 0
        # рисуем на холсте

        self.holst = cv2.circle(self.holst, coords, brush.radius, brush.color, -1)



    def clear_draw(self, color=None):

        self.holst = np.zeros(self.resolution + (3,), np.uint8)





    
        
        