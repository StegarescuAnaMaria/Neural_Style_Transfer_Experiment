from random import choice
import random
from PIL import ImageDraw, Image as img
import threading
import numpy as np
import torch
from torchvision import models, transforms

import os
import sys
import logging
import PyQt5
from PyQt5 import QtWidgets
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt
import os
import qrc_resources as resource
import math
import cv2
from matplotlib.image import imread
import tensorflow as tf
import time
from tensorflow.keras.models import Model
from tensorflow.keras import layers, losses

from argparse import ArgumentParser
"""
parser = ArgumentParser(description='Example')
parser.add_argument('–gpu', type=int, default=[0,1], nargs='+', help='used gpu')

args = parser.parse_args()
os.environ["CUDA_VISIBLE_DEVICES"] = ','.join(str(x) for x in args.gpu)
"""
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = '0'

dev = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
print(dev)

def texture_func(size):
    path_text = "./resources/textures"
    images = ["brush1.png", "brush2.png", "brush3.png", "brush4.png", "brush5.png", "brush6.png", "brush7.png", "brush8.png",
              "brush8.png", "brush9.png", "brush10.png", "brush11.png"]
    lista_img = []
    for image in images:
        imagine = QtGui.QImage(os.path.join(path_text, image))
        imagine = imagine.scaled(size, QtCore.Qt.KeepAspectRatio)
        lista_img.append(imagine)
    return lista_img


def icon_func():
    lista_icon = [QtGui.QIcon(":brush1"), QtGui.QIcon(":brush2"), QtGui.QIcon(":brush3"), QtGui.QIcon(":brush4"),
                  QtGui.QIcon(":brush5"), QtGui.QIcon(":brush6"), QtGui.QIcon(":brush7"), QtGui.QIcon(":brush8"),
                  QtGui.QIcon(":brush9"), QtGui.QIcon(":brush10"), QtGui.QIcon(":brush11")]
    return lista_icon


class MyProxyStyle(QtWidgets.QProxyStyle):
    pass
    def pixelMetric(self, QStyle_PixelMetric, option=None, widget=None):

        if QStyle_PixelMetric == QtWidgets.QStyle.PM_SmallIconSize:
            return 25
        else:
            return QtWidgets.QProxyStyle.pixelMetric(self, QStyle_PixelMetric, option, widget)



class ScribbleArea(QtWidgets.QWidget):
    def __init__(self, format, parent=0):
        super().__init__()
        self.width = 700
        self.height = 700
        self.parent = parent
        self.modified = False
        self.scribbling = False
        self.myPenColor = QtGui.QColor(0, 0, 255, 255)                        #blue
        self.myPenWidth = 1
        self.cap = Qt.RoundCap
        self.join = Qt.RoundJoin
        self.line = Qt.SolidLine
        self.pen = QtGui.QPen(self.myPenColor, self.myPenWidth, self.line, self.cap, self.join)
        self.hasPen = True                                         #foloseste creionul la moment (are creionul activ)
        self.hasEraser = False                                                   #foloseste radiera
        self.hasBrush = False
        self.hasBlur = False
        self.blurRadius = 7
        self.hasBucket = False
        self.erasing = False
        self.hasCrop = False
        self.rubberBand = None
        self.croppedRect = None
        self.eraserWidth = 5
        self.lastPoint = None
        self.format = format
        self.rgb = QtGui.QImage.Format_RGB32
        self.rgba = QtGui.QImage.Format_RGBA64
        self.setAttribute(QtCore.Qt.WA_StaticContents)
        self.brush = None
        self.texture = None
        self.texture_name = None
        self.rainbow = False
        self.undoIcon = QtGui.QIcon(":undo")
        self.redoIcon = QtGui.QIcon(":redo")
        self.undoGrayIcon = QtGui.QIcon(":undo_gray")
        self.redoGrayIcon = QtGui.QIcon(":redo_gray")
        self.saveIcon = QtGui.QIcon(":save")
        self.saveGrayIcon = QtGui.QIcon(":save_gray")
        self.saveRGBIcon = QtGui.QIcon(":rgb")
        self.saveRGBGrayIcon = QtGui.QIcon(":rgb_gray")
        self.saveRGBAIcon = QtGui.QIcon(":rgba")
        self.saveRGBAGrayIcon = QtGui.QIcon(":rgba_gray")
        self.cropIcon = QtGui.QIcon(":crop")
        cropSelectIcon = QtGui.QPixmap(":crop_select")                                    #marime 32 pixeli
        self.cursor_crop = QtGui.QCursor(cropSelectIcon, 0, 0)
        self.last_saved_filename = None
        self.colors = QtGui.QColor.colorNames()
        self.hasSpray = False
        self.texture_size = QtCore.QSize(30, 30)
        self.texture_icons = icon_func()
        self.brush_textures = texture_func(self.texture_size)
        cursor_pixmap = QtGui.QPixmap(":bucket_32")                                       #marime 32 pixeli
        self.cursor_bucket = QtGui.QCursor(cursor_pixmap, 0, 0)
        self.undo_pos = -1
        self.image = QtGui.QImage(self.width, self.height, format)
        if self.format == QtGui.QImage.Format_RGB32:
            self.image.fill(QtGui.QColor(255, 255, 255))
            self.file_filter = 'Bitmap (*.bmp);; Cursor (*.cur);; Icon macOS (*.icns);; Icon Windows (*.ico);; ' \
                               'Joint Photographic Experts Group (*.jpeg);; Portable Bitmap (*.pbm);; Portable Grayscale (*.pgm);; ' \
                               'Portable Network Graphic (*.png);; Portable Colored (*.ppm);; Tagged Image Format (*.tif);;' \
                               'Wireless Application Protocol Bitmap (*.wbmp);; WebP (*.webp);; X Bitmap Graphic (*.xbm);;' \
                               'X PixMap (*.xpm)'
        else:
            self.image.fill(QtCore.Qt.transparent)
            self.file_filter = 'Tagged Image Format (*.tif) ;; Portable Network Graphic (*.png);;Cursor (*.cur);; ' \
                               'Icon macOS (*.icns);; Icon Windows (*.ico);; WebP (*.webp);;' \
                               'X PixMap (*.xpm)'
        self.undo_images = [self.image.copy()]



    def openImage(self, fileName):
        loadedImage = QtGui.QImage(fileName, self.format)
        if not loadedImage:
            return False
        newSize = loadedImage.size().expandedTo(self.size())
        loadedImage = self.resizeImage(loadedImage, newSize)
        self.image = loadedImage
        self.modified = False
        self.update()
        return True


    def clearImage(self):
        if self.undo_pos != -1:
            self.undo_images = self.undo_images[:self.undo_pos + 1]
            self.undo_pos = -1
            if self.format == self.rgb:
                self.redoAct.setEnabled(False)
                self.redoAct.setIcon(self.redoGrayIcon)
        if self.format == self.rgb:
            self.image.fill(QtGui.QColor(255, 255, 255))
        else:
            self.image.fill(QtCore.Qt.transparent)
        self.modified = True
        self.undo_images.append(self.image.copy())
        self.update()
        if self.format == self.rgb:
            self.parent.hiddenArea.clearImage()


    def Print(self):
        try:
            from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
        except ImportError as e:
            print("not print support")
        else:
            if self.image is None:
                return
            printer = QPrinter()
            printer.setPageSize(QPrinter.A4)
            printDialog = QPrintDialog(printer, self)
            if printDialog.exec_() == QtWidgets.QDialog.Accepted:
                painter = QtGui.QPainter(printer)
                rect = painter.viewport()
                image_aux = self.image.copy().scaled(rect.size(), QtCore.Qt.KeepAspectRatio, Qt.SmoothTransformation)                             #A4
                painter.drawImage(0, 0, image_aux)
                del painter



    def getCardinalPoints(self, haveSeen, centerPos, w, h):
        points = []
        cx, cy = centerPos
        for x, y in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            xx, yy = cx + x, cy + y
            if (xx >= 0 and xx < w and yy >= 0 and yy < h and (xx, yy) not in haveSeen):
                points.append((xx, yy))
                haveSeen.add((xx, yy))
        return points


    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.lastPoint = event.pos()
            if self.hasPen or self.hasBrush:
                self.scribbling = True
            elif self.hasEraser:
                self.erasing = True
            elif self.hasBucket:
                pos = event.pos()
                x = pos.x()
                y = pos.y()
                w, h = self.width, self.height
                target_color = self.image.pixel(x, y)
                haveSeen = set()
                queue = [(x, y)]
                painter = QtGui.QPainter(self.image)
                if self.hasBrush:
                    painter.setPen(QtGui.QPen(self.brush, self.myPenWidth, self.line,
                                              self.cap, self.join))
                else:
                    painter.setPen(QtGui.QPen(self.myPenColor, self.myPenWidth, self.line,
                                              self.cap, self.join))
                while queue:
                    x, y = queue.pop()
                    if self.image.pixel(x, y) == target_color:
                        painter.drawPoint(QtCore.QPoint(x, y))
                        queue[0:0] = self.getCardinalPoints(haveSeen, (x, y), w, h)
                self.update()
            elif self.hasCrop:
                self.origin = event.pos()
                if self.rubberBand is None:
                    self.rubberBand = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
                self.rubberBand.setGeometry(QtCore.QRect(self.origin, QtCore.QSize()))
                self.rubberBand.show()
        if self.format == self.rgb:
            self.parent.hiddenArea.mousePressEvent(event)



    def mouseMoveEvent(self, event):
        if event.buttons() & QtCore.Qt.LeftButton:
            if self.scribbling:
                self.drawLineTo(event.pos())
            elif self.erasing:
                self.erase(event.pos())
            elif self.hasCrop:
                self.rubberBand.setGeometry(QtCore.QRect(self.origin, event.pos()).normalized())
        if self.format == self.rgb:
            self.parent.hiddenArea.mouseMoveEvent(event)



    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            if self.scribbling:
                self.drawLineTo(event.pos())
                self.scribbling = False
            elif self.erasing:
                self.erase(event.pos())
                self.erasing = False
        if self.format == self.rgb:
            self.undoAct.setEnabled(True)
            self.undoAct.setIcon(self.undoIcon)
        if self.undo_pos != -1:
            self.undo_images = self.undo_images[:self.undo_pos+1]
            self.undo_pos = -1
            if self.format == self.rgb:
                self.redoAct.setEnabled(False)
                self.redoAct.setIcon(self.redoGrayIcon)
        self.undo_images.append(self.image.copy())
        if self.hasCrop:
            self.croppedRect = self.rubberBand.geometry()
            self.rubberBand.hide()
        if self.format == self.rgb:
            self.parent.hiddenArea.mouseReleaseEvent(event)



    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        dirtyRect = event.rect()
        painter.drawImage(dirtyRect, self.image, dirtyRect)
        if self.format == self.rgb:
            self.parent.hiddenArea.paintEvent(event)


    def resizeEvent(self, event):
        """
        if self.format == self.rgb:
            print("here")
            self.undoAct.setEnabled(True)
            self.undoAct.setIcon(self.undoIcon)
        if self.undo_pos != -1:
            self.undo_images = self.undo_images[:self.undo_pos + 1]
            self.undo_pos = -1
            if self.format == self.rgb:
                self.redoAct.setEnabled(False)
                self.redoAct.setIcon(self.redoGrayIcon)

        if self.width > self.image.width() or self.height > self.image.height():
            newWidth = max(self.width + 128, self.width)
            newHeight = max(self.height + 128, self.height)
            self.image = self.resizeImage(self.image, QtCore.QSize(newWidth, newHeight))
            self.update()
            """
        QtWidgets.QWidget.resizeEvent(self, event)
        self.width = self.image.width()
        self.height = self.image.height()
        if self.format == self.rgb:
            self.parent.hiddenArea.resizeEvent(event)


    def erase(self, endPoint):
        painter = QtGui.QPainter(self.image)
        if self.format == self.rgba:
            r = QtCore.QRect(QtCore.QPoint(), QtCore.QSize(5*self.eraserWidth, 5*self.eraserWidth))
            r.moveCenter(endPoint)
            painter.save()
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.eraseRect(r)
        else:
            painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255), 5*self.eraserWidth, QtCore.Qt.SolidLine, QtCore.Qt.RoundCap, QtCore.Qt.RoundJoin))
            painter.drawLine(self.lastPoint, endPoint)
        self.modified = True
        self.update()
        self.lastPoint = endPoint


    def crop(self):
        self.setCursor(self.cursor_crop)
        self.hasPen = False
        self.hasBrush = False
        self.hasBucket = False
        self.hasEraser = False
        self.hasCrop = True
        self.scribbling = False
        self.erasing = False


    def drawLineTo(self, endPoint):
        painter = QtGui.QPainter(self.image)
        if not self.rainbow and self.texture is None:     #scribbling, pen or brush
            if self.hasBrush and self.brush is not None:
                painter.setPen(QtGui.QPen(self.brush, self.myPenWidth, self.line,
                                          self.cap, self.join))
            #elif self.hasPen:
            else:
                painter.setPen(QtGui.QPen(self.myPenColor, self.myPenWidth, self.line,
                                          self.cap, self.join))
        elif self.rainbow:                                                                      #rainbow
            color = QtGui.QColor(choice(self.colors))
            if self.hasBrush and self.brush is not None:
                self.brush.setColor(color)
                painter.setPen(QtGui.QPen(self.brush, self.myPenWidth, self.line,
                                          self.cap, self.join))
            #elif self.hasPen:
            else:
                painter.setPen(QtGui.QPen(color, self.myPenWidth, self.line,
                                          self.cap, self.join))
        if not self.hasSpray and self.texture is None:
            painter.drawLine(self.lastPoint, endPoint)
            self.update()
        elif self.hasSpray:                                                                        #hasSpray
            pen = painter.pen()
            pen.setWidth(1)
            painter.setPen(pen)
            for n in range(self.myPenWidth*10 + 5):
                xo = random.gauss(0, 4 + self.myPenWidth)
                yo = random.gauss(0, 4 + self.myPenWidth)
                painter.drawPoint(int(self.lastPoint.x() + xo), int(self.lastPoint.y() + yo))
        elif self.texture is not None:
            line = QtCore.QLineF(self.lastPoint, endPoint)
            lista = []
            for i in range(int(line.length())):
                x = line.x1() + i*math.cos(math.radians(line.angle()))
                y = line.y1() - i*math.sin(math.radians(line.angle()))
                point = QtCore.QPoint(int(x), int(y))
                lista.append(point)
            for pos in lista:
                painter.drawImage(pos, self.texture)
                self.update()
        self.update()
        self.modified = True
        self.lastPoint = endPoint




    """chemata la salvarea imaginii"""
    def resizeImage(self, image, newSize):
        if image.size() == newSize:
            return image
        newImage = QtGui.QImage(newSize, self.format)
        if self.format == self.rgba:
            newImage.fill(QtCore.Qt.transparent)
        else:
            newImage.fill(QtGui.QColor(255, 255, 255))
        painter = QtGui.QPainter(newImage)
        painter.drawImage(QtCore.QPoint(0, 0), image)
        image = newImage
        return image



    def saveImage(self, fileName):
        visibleImage = self.image
        visibleImage = self.resizeImage(visibleImage, self.image.size())
        if visibleImage.save(fileName, quality=100):
            self.modified = False
            return True
        else:
            return False


class Image(QtWidgets.QWidget):
    def __init__(self, image, parent, width, height):
        super().__init__()
        if image:
            self.image = image
        else:
            self.image = QtGui.QImage(width, height, QtGui.QImage.Format_RGB32)
            self.image.fill(QtGui.QColor(255, 255, 255))
            self.undo_images.append(self.image.copy())
        self.coord = None
        self.parent = parent
        self.setAttribute(QtCore.Qt.WA_StaticContents)


    def paintEvent(self, event):
        if self.image:
            painter = QtGui.QPainter(self)
            dirtyRect = event.rect()
            painter.drawImage(dirtyRect, self.image, dirtyRect)


    def mousePressEvent(self, event):
        self.coord = event.pos()
        self.parent.close()



class resizeArea(QtWidgets.QDialog):
    def __init__(self, width, height):
        super().__init__()
        self.layout1 = QtWidgets.QHBoxLayout()
        self.layout2 = QtWidgets.QHBoxLayout()
        self.layout3 = QtWidgets.QVBoxLayout()
        self.setWindowTitle(self.tr("Change the image width/height"))
        self.widthVal = None
        self.heightVal = None
        self.labelWidth = QtWidgets.QLabel("Set the width: ")
        self.labelHeight = QtWidgets.QLabel("Set the height: ")
        self.widthBox = QtWidgets.QSpinBox()
        self.heightBox = QtWidgets.QSpinBox()
        self.widthBox.setMinimum(1)
        self.heightBox.setMinimum(1)
        self.widthBox.setRange(1, 5000)
        self.heightBox.setRange(1, 5000)
        self.widthBox.setSingleStep(50)
        self.heightBox.setSingleStep(50)
        self.widthBox.setValue(width)
        self.heightBox.setValue(height)
        self.layout1.addWidget(self.labelWidth)
        self.layout1.addWidget(self.widthBox)
        self.layout2.addWidget(self.labelHeight)
        self.layout2.addWidget(self.heightBox)
        self.button = QtWidgets.QPushButton('Set', self)
        self.button.resize(100, 50)
        self.button.clicked.connect(self.getVal)
        self.layout3.addLayout(self.layout1)
        self.layout3.addLayout(self.layout2)
        self.layout3.addWidget(self.button)
        self.setLayout(self.layout3)
        self.setFixedWidth(300)
        self.setFixedHeight(100)
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(True)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.exec_()

    def getVal(self):
        self.widthVal = self.widthBox.value()
        self.heightVal = self.heightBox.value()
        self.close()


class Coord(QtWidgets.QDialog):
    def __init__(self, image, title, width, height):
        super().__init__()
        self.layout = QtWidgets.QVBoxLayout()
        self.area = Image(image, self, width, height)
        self.layout.addWidget(self.area)
        self.setLayout(self.layout)
        self.setWindowTitle(self.tr(title))
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(True)
        self.resize(width, height)
        self.coord = None
        self.signal = False
        self.exec_()



class Slider(QtWidgets.QDialog):
    def __init__(self, title, min_val, max_val, current_val):
        super().__init__()
        self.setWindowTitle(self.tr(title))
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setModal(True)
        self.slider = QtWidgets.QSlider()
        self.slider.setRange(min_val, max_val)
        self.slider.setPageStep(1)
        self.slider.setOrientation(QtCore.Qt.Horizontal)
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addWidget(self.slider)
        self.button = QtWidgets.QPushButton('Ok', self)
        self.button.resize(150, 50)
        self.button.clicked.connect(self.getVal)
        self.layout.addWidget(self.button)
        self.setLayout(self.layout)
        self.resize(400, 100)
        self.val = None                                              #changes on button click
        self.slider.setValue(current_val)
        self.exec_()


    def getVal(self):
        self.val = self.slider.value()
        self.close()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=0):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon(':picasso'))
        self.scribbleArea = ScribbleArea(QtGui.QImage.Format_RGB32, self)
        self.hiddenArea = ScribbleArea(QtGui.QImage.Format_RGBA64, self)
        self.saveAsMenu = None
        self.fileMenu = None
        self.parent = parent
        self.optionMenu = None
        self.helpMenu = None
        self.openAct = None
        self.saveAsActs = []
        self.penColorAct = None
        self.penWidthAct = None
        self.printAct = None
        self.exitAct = None
        self.clearScreenAct = None
        self.aboutAct = None
        self.aboutQtAct = None
        self.setCentralWidget(self.scribbleArea)
        self.createActions()
        self.createMenus()
        self.setWindowTitle(self.tr("Scribble"))
        self.resize(self.scribbleArea.width, self.scribbleArea.height)


    def closeEvent(self, event):
        #self.parent.button_static.setEnabled(True)
        #self.parent.button_abstract.setEnabled(True)
        self.parent.button_upload.setEnabled(True)
        if self.maybeSave():
            event.accept()
        else:
            event.ignore()


    def open(self):
        if self.maybeSave():
            fileName,_filter = QtWidgets.QFileDialog.getOpenFileName(self, self.tr("Open File"), QtCore.QDir.currentPath())
            if fileName:
                self.scribbleArea.openImage(fileName)


    def save(self, format):
        if format == self.scribbleArea.rgb:
            self.scribbleArea.image.save(self.scribbleArea.last_saved_filename)
        else:
            self.hiddenArea.image.save(self.hiddenArea.last_saved_filename)


    def saveFile(self, format):
        if format == self.scribbleArea.rgb:
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=self,
                caption=self.tr("Save As"),
                directory=os.getcwd()+"/NewFile",
                filter=self.scribbleArea.file_filter
            )
            if not fileName:
                return False
            else:
                self.scribbleArea.last_saved_filename = fileName
                self.saveRGBAct.setEnabled(True)
                self.saveRGBAct.setIcon(self.scribbleArea.saveRGBIcon)
                self.saveMenu.setIcon(self.scribbleArea.saveIcon)
                return self.scribbleArea.saveImage(fileName)
        else:
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
                parent=self,
                caption=self.tr("Save As"),
                directory=os.getcwd() + "/NewFile",
                filter=self.hiddenArea.file_filter
            )
            if not fileName:
                return False
            else:
                self.hiddenArea.last_saved_filename = fileName
                self.saveRGBAAct.setEnabled(True)
                self.saveMenu.setIcon(self.scribbleArea.saveIcon)
                self.saveRGBAAct.setIcon(self.scribbleArea.saveRGBAIcon)
                return self.hiddenArea.saveImage(fileName)



    def settPen(self):
        self.setCursor(Qt.ArrowCursor)
        self.scribbleArea.hasPen = True
        self.scribbleArea.hasEraser = False
        self.scribbleArea.hasBrush = False
        self.scribbleArea.hasBucket = False
        self.scribbleArea.rainbow = False
        self.scribbleArea.hasSpray = False
        self.scribbleArea.texture = None

        self.hiddenArea.hasPen = True
        self.hiddenArea.hasEraser = False
        self.hiddenArea.hasBrush = False
        self.hiddenArea.hasBucket = False
        self.hiddenArea.rainbow = False
        self.hiddenArea.hasSpray = False
        self.hiddenArea.texture = None


    def settEraser(self):
        self.setCursor(Qt.ArrowCursor)
        self.scribbleArea.hasEraser = True
        self.scribbleArea.hasPen = False
        self.scribbleArea.hasBrush = False
        self.scribbleArea.hasBucket = False
        self.scribbleArea.rainbow = False
        self.scribbleArea.hasSpray = False
        self.scribbleArea.texture = None

        self.hiddenArea.hasEraser = True
        self.hiddenArea.hasPen = False
        self.hiddenArea.hasBrush = False
        self.hiddenArea.hasBucket = False
        self.hiddenArea.rainbow = False
        self.hiddenArea.hasSpray = False
        self.hiddenArea.texture = None


    def setRainbow(self):
        self.setCursor(Qt.ArrowCursor)
        self.scribbleArea.hasBucket = False
        self.scribbleArea.hasEraser = False
        self.scribbleArea.rainbow = True
        self.scribbleArea.texture = None

        self.hiddenArea.hasBucket = False
        self.hiddenArea.hasEraser = False
        self.hiddenArea.rainbow = True                       #can have spray and rainbow at the same time
        self.hiddenArea.texture = None



    def setSpray(self):
        self.setCursor(Qt.ArrowCursor)
        self.scribbleArea.hasBucket = False
        self.scribbleArea.hasEraser = False
        self.scribbleArea.hasSpray = True                               #can have spray and rainbow at the same time
        self.scribbleArea.texture = None

        self.hiddenArea.hasBucket = False
        self.hiddenArea.hasEraser = False
        self.hiddenArea.hasSpray = True                                    #is scribbling(has pen or brush)
        self.hiddenArea.texture = None



    def setCap(self, name):
        self.setCursor(Qt.ArrowCursor)
        cap = None
        if name == "Flat Cap":
            cap = Qt.FlatCap
        elif name == "Round Cap":
            cap = Qt.RoundCap
        else:
            cap = Qt.SquareCap

        self.scribbleArea.cap = cap
        self.hiddenArea.cap = cap


    def setJoin(self, name):
        self.setCursor(Qt.ArrowCursor)
        join = None
        if name == "Bevel Join":
            join = Qt.BevelJoin
        elif name == "Miter Join":
            join = Qt.MiterJoin
        else:
            join = Qt.RoundJoin
        self.scribbleArea.join = join
        self.hiddenArea.join = join


    def setLine(self, name):
        self.setCursor(Qt.ArrowCursor)
        line = None
        if name == "Dash Dot Dot Line":
            line = Qt.DashDotDotLine
        elif name == "Dash Dot Line":
            line = Qt.DashDotLine
        elif name == "Dash Line":
            line = Qt.DashLine
        elif name == "Dot Line":
            line = Qt.DotLine
        elif name == "Solid Line":
            line = Qt.SolidLine
        self.scribbleArea.line = line
        self.hiddenArea.line = line



    def setBucket(self):
        self.scribbleArea.hasBrush = False
        self.scribbleArea.hasPen = False
        self.scribbleArea.hasEraser = False
        self.scribbleArea.hasBucket = True
        self.scribbleArea.hasSpray = False
        self.scribbleArea.texture = None
        self.scribbleArea.rainbow = False

        self.hiddenArea.hasBrush = False
        self.hiddenArea.hasPen = False
        self.hiddenArea.hasEraser = False
        self.hiddenArea.hasBucket = True
        self.hiddenArea.hasSpray = False
        self.hiddenArea.texture = None
        self.hiddenArea.rainbow = False
        self.setCursor(self.scribbleArea.cursor_bucket)


    def setTexture(self, name):
        self.setCursor(Qt.ArrowCursor)

        self.hiddenArea.hasBrush = True
        self.hiddenArea.hasPen = False
        self.hiddenArea.hasEraser = False
        self.hiddenArea.hasBucket = False
        self.hiddenArea.hasSpray = False
        self.hiddenArea.rainbow = False
        self.hiddenArea.texture_name = name

        self.scribbleArea.hasBrush = True
        self.scribbleArea.hasPen = False
        self.scribbleArea.hasEraser = False
        self.scribbleArea.hasBucket = False
        self.scribbleArea.hasSpray = False
        self.scribbleArea.rainbow = False
        self.scribbleArea.texture_name = name
        if "Brush" in name:
            idx = int(name[6:])
            image = img.open("./resources/textures/brush"+str(idx)+".png", formats=None)
            target_col = self.hiddenArea.myPenColor
            my_blue = target_col.blue()
            my_red = target_col.red()
            my_green = target_col.green()
            target_col = np.array((my_red, my_green, my_blue))
            image_np = np.asarray(image)
            alpha = image_np[:, :, -1:]
            image_rgb = image_np[:, :, :-1]
            imgGray = image.convert('L')
            image_array = np.asarray(imgGray)
            image_float = image_array / 255

            new_img = np.zeros(image_rgb.shape)

            for i in range(len(image_float)):
                for j in range(len(image_float[0])):
                    new_img[i][j] = image_float[i][j] * target_col

            new_img = np.concatenate((new_img, alpha), axis=2)
            output_image = img.fromarray(new_img.astype(np.uint8))
            output_image.save("output.png")

            new = QtGui.QImage("output.png")

            new = new.scaled(self.hiddenArea.texture_size)
            self.hiddenArea.texture = new
            self.scribbleArea.texture = new


    def setBrush(self, name):
        self.setCursor(Qt.ArrowCursor)
        self.scribbleArea.hasBrush = True
        self.scribbleArea.hasPen = False
        self.scribbleArea.hasEraser = False
        self.scribbleArea.hasBucket = False
        self.scribbleArea.texture = None

        self.hiddenArea.hasBrush = True
        self.hiddenArea.hasPen = False
        self.hiddenArea.hasEraser = False
        self.hiddenArea.hasBucket = False
        self.hiddenArea.texture = None                                #custom texture

        pattern = None
        grad = None
        if name == "Dense 1 Pattern":
            pattern = QtCore.Qt.Dense1Pattern
        elif name == "Dense 2 Pattern":
            pattern = QtCore.Qt.Dense2Pattern
        elif name == "Dense 3 Pattern":
            pattern = QtCore.Qt.Dense3Pattern
        elif name == "Dense 4 Pattern":
            pattern = QtCore.Qt.Dense4Pattern
        elif name == "Dense 5 Pattern":
            pattern = QtCore.Qt.Dense5Pattern
        elif name == "Dense 6 Pattern":
            pattern = QtCore.Qt.Dense6Pattern
        elif name == "Dense 7 Pattern":
            pattern = QtCore.Qt.Dense7Pattern
        elif name == "Horizontal Pattern":
            pattern = QtCore.Qt.HorPattern
        elif name == "Vertical Pattern":
            pattern = QtCore.Qt.VerPattern
        elif name == "Cross Pattern":
            pattern = QtCore.Qt.CrossPattern
        elif name == "B Diagonal Pattern":
            pattern = QtCore.Qt.BDiagPattern
        elif name == "F Diagonal Pattern":
            pattern = QtCore.Qt.FDiagPattern
        elif name == "Diagonal Cross Pattern":
            pattern = QtCore.Qt.DiagCrossPattern
        elif name == "Linear Gradient Pattern":
            self.scribbleArea.rainbow = False
            self.hiddenArea.rainbow = False
            nrCol, ok = QtWidgets.QInputDialog.getInt(self, self.tr("Gradient"), self.tr("Select number of colors for the linear gradient: "),
                                                         2, 2, 10, 1)
            lista = []
            if ok:
                pos1 = Coord(self.scribbleArea.image, "Select first focal point position", self.scribbleArea.width, self.scribbleArea.height)
                pos2 = Coord(self.scribbleArea.image, "Select second focal point position", self.scribbleArea.width, self.scribbleArea.height)
                for i in range(nrCol):
                    newColor = QtWidgets.QColorDialog.getColor(self.scribbleArea.myPenColor)
                    slider = Slider("Select a position for the color", 0, 10, 0)
                    if newColor and slider.val is not None:
                        lista.append((newColor, slider.val))
                if pos1.area.coord and pos2.area.coord and lista:
                    grad = QtGui.QLinearGradient(pos1.area.coord, pos2.area.coord)

                    for i in range(nrCol):
                        grad.setColorAt(lista[i][1]/10, lista[i][0])
            else:
                x = self.scribbleArea.geometry().x()
                y = self.scribbleArea.geometry().y()
                grad = QtGui.QLinearGradient(x, y, self.scribbleArea.geometry().width() + x,
                                                 self.scribbleArea.geometry().height() + y)
                grad.setColorAt(0.0, self.scribbleArea.myPenColor)
                grad.setColorAt(0.5, QtCore.Qt.black)

        elif name == "Radial Gradient Pattern":
            self.scribbleArea.rainbow = False
            self.hiddenArea.rainbow = False
            nrCol, ok = QtWidgets.QInputDialog.getInt(self, self.tr("Gradient"),
                                                      self.tr("Select number of colors for the radial gradient: "),
                                                      2, 2, 10, 1)
            if ok:
                print("ok")
                lista = []
                pos1 = Coord(self.scribbleArea.image, "Select center position",
                             self.scribbleArea.width, self.scribbleArea.height)
                slider1 = Slider("Select gradient radius:", 1, 1000, 1)
                for i in range(nrCol):
                    newColor = QtWidgets.QColorDialog.getColor(self.scribbleArea.myPenColor)
                    slider2 = Slider("Select a position for the color", 0, 10, 0)
                    if newColor and slider2.val is not None:
                        lista.append((newColor, slider2.val))
                if pos1.area.coord and lista and slider1.val:
                    grad = QtGui.QRadialGradient(pos1.area.coord, slider1.val)

                    for i in range(nrCol):
                        grad.setColorAt(lista[i][1]/10, lista[i][0])
            else:
                x = self.scribbleArea.geometry().x()
                y = self.scribbleArea.geometry().y()
                width = self.scribbleArea.geometry().width()
                height = self.scribbleArea.geometry().height()
                grad = QtGui.QRadialGradient(x + width/2, y + height/2, min(x + width/2, y + height/2))
                grad.setColorAt(0.0, self.scribbleArea.myPenColor)
                grad.setColorAt(0.5, QtCore.Qt.black)

        elif name == "Conical Gradient Pattern":
            self.scribbleArea.rainbow = False
            self.hiddenArea.rainbow = False
            nrCol, ok = QtWidgets.QInputDialog.getInt(self, self.tr("Gradient"),
                                                      self.tr("Select number of colors for the conical gradient: "),
                                                      2, 2, 10, 1)
            if ok:
                lista = []
                pos1 = Coord(self.scribbleArea.image, "Select center position",
                             self.scribbleArea.width, self.scribbleArea.height)
                slider1 = Slider("Select Select angle (1° - 359°) :", 1, 359, 1)
                for i in range(nrCol):
                    newColor = QtWidgets.QColorDialog.getColor(self.scribbleArea.myPenColor)
                    slider2 = Slider("Select a position for the color", 0, 10, 0)
                    if newColor and slider2.val is not None:
                        lista.append((newColor, slider2.val))
                if pos1.area.coord and lista and slider1.val:
                    grad = QtGui.QConicalGradient(pos1.area.coord, slider1.val)

                    for i in range(nrCol):
                        grad.setColorAt(lista[i][1] / 10, lista[i][0])
            else:
                x = self.scribbleArea.geometry().x()
                y = self.scribbleArea.geometry().y()
                width = self.scribbleArea.geometry().width()
                height = self.scribbleArea.geometry().height()
                grad = QtGui.QConicalGradient(x + width / 2, y + height / 2, 30)
                grad.setColorAt(0.0, self.scribbleArea.myPenColor)
                grad.setColorAt(0.5, QtCore.Qt.black)
        else:
            fileName, _filter = QtWidgets.QFileDialog.getOpenFileName(self, self.tr("Open File"), QtCore.QDir.currentPath())
            if fileName:
                image = QtGui.QImage(fileName)
                self.scribbleArea.brush = QtGui.QBrush(image)
                self.hiddenArea.brush = QtGui.QBrush(image)
        if name != "Texture Pattern..." and not grad:
            self.scribbleArea.brush = QtGui.QBrush(self.scribbleArea.myPenColor, pattern)
            self.hiddenArea.brush = QtGui.QBrush(self.hiddenArea.myPenColor, pattern)
        elif grad:
            self.scribbleArea.brush = QtGui.QBrush(grad)
            self.hiddenArea.brush = QtGui.QBrush(grad)



    def penColor(self):
        self.scribbleArea.rainbow = False
        self.hiddenArea.rainbow = False
        newColor = QtWidgets.QColorDialog.getColor(self.scribbleArea.myPenColor)
        if newColor.isValid():
            self.scribbleArea.myPenColor = newColor
            self.hiddenArea.myPenColor = newColor
            if self.hiddenArea.texture is not None:
                self.setTexture(self.hiddenArea.texture_name)


    def penWidth(self):
        slider = Slider("Select pen width", 1, 50, self.scribbleArea.myPenWidth)
        self.scribbleArea.myPenWidth = slider.val
        self.hiddenArea.myPenWidth = slider.val


    def eraserWidth(self):
        slider = Slider("Select eraser width", 1, 15, self.scribbleArea.eraserWidth)
        self.scribbleArea.eraserWidth = slider.val
        self.hiddenArea.eraserWidth = slider.val


    def textureWidth(self):
        slider = Slider("Select texture width", 10, 60, self.scribbleArea.texture_size.width())
        self.scribbleArea.texture_size = self.hiddenArea.texture_size = QtCore.QSize(slider.val, slider.val)
        self.setTexture(self.scribbleArea.texture_name)


    def about(self):
        QtWidgets.QMessageBox.about(self, self.tr("About scribble"), self.tr("<p>The <b>Scribble</b> example is awesome</p>"))


    def undo(self):
        lista = [self.scribbleArea, self.hiddenArea]
        for area in lista:
            if area.undo_pos == -1:
                area.undo_pos = len(area.undo_images)-2
                if area.format == area.rgb:
                    area.redoAct.setEnabled(True)
                    area.redoAct.setIcon(area.redoIcon)
            elif area.undo_pos > 0:
                area.undo_pos -= 1
                if area.format == area.rgb:
                    area.redoAct.setEnabled(True)
                    area.redoAct.setIcon(area.redoIcon)
            elif area.format == area.rgb:                                                        #nu mai poate da inapoi
                area.undoAct.setEnabled(False)
                area.undoAct.setIcon(area.undoGrayIcon)
            if area.format == area.rgb and area.undo_pos == 0:
                area.undoAct.setEnabled(False)
                area.undoAct.setIcon(area.undoGrayIcon)
            area.image = area.undo_images[area.undo_pos].copy()
            area.modified = True
            area.update()


    def export(self):
        image = self.scribbleArea.image
        image.save("My_Drawing.png", quality=100)
        image = image.scaled(self.parent.size, QtCore.Qt.KeepAspectRatio)
        self.parent.your_image = QtGui.QPixmap.fromImage(image)
        self.parent.drawed = True
        if self.parent.transfered:
            self.parent.button_compare.setEnabled(True)
        self.parent.button_static.setEnabled(True)
        self.parent.button_abstract.setEnabled(True)
        self.parent.button_upload.setEnabled(True)
        self.parent.label_comparison.setText("Current similarity (from 0 to 10): Empty")
        self.parent.your_image_label.setPixmap(QtGui.QPixmap.fromImage(image))
        self.parent.window.hide()



    def redo(self):
        lista = [self.scribbleArea, self.hiddenArea]
        for area in lista:
            if area.format == area.rgb:
                area.undoAct.setEnabled(True)
                area.undoAct.setIcon(area.undoIcon)
            if area.undo_pos > -1:
                area.undo_pos += 1
            if area.format == area.rgb and area.undo_pos == (len(area.undo_images) - 1):
                area.redoAct.setEnabled(False)
                area.redoAct.setIcon(area.redoGrayIcon)
            area.image = area.undo_images[area.undo_pos].copy()
            area.modified = True
            area.update()


    def resizeImage(self):
        resizeObj = resizeArea(self.scribbleArea.width, self.scribbleArea.height)
        newSize = QtCore.QSize(resizeObj.widthVal, resizeObj.heightVal)
        if self.scribbleArea.image.size() == newSize:
            return
        newImageRGB = QtGui.QImage(newSize, self.scribbleArea.rgb)
        newImageRGBA = QtGui.QImage(newSize, self.scribbleArea.rgba)
        newImageRGBA.fill(QtCore.Qt.transparent)
        newImageRGB.fill(QtGui.QColor(255, 255, 255))

        painterRGB = QtGui.QPainter(newImageRGB)
        painterRGB.drawImage(QtCore.QPoint(0, 0), self.scribbleArea.image)
        self.scribbleArea.image = newImageRGB

        painterRGBA = QtGui.QPainter(newImageRGBA)
        painterRGBA.drawImage(QtCore.QPoint(0, 0), self.hiddenArea.image)
        self.hiddenArea.image = newImageRGBA

        self.scribbleArea.undo_images.append(self.scribbleArea.image.copy())
        self.hiddenArea.undo_images.append(self.hiddenArea.image.copy())



    def createActions(self):
        openIcon = QtGui.QIcon(":openfile")
        self.openAct = QtWidgets.QAction(openIcon, self.tr("Open..."), self)
        self.openAct.setShortcuts(QtGui.QKeySequence.Open)
        self.openAct.triggered.connect(self.open)
        saveAsRGBIcon = QtGui.QIcon(":rgb")
        self.saveAsRGBAct = QtWidgets.QAction(saveAsRGBIcon, self.tr("Save as RGB..."), self)
        self.saveAsRGBAct.triggered.connect(lambda ch, x=self.scribbleArea.rgb:  self.saveFile(x))

        saveAsRGBAIcon = QtGui.QIcon(":rgba")
        self.saveAsRGBAAct = QtWidgets.QAction(saveAsRGBAIcon, self.tr("Save as RGBA (transparent bg.)..."), self)
        self.saveAsRGBAAct.triggered.connect(lambda ch, x=self.scribbleArea.rgba: self.saveFile(x))


        self.saveRGBAct = QtWidgets.QAction(self.scribbleArea.saveRGBGrayIcon, self.tr("Save RGB"), self)
        self.saveRGBAct.setEnabled(False)
        self.saveRGBAct.triggered.connect(lambda ch, x=self.scribbleArea.rgb:  self.save(x))


        self.saveRGBAAct = QtWidgets.QAction(self.scribbleArea.saveRGBAGrayIcon, self.tr("Save RGBA (transparent bg.)"), self)
        self.saveRGBAAct.setEnabled(False)
        self.saveRGBAAct.triggered.connect(lambda ch, x=self.scribbleArea.rgba: self.save(x))

        exportIcon = QtGui.QIcon(":export")
        self.exportAct = QtWidgets.QAction(exportIcon, self.tr("Export image back to the app"), self)
        self.exportAct.triggered.connect(self.export)
        self.exportAct.setShortcut(self.tr("Ctrl+E"))

        printIcon = QtGui.QIcon(":print")
        self.printAct = QtWidgets.QAction(printIcon, self.tr("Print..."), self)
        self.printAct.triggered.connect(self.scribbleArea.Print)
        self.printAct.setShortcut(self.tr("Ctrl+P"))

        exitIcon = QtGui.QIcon(":exit")
        self.exitAct = QtWidgets.QAction(exitIcon, self.tr("Exit"), self)
        self.exitAct.setShortcuts(QtGui.QKeySequence.Quit)
        self.exitAct.triggered.connect(self.close)

        colorIcon = QtGui.QIcon(":color")
        self.penColorAct = QtWidgets.QAction(colorIcon, self.tr("Pen color..."), self)
        self.penColorAct.triggered.connect(self.penColor)

        resizeIcon = QtGui.QIcon(":resize")
        self.resizeAct = QtWidgets.QAction(resizeIcon, self.tr("Resize..."), self)
        self.resizeAct.triggered.connect(self.resizeImage)

        penWidthIcon = QtGui.QIcon(":linewidth")
        self.penWidthAct = QtWidgets.QAction(penWidthIcon, self.tr("Pen width..."), self)
        self.penWidthAct.triggered.connect(self.penWidth)

        eraserWidthIcon = QtGui.QIcon(":eraserwidth")
        self.eraserWidthAct = QtWidgets.QAction(eraserWidthIcon, self.tr("Eraser width..."), self)
        self.eraserWidthAct.triggered.connect(self.eraserWidth)

        textureSizeIcon = QtGui.QIcon(":texture_size")
        self.textureWidthAct = QtWidgets.QAction(textureSizeIcon, self.tr("Custom texture width..."), self)
        self.textureWidthAct.triggered.connect(self.textureWidth)

        clsIcon = QtGui.QIcon(":clearscreen")
        self.clearScreenAct = QtWidgets.QAction(clsIcon, self.tr("Clear Screen..."), self)
        self.clearScreenAct.setShortcut(self.tr("Ctrl+L"))
        self.clearScreenAct.triggered.connect(self.scribbleArea.clearImage) #

        penIcon = QtGui.QIcon(":pen")
        self.setPenAct = QtWidgets.QAction(penIcon, self.tr("Select Pen"), self)
        self.setPenAct.triggered.connect(self.settPen)

        self.scribbleArea.undoAct = QtWidgets.QAction(self.scribbleArea.undoGrayIcon, self.tr("Undo"), self)
        self.scribbleArea.undoAct.setEnabled(False)
        self.scribbleArea.undoAct.triggered.connect(self.undo)
        self.scribbleArea.undoAct.setShortcut(self.tr("Ctrl+Z"))

        self.scribbleArea.redoAct = QtWidgets.QAction(self.scribbleArea.redoGrayIcon, self.tr("Redo"), self)
        self.scribbleArea.redoAct.setEnabled(False)
        self.scribbleArea.redoAct.triggered.connect(self.redo)
        self.scribbleArea.redoAct.setShortcut(self.tr("Ctrl+Y"))

        self.cropAct = QtWidgets.QAction(self.tr("Crop"), self)
        self.cropAct.triggered.connect(self.scribbleArea.crop)

        eraserIcon = QtGui.QIcon(":eraser")
        self.setEraserAct = QtWidgets.QAction(eraserIcon, self.tr("Select Eraser"), self)
        self.setEraserAct.triggered.connect(self.settEraser)


        dense1Pattern = QtGui.QIcon(":Dense1Pattern")
        dense2Pattern = QtGui.QIcon(":Dense2Pattern")
        dense3Pattern = QtGui.QIcon(":Dense3Pattern")
        dense4Pattern = QtGui.QIcon(":Dense4Pattern")
        dense5Pattern = QtGui.QIcon(":Dense5Pattern")
        dense6Pattern = QtGui.QIcon(":Dense6Pattern")
        dense7Pattern = QtGui.QIcon(":Dense7Pattern")
        horPattern = QtGui.QIcon(":HorPattern")
        verPattern = QtGui.QIcon(":VerPattern")
        crossPattern = QtGui.QIcon(":CrossPattern")
        bDiagPattern = QtGui.QIcon(":BDiagPattern")
        fDiagPattern = QtGui.QIcon(":FDiagPattern")
        diagCrossPattern = QtGui.QIcon(":DiagCrossPattern")
        linearGradientPattern = QtGui.QIcon(":LinearGradientPattern")
        radialGradientPattern = QtGui.QIcon(":RadialGradientPattern")
        conicalGradientPattern = QtGui.QIcon(":ConicalGradientPattern")

        acts = []
        self.dense1Act = QtWidgets.QAction(dense1Pattern, self.tr("Dense 1 Pattern"), self)

        self.dense2Act = QtWidgets.QAction(dense2Pattern, self.tr("Dense 2 Pattern"), self)
        self.dense3Act = QtWidgets.QAction(dense3Pattern, self.tr("Dense 3 Pattern"), self)
        self.dense4Act = QtWidgets.QAction(dense4Pattern, self.tr("Dense 4 Pattern"), self)
        self.dense5Act = QtWidgets.QAction(dense5Pattern, self.tr("Dense 5 Pattern"), self)
        self.dense6Act = QtWidgets.QAction(dense6Pattern, self.tr("Dense 6 Pattern"), self)
        self.dense7Act = QtWidgets.QAction(dense7Pattern, self.tr("Dense 7 Pattern"), self)
        self.horAct = QtWidgets.QAction(horPattern, self.tr("Horizontal Pattern"), self)
        self.verAct = QtWidgets.QAction(verPattern, self.tr("Vertical Pattern"), self)
        self.crossAct = QtWidgets.QAction(crossPattern, self.tr("Cross Pattern"), self)
        self.bDiagAct = QtWidgets.QAction(bDiagPattern, self.tr("B Diagonal Pattern"), self)
        self.fDiagAct = QtWidgets.QAction(fDiagPattern, self.tr("F Diagonal Pattern"), self)
        self.diagCrossAct = QtWidgets.QAction(diagCrossPattern, self.tr("Diagonal Cross Pattern"), self)
        self.liniarGradientAct = QtWidgets.QAction(linearGradientPattern, self.tr("Linear Gradient Pattern"), self)
        self.radialGradientAct = QtWidgets.QAction(radialGradientPattern, self.tr("Radial Gradient Pattern"), self)
        self.conicalGradientAct = QtWidgets.QAction(conicalGradientPattern, self.tr("Conical Gradient Pattern"), self)
        self.textureAct = QtWidgets.QAction(self.tr("Texture Pattern..."), self)


        acts.append(self.dense1Act)
        acts.append(self.dense2Act)
        acts.append(self.dense3Act)
        acts.append(self.dense4Act)
        acts.append(self.dense5Act)
        acts.append(self.dense6Act)
        acts.append(self.dense7Act)
        acts.append(self.horAct)
        acts.append(self.verAct)
        acts.append(self.crossAct)
        acts.append(self.bDiagAct)
        acts.append(self.fDiagAct)
        acts.append(self.diagCrossAct)
        acts.append(self.liniarGradientAct)
        acts.append(self.radialGradientAct)
        acts.append(self.conicalGradientAct)
        self.grad_acts = acts

        self.texture_acts = []

        for i in range(11):
            self.texture_acts.append(QtWidgets.QAction(self.scribbleArea.texture_icons[i], self.tr("Brush "+str(i+1)), self))

        for action in self.texture_acts:
            action.triggered.connect(lambda ch, x=action.text(): self.setTexture(x))


        self.cap_acts = []

        flatCapIcon = QtGui.QIcon(":FlatCap")
        roundCapIcon = QtGui.QIcon(":RoundCap")
        squareCapIcon = QtGui.QIcon(":SquareCap")
        flatCapAct = QtWidgets.QAction(flatCapIcon, self.tr("Flat Cap"), self)
        roundCapAct = QtWidgets.QAction(roundCapIcon, self.tr("Round Cap"), self)
        squareCapAct = QtWidgets.QAction(squareCapIcon, self.tr("Square Cap"), self)

        self.cap_acts.append(flatCapAct)
        self.cap_acts.append(roundCapAct)
        self.cap_acts.append(squareCapAct)

        self.join_acts = []

        bevelJoinIcon = QtGui.QIcon(":BevelJoin")
        miterJoinIcon = QtGui.QIcon(":MiterJoin")
        roundJoinIcon = QtGui.QIcon(":RoundJoin")
        bevelJoinAct = QtWidgets.QAction(bevelJoinIcon, self.tr("Bevel Join"), self)
        miterJoinAct = QtWidgets.QAction(miterJoinIcon, self.tr("Miter Join"), self)
        roundJoinAct = QtWidgets.QAction(roundJoinIcon, self.tr("Round Join"), self)

        self.join_acts.append(bevelJoinAct)
        self.join_acts.append(miterJoinAct)
        self.join_acts.append(roundJoinAct)

        self.line_acts = []

        dashDotDotLineIcon = QtGui.QIcon(":DashDotDotLine")
        dashDotLineIcon = QtGui.QIcon(":DashDotLine")
        dashLineIcon = QtGui.QIcon(":DashLine")
        dotLineIcon = QtGui.QIcon(":DotLine")
        solidLineIcon = QtGui.QIcon(":SolidLine")
        dashDotDotAct = QtWidgets.QAction(dashDotDotLineIcon, self.tr("Dash Dot Dot Line"), self)
        dashDotAct = QtWidgets.QAction(dashDotLineIcon, self.tr("Dash Dot Line"), self)
        dashAct = QtWidgets.QAction(dashLineIcon, self.tr("Dash Line"), self)
        dotAct = QtWidgets.QAction(dotLineIcon, self.tr("Dot Line"), self)
        solidAct = QtWidgets.QAction(solidLineIcon, self.tr("Solid Line"), self)

        self.line_acts.append(dashDotDotAct)
        self.line_acts.append(dashDotAct)
        self.line_acts.append(dashAct)
        self.line_acts.append(dotAct)
        self.line_acts.append(solidAct)

        bucketIcon = QtGui.QIcon(":bucket")
        self.bucketAct = QtWidgets.QAction(bucketIcon, self.tr("Bucket"), self)
        self.bucketAct.triggered.connect(self.setBucket)

        rainbowIcon = QtGui.QIcon(":rainbow")
        self.rainbowAct = QtWidgets.QAction(rainbowIcon, self.tr("Rainbow"), self)
        self.rainbowAct.triggered.connect(self.setRainbow)

        sprayIcon = QtGui.QIcon(":spray")
        self.sprayAct = QtWidgets.QAction(sprayIcon, self.tr("Spray"), self)
        self.sprayAct.triggered.connect(self.setSpray)

        for act in acts:
            act.triggered.connect(lambda ch, x=act.text(): self.setBrush(x))

        self.textureAct.triggered.connect(lambda ch, x=self.textureAct.text(): self.setBrush(x))

        for act in self.cap_acts:
            act.triggered.connect(lambda ch, x=act.text(): self.setCap(x))

        for act in self.join_acts:
            act.triggered.connect(lambda ch, x=act.text(): self.setJoin(x))

        for act in self.line_acts:
            act.triggered.connect(lambda ch, x=act.text(): self.setLine(x))


        self.aboutAct = QtWidgets.QAction(self.tr("About..."), self)
        self.aboutAct.triggered.connect(self.about)
        self.aboutQtAct = QtWidgets.QAction(self.tr("About Qt ..."), self)
        self.aboutQtAct.triggered.connect(QtWidgets.qApp.aboutQt)


    def createMenus(self):
        fileIcon = QtGui.QIcon(":file")
        self.fileMenu = QtWidgets.QMenu(self.tr("File"), self)

        saveAsIcon = QtGui.QIcon(":saveas")
        self.saveAsMenu = QtWidgets.QMenu(self.tr("Save as"), self)
        self.saveAsMenu.setIcon(saveAsIcon)

        self.saveMenu = QtWidgets.QMenu(self.tr("Save"), self)
        self.saveMenu.setIcon(self.scribbleArea.saveGrayIcon)

        self.saveAsMenu.addAction(self.saveAsRGBAct)
        self.saveAsMenu.addAction(self.saveAsRGBAAct)
        self.saveMenu.addAction(self.saveRGBAct)
        self.saveMenu.addAction(self.saveRGBAAct)

        self.fileMenu.setIcon(fileIcon)
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addMenu(self.saveAsMenu)
        self.fileMenu.addMenu(self.saveMenu)
        self.fileMenu.addAction(self.exportAct)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)
        self.optionMenu = QtWidgets.QMenu(self.tr("Options"), self)
        self.optionMenu.addAction(self.penColorAct)
        self.optionMenu.addAction(self.penWidthAct)


        self.optionMenu.addAction(self.eraserWidthAct)
        self.optionMenu.addAction(self.textureWidthAct)
        self.optionMenu.addSeparator()
        self.optionMenu.addAction(self.resizeAct)
        self.optionMenu.addAction(self.clearScreenAct)

        brushIcon = QtGui.QIcon(":brush")
        helpIcon = QtGui.QIcon(":help")
        self.helpMenu = QtWidgets.QMenu(self.tr("Help"), self)
        self.helpMenu.setIcon(helpIcon)
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addAction(self.setPenAct)
        self.menuBar().addAction(self.setEraserAct)
        brushMenu = self.menuBar().addMenu("Select Brush")
        brushMenu.setIcon(brushIcon)

        textureIcon = QtGui.QIcon(":texture")
        capIcon = QtGui.QIcon(":cap")
        joinIcon = QtGui.QIcon(":join")
        lineIcon = QtGui.QIcon(":line")

        textureMenu = brushMenu.addMenu("Textures and Patterns")
        capMenu = brushMenu.addMenu("Cap styles")
        joinMenu = brushMenu.addMenu("Line join styles")
        lineMenu = brushMenu.addMenu("Line styles")

        textureMenu.setIcon(textureIcon)
        capMenu.setIcon(capIcon)
        joinMenu.setIcon(joinIcon)
        lineMenu.setIcon(lineIcon)

        customtextIcon = QtGui.QIcon(":custom_texture")
        customTextMenu = textureMenu.addMenu(customtextIcon, "Custom textures")
        textureMenu.addActions(self.grad_acts)

        customTextMenu.addActions(self.texture_acts)
        customTextMenu.addAction(self.textureAct)
        capMenu.addActions(self.cap_acts)
        joinMenu.addActions(self.join_acts)
        lineMenu.addActions(self.line_acts)
        brushMenu.addAction(self.bucketAct)
        brushMenu.addAction(self.rainbowAct)
        brushMenu.addAction(self.sprayAct)

        self.menuBar().addMenu(self.optionMenu)

        self.menuBar().addAction(self.scribbleArea.undoAct)

        self.menuBar().addAction(self.scribbleArea.redoAct)

        self.menuBar().addAction(self.cropAct)

        self.menuBar().addMenu(self.helpMenu)



    def maybeSave(self):
        if self.scribbleArea.modified:
            ret = QtWidgets.QMessageBox.warning(self, self.tr("Scribble"), self.tr("The image has been modified. \n"
                                                                                   "Do you want to save the changes?"),
                            QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.Discard | QtWidgets.QMessageBox.Cancel)
            if ret == QtWidgets.QMessageBox.Save:
                return self.saveFile("bmp")
            elif ret == QtWidgets.QMessageBox.Cancel:
                return False
        return True



class ModelEncoder(Model):
    def __init__(self):
        super(ModelEncoder, self).__init__()
        self.encoder = tf.keras.Sequential([
            layers.Input(shape=(1, 256, 256, 4)),
            layers.Conv2D(256, (3, 3), activation='relu', padding='same', strides=2, input_shape=(1, 256, 256, 4)),
            layers.Conv2D(128, (3, 3), activation='relu', padding='same', strides=2),
            layers.Conv2D(64, (3, 3), activation='relu', padding='same', strides=2),
            layers.Conv2D(16, (3, 3), activation='relu', padding='same', strides=2),
            layers.Conv2D(8, (3, 3), activation='relu', padding='same', strides=2),
            layers.Flatten(),
            layers.Dense(512)])

        self.decoder = tf.keras.Sequential([
            layers.Dense(512, activation='sigmoid'),
            layers.Reshape((8, 8, 8)),
            layers.Conv2DTranspose(8, kernel_size=3, strides=2, activation='relu', padding='same'),
            layers.Conv2DTranspose(16, kernel_size=3, strides=2, activation='relu', padding='same'),
            layers.Conv2DTranspose(64, kernel_size=3, strides=2, activation='relu', padding='same'),
            layers.Conv2DTranspose(128, kernel_size=3, strides=2, activation='relu', padding='same'),
            layers.Conv2DTranspose(256, kernel_size=3, strides=2, activation='relu', padding='same'),
            layers.Conv2D(4, kernel_size=(3, 3), activation='sigmoid', padding='same')])


    def call(self, x):
        encoded = self.encoder(x)
        #print(encoded.shape)
        return encoded


class StyleTransferVGG19:
    def __init__(self, parent=0):
        with tf.device("/GPU:0"):
            self.parent = parent

            self.device = ("cuda" if torch.cuda.is_available() else "cpu")

            self.model = models.vgg19(pretrained=True).features
            for p in self.model.parameters():
                p.requires_grad = False
            self.model.to(self.device)

            self.transform = transforms.Compose([transforms.Resize(400), transforms.ToTensor(),
                                                 transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))])



    def stylize(self, thread=None):
        if thread is None:
            self.parent.button_static.setEnabled(False)
            self.parent.button_abstract.setEnabled(False)
            self.parent.label_message.setText("Currently style transfering...You may draw/re-draw/upload an image or begin 2nd style transferring")

        with tf.device("/GPU:0"):
            self.parent.button_stylize2.setEnabled(False)
            content = img.open(self.parent.static_choice).convert("RGB")
            content = self.transform(content).to(self.device)
            style = img.open(self.parent.abstract_choice).convert("RGB")
            style = self.transform(style).to(self.device)
            _, w, h = content.size()
            dim = max(w, h)
            content = self.parent.process_image(content, dim)
            target = content.clone().requires_grad_(True).to(self.device)

            style_features = self.model_activations(style, self.model)
            content_features = self.model_activations(content, self.model)
            style_wt_meas = {"conv1_1": 2.0, "conv2_1": 1.4, "conv3_1": 0.8, "conv4_1": 0.4, "conv5_1": 0.3}
            style_grams = {layer: self.gram_matrix(style_features[layer]) for layer in style_features}

            content_wt = 1000
            style_wt = 1e8
            #print_after = 30
            epochs = 100
            optimizer = torch.optim.Adam([target], lr=0.2)

            now = time.time()
            for i in range(1, epochs + 1):
                target_features = self.model_activations(target, self.model)
                content_loss = torch.mean((content_features['conv4_2'] - target_features['conv4_2']) ** 2)  # mse
                # content_loss = torch.mean((content_features['conv3_2'] - target_features['conv3_2'])**2)

                style_loss = 0
                for layer in style_wt_meas:
                    style_gram = style_grams[layer]
                    target_gram = target_features[layer]
                    _, d, w, h = target_gram.shape
                    target_gram = self.gram_matrix(target_gram)
                    style_loss += (style_wt_meas[layer] * torch.mean((target_gram - style_gram) ** 2)) / d * w * h

                total_loss = content_wt * content_loss + style_wt * style_loss

                if i % 100 == 0:
                    print("epoch ", i, " ", total_loss)

                optimizer.zero_grad()
                total_loss.backward()
                optimizer.step()
                """
                if i % print_after == 0:
                    plt.imshow(imcnvt(target), label="Epoch " + str(i))
                    plt.show()
                    print(time.time() - now)
                    plt.imsave(os.path.join(save_path, str(i) + '.png'), imcnvt(target), format='png')
                """
            print(time.time()-now)
            self.parent.transfered2 = True
            print(target.shape)
            target = target.detach().numpy()
            target = np.transpose(target, (1, 2, 0))
            image = self.parent.process_image(target, 256)
            image = tf.keras.preprocessing.image.array_to_img(image)

            image.save("stylized_image2.png")
            self.parent.stylized_image2_label.setPixmap(QtGui.QPixmap("stylized_image2.png"))
            self.parent.button_static.setEnabled(True)
            self.parent.button_abstract.setEnabled(True)


    def imcnvt(self, image):
        x = image.to("cpu").clone().detach().numpy().squeeze()
        x = x.transpose(1, 2, 0)
        x = x * np.array((0.5, 0.5, 0.5)) + np.array((0.5, 0.5, 0.5))
        return np.clip(x, 0, 1)


    def model_activations(self, input, model):
        layers = {
            '0': 'conv1_1',
            '5': 'conv2_1',
            '10': 'conv3_1',
            '19': 'conv4_1',
            '21': 'conv4_2',
            '28': 'conv5_1'
        }
        features = {}
        x = input
        x = x.unsqueeze(0)
        for name, layer in model._modules.items():
            x = layer(x)
            if name in layers:
                features[layers[name]] = x
        return features

    def gram_matrix(self, imgfeature):
        _, d, h, w = imgfeature.size()
        imgfeature = imgfeature.view(d, h * w)
        gram_mat = torch.mm(imgfeature, imgfeature.t())
        return gram_mat



class Widget(QtWidgets.QWidget):
    def __init__(self, images_static, images_abstract):
        super().__init__()
        self.button_static = QtWidgets.QPushButton("Pick another object image randomly", self)
        self.button_abstract = QtWidgets.QPushButton("Pick another abstract image randomly", self)
        self.button_static.resize(100, 50)
        self.button_abstract.resize(100, 50)
        self.size = QtCore.QSize(256, 256)
        self.images_static = images_static
        self.images_abstract = images_abstract

        self.static_image_label = QtWidgets.QLabel()
        self.static_choice = "./static_art/flower10.jpg"
        self.static_image = QtGui.QPixmap("./static_art/flower10.jpg")
        self.static_image = self.static_image.scaled(self.size, QtCore.Qt.KeepAspectRatio)
        self.static_image_label.setPixmap(self.static_image)
        self.static_note = QtWidgets.QLabel("Content image")

        self.abstract_image_label = QtWidgets.QLabel()
        self.abstract_choice = "./abstract_art/Ivana Olbright_Desert Roses.jpg"
        self.abstract_image = QtGui.QPixmap("./abstract_art/Ivana Olbright_Desert Roses.jpg")
        self.abstract_image = self.abstract_image.scaled(self.size, QtCore.Qt.KeepAspectRatio)
        self.abstract_image_label.setPixmap(self.abstract_image)
        self.abstract_note = QtWidgets.QLabel("Style image")

        self.your_image = QtGui.QImage(256, 256, QtGui.QImage.Format_RGB32)
        self.your_image.fill(QtGui.QColor(255, 255, 255))

        self.your_image = QtGui.QPixmap.fromImage(self.your_image)
        self.your_image_label = QtWidgets.QLabel()
        self.your_image_label.setPixmap(self.your_image)
        self.your_image_note = QtWidgets.QLabel("User style transfer")

        self.button_draw = QtWidgets.QPushButton("Start drawing...", self)
        self.button_draw.clicked.connect(self.draw)
        self.button_draw.resize(100, 50)

        self.button_upload = QtWidgets.QPushButton("Upload image...", self)
        self.button_upload.clicked.connect(self.upload)
        self.button_upload.resize(100, 50)

        self.stylized_image = QtGui.QImage(256, 256, QtGui.QImage.Format_RGB32)
        self.stylized_image.fill(QtGui.QColor(255, 255, 255))
        self.stylized_image = QtGui.QPixmap.fromImage(self.stylized_image)
        self.stylized_image_label = QtWidgets.QLabel()
        self.stylized_image_label.setPixmap(self.stylized_image)
        self.stylized_note = QtWidgets.QLabel("AI style transfer1")

        self.stylized_image2 = QtGui.QImage(256, 256, QtGui.QImage.Format_RGB32)
        self.stylized_image2.fill(QtGui.QColor(255, 255, 255))
        self.stylized_image2 = QtGui.QPixmap.fromImage(self.stylized_image2)
        self.stylized_image2_label = QtWidgets.QLabel()
        self.stylized_image2_label.setPixmap(self.stylized_image2)
        self.stylized_note = QtWidgets.QLabel("AI style transfer2")

        self.button_stylize = QtWidgets.QPushButton("Begin image style transfer...", self)
        self.button_stylize.clicked.connect(self.style_transfer_aux)
        self.button_stylize.resize(100, 50)
        self.vgg19 = StyleTransferVGG19(self)
        self.button_stylize2 = QtWidgets.QPushButton("Begin image style transfer...", self)
        self.button_stylize2.clicked.connect(self.style_transfer_aux2)
        self.button_stylize2.resize(100, 50)

        self.layout0 = QtWidgets.QHBoxLayout()
        self.static_note.resize(30, 5)
        self.abstract_note.resize(30, 5)
        self.your_image_note.resize(30, 5)
        self.stylized_note.resize(30, 5)
        self.layout0.addWidget(self.static_note)
        self.layout0.addWidget(self.abstract_note)
        self.layout0.addWidget(self.your_image_note)
        self.layout0.addWidget(self.stylized_note)

        self.layout1 = QtWidgets.QHBoxLayout()
        self.layout1.addWidget(self.static_image_label)
        self.layout1.addWidget(self.abstract_image_label)
        self.layout1.addWidget(self.your_image_label)
        self.layout1.addWidget(self.stylized_image_label)
        self.layout1.addWidget(self.stylized_image2_label)

        self.layout2 = QtWidgets.QVBoxLayout()
        self.layout2.addWidget(self.button_draw)
        self.layout2.addWidget(self.button_upload)

        self.layout3 = QtWidgets.QHBoxLayout()
        self.layout3.addWidget(self.button_static)
        self.layout3.addWidget(self.button_abstract)
        self.layout3.addLayout(self.layout2)
        self.layout3.addWidget(self.button_stylize)
        self.layout3.addWidget(self.button_stylize2)

        self.label_message = QtWidgets.QLabel()
        self.label_message.setStyleSheet(" font-size: 16px;")
        self.label_message.setFixedHeight(50)
        self.layout4 = QtWidgets.QVBoxLayout()
        self.button_compare = QtWidgets.QPushButton("Begin image comparison...", self)
        self.button_compare.clicked.connect(self.compare)
        self.button_compare.setEnabled(False)
        self.label_comparison = QtWidgets.QLabel("Current similarity (from 0 to 10): Empty")
        self.label_comparison.setFixedHeight(50)
        self.label_comparison.setStyleSheet(" font-size: 16px;")

        self.label_name = QtWidgets.QLabel("Author and name of the abstract art image: Ivana Olbright - Desert Roses")
        self.label_name.setFixedHeight(50)
        self.label_name.setStyleSheet(" font-size: 16px;")

        self.layout4.addWidget(self.label_message)
        self.layout4.addWidget(self.label_name)
        self.layout4.addWidget(self.label_comparison)
        self.layout4.addWidget(self.button_compare)

        self.drawed = False
        self.transfered = False
        self.transfered2 = False
        self.compare_model = ModelEncoder()
        checkpoint = tf.train.Checkpoint(self.compare_model)
        checkpoint.restore("./check1/cp.ckpt")
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.layout1)
        self.layout.addLayout(self.layout3)
        self.layout.addLayout(self.layout4)
        self.setLayout(self.layout)
        self.button_static.clicked.connect(self.changeStatic)
        self.button_abstract.clicked.connect(self.changeAbstract)
        self.setAttribute(QtCore.Qt.WA_StaticContents)
        self.resize(1000, 900)


    def changeStatic(self):
        img_choice = choice(self.images_static)
        self.static_choice = img_choice
        image = QtGui.QPixmap(img_choice)
        image = image.scaled(self.size, QtCore.Qt.KeepAspectRatio)
        self.static_image_label.setPixmap(image)
        self.button_stylize.setEnabled(True)
        self.drawed = False
        self.transfered = False
        self.transfered2 = False
        self.button_compare.setEnabled(False)
        self.label_comparison.setText("Current similarity (from 0 to 10): Empty")


    def changeAbstract(self):
        img_choice = choice(self.images_abstract)
        author = ""
        c = img_choice[0]
        i = 1
        name = ""
        while c != "_":
            author += c
            c = img_choice[i]
            i += 1

        while c != ".":
            c = img_choice[i]
            i += 1
            name += c
        self.abstract_choice = os.path.join("./abstract_art", img_choice)
        image = QtGui.QPixmap(self.abstract_choice)
        image = image.scaled(self.size, QtCore.Qt.KeepAspectRatio)
        self.abstract_image_label.setPixmap(image)
        self.button_stylize.setEnabled(True)
        self.drawed = False
        self.transfered = False
        self.transfered2 = False
        self.button_compare.setEnabled(False)
        self.label_name.setText("Author and name of the abstract art image: " + author + " - " + name)
        self.label_comparison.setText("Current similarity (from 0 to 10): Empty")


    def compare(self):
        self.button_compare.setEnabled(False)
        self.your_image.save("my_drawing.png")
        your_drawing = img.open("my_drawing.png")
        your_drawing_np = np.array(your_drawing)
        stylized_image = img.open("stylized_image.png")
        stylized_image_np = np.array(stylized_image)

        your_drawing_rgb = self.process_image(tf.convert_to_tensor(your_drawing_np), 256)
        stylized_image_rgb = self.process_image(tf.convert_to_tensor(stylized_image_np), 256)

        your_drawing = your_drawing_rgb.numpy()
        stylized_image = stylized_image_rgb.numpy()

        alpha_channels = np.empty((256, 256, 1))
        alpha_channels.fill(255)

        if your_drawing.shape[-1] == 3:
            your_drawing = np.concatenate((your_drawing, alpha_channels), axis=2)

        if stylized_image.shape[-1] == 3:
            stylized_image = np.concatenate((stylized_image, alpha_channels), axis=2)

        your_drawing = np.expand_dims(your_drawing, axis=0)
        stylized_image = np.expand_dims(stylized_image, axis=0)

        your_drawing = tf.cast(your_drawing, tf.float32) / 255.
        stylized_image = tf.cast(stylized_image, tf.float32) / 255.

        your_drawing_info = self.compare_model(your_drawing)
        stylized_image_info = self.compare_model(stylized_image)

        sim = self.similarity(your_drawing_info, stylized_image_info)
        sim = sim/512 * 10
        self.label_comparison.setText("Current similarity (from 0 to 10): "+str(round(sim, 2)))
        self.button_static.setEnabled(True)
        self.button_abstract.setEnabled(True)



    def similarity(self, image1, image2, threshold=5):
        image1 = tf.squeeze(image1)
        image2 = tf.squeeze(image2)
        suma = 0
        for i in range(512):
            suma += 1 if abs(image1[i] - image2[i]) < threshold else 0
        return suma


    def draw(self):
        self.button_upload.setEnabled(False)
        self.button_static.setEnabled(False)
        self.button_abstract.setEnabled(False)
        self.button_stylize.setEnabled(False)
        self.window = MainWindow(self)
        self.window.show()
        if not self.transfered:
            x = threading.Thread(target=self.style_transfer, args=())
            x.start()
        if not self.transfered2:
            #torch.device("cuda")
            with tf.device("/GPU:0"):
                y = threading.Thread(target=self.vgg19.stylize, args=("drawing",))
                #y.device =
                y.start()


    def style_transfer_aux(self):
        x = threading.Thread(target=self.style_transfer, args=())
        x.start()


    def style_transfer_aux2(self):
        with tf.device("/GPU:0"):
            x = threading.Thread(target=self.vgg19.stylize, args=())
            x.start()


    def style_transfer(self, thread=None):
        #if self.drawed:
        self.button_static.setEnabled(False)
        self.button_abstract.setEnabled(False)
        self.button_stylize.setEnabled(False)
        self.label_message.setText("Currently style transfering...You may draw/re-draw/upload an image or begin 2nd style transferring")
        now = time.time()
        content_image = self.load_image(self.static_choice)
        content_image = self.load_content_image(content_image)

        style_image = self.load_image(self.abstract_choice)
        style_predict_path = tf.keras.utils.get_file('style_predict.tflite',
                                                     'https://tfhub.dev/sayakpaul/lite-model/arbitrary-image-stylization-inceptionv3-dynamic-shapes/int8/predict/1?lite-format=tflite')
        style_transform_path = tf.keras.utils.get_file('style_transform.tflite',
                                                       'https://tfhub.dev/sayakpaul/lite-model/arbitrary-image-stylization-inceptionv3-dynamic-shapes/int8/transfer/1?lite-format=tflite')
        content_image_size = 256.0

        if len(content_image.shape) > 3:
            content_image = tf.squeeze(content_image)

        if len(style_image.shape) > 3:
            style_image = tf.squeeze(style_image)

        preprocessed_content_image = self.process_image(content_image, tf.constant([content_image_size]))
        preprocessed_style_image = self.process_image(style_image, 256)
        preprocessed_style_image = tf.expand_dims(preprocessed_style_image, 0)
        style_bottleneck = self.style_predict(preprocessed_style_image, style_predict_path)

        stylized_image = self.style_transform(style_bottleneck, tf.expand_dims(preprocessed_content_image, 0),
                                             style_transform_path, content_image_size)
        if len(stylized_image.shape) > 3:
            stylized_image = tf.squeeze(stylized_image, axis=0)
        image = tf.keras.preprocessing.image.array_to_img(stylized_image)
        image.save("stylized_image.png")
        self.stylized_image_label.setPixmap(QtGui.QPixmap("stylized_image.png"))
        now = time.time() - now
        print("Time took to style transfer with the new method: " + str(now) + " seconds")
        self.label_comparison.setText("Current similarity (from 0 to 10): Empty")
        self.label_message.setText("")
        self.transfered = True
        if self.drawed:
            self.button_compare.setEnabled(True)
        self.button_static.setEnabled(True)
        self.button_abstract.setEnabled(True)
        if thread is not None:
            threading.currentThread().join()



    def style_predict(self, processed_style_image, style_predict_path):
        interpreter = tf.lite.Interpreter(model_path=style_predict_path)

        interpreter.allocate_tensors()
        input_details = interpreter.get_input_details()
        interpreter.set_tensor(input_details[0]["index"], processed_style_image)

        interpreter.invoke()
        style_bottleneck = interpreter.tensor(interpreter.get_output_details()[0]["index"])()
        return style_bottleneck


    def style_transform(self, style_bottleneck, processed_content_image, style_transform_path, content_image_size):
        interpreter = tf.lite.Interpreter(model_path=style_transform_path)

        input_det = interpreter.get_input_details()
        for index in range(len(input_det)):
            if input_det[index]["name"] == 'content_image':
                index = input_det[index]["index"]
                interpreter.resize_tensor_input(index, [1, content_image_size, content_image_size, 3])
        interpreter.allocate_tensors()

        for index in range(len(input_det)):
            if input_det[index]["name"] == 'Conv/BiasAdd':
                interpreter.set_tensor(input_det[index]["index"], style_bottleneck)
            elif input_det[index]["name"] == 'content_image':
                interpreter.set_tensor(input_det[index]["index"], processed_content_image)
        interpreter.invoke()

        stylized_image = interpreter.tensor(interpreter.get_output_details()[0]["index"])()
        return stylized_image


    def load_image(self, path_to_img):
        img = tf.io.read_file(path_to_img)
        img = tf.io.decode_image(img, channels=3)
        img = tf.image.convert_image_dtype(img, tf.float32)
        img = img[tf.newaxis, :]
        return img


    def process_image(self, image, target_dim):
        shape = tf.cast(tf.shape(image)[0:-1], tf.float32)
        short_dim = min(shape)
        scale = target_dim / short_dim
        new_shape = tf.cast(shape * scale, tf.int32)
        image = tf.image.resize(image, new_shape)
        image = tf.image.resize_with_crop_or_pad(image, int(target_dim), int(target_dim))
        return image


    def load_content_image(self, image_pix):
        if image_pix.shape[-1] == 4:
            image_pixels = Image.fromarray(image_pix)
            image = image_pixels.convert('RGB')
            image = np.array(image)
            image = tf.convert_to_tensor(image)
            image = tf.image.convert_image_dtype(image, tf.float32)
            image = image[tf.newaxis, :]
            return image
        elif image_pix.shape[-1] == 3:
            image = tf.convert_to_tensor(image_pix)
            image = tf.image.convert_image_dtype(image, tf.float32)
            image = image[tf.newaxis, :]
            return image
        elif image_pix.shape[-1] == 1:
            raise TypeError('Grayscale images not supported! Please try with RGB or RGBA images.')
        print('Exception not thrown')


    def upload(self):
        self.button_static.setEnabled(False)
        self.button_abstract.setEnabled(False)
        fileName, _filter = QtWidgets.QFileDialog.getOpenFileName(self, self.tr("Open File"), QtCore.QDir.currentPath())
        loadedImage = QtGui.QPixmap(fileName)
        loadedImage = loadedImage.scaled(self.size, QtCore.Qt.KeepAspectRatio)
        self.your_image = loadedImage
        self.your_image_label.setPixmap(loadedImage)
        self.button_upload.setText("Upload another image...")
        self.button_static.setEnabled(True)
        self.button_abstract.setEnabled(True)
        self.drawed = True
        if self.transfered:
            self.button_compare.setEnabled(True)
        self.label_comparison.setText("Current similarity (from 0 to 10): Empty")


class App(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        #window = MainWindow()
        self.setWindowTitle(self.tr("Style Transfer Experiment"))
        self.setWindowIcon(QtGui.QIcon(':the_scream'))
        static_art = os.listdir("./static_art")
        #abstract_art = os.listdir("./abstract_art")
        self.static_images = [os.path.join("./static_art", e) for e in static_art]
        self.abstract_images = os.listdir("./abstract_art")
            #[os.path.join("./abstract_art", e) for e in abstract_art]
        self.image_widget = Widget(self.static_images, self.abstract_images)
        self.setCentralWidget(self.image_widget)

        self.resize(1280, 720)





def pr(t, val ,tb):
    QtWidgets.QMessageBox.critical(None, "", val)
    print(val)

def ex(t, val, tb):
    QtWidgets.QMessageBox.critical(None, "", val)
    print(val)




sys.breakpointhook = pr
sys.excepthook = ex


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    myStyle = MyProxyStyle('Plastique')
    app.setStyle(myStyle)
    window = App()
    window.show()
    app.exec()