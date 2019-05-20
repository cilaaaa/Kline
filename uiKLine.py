# -*- coding: utf-8 -*-
"""
Python K线模块,包含十字光标和鼠标键盘交互
Support By 量投科技(http://www.quantdo.com.cn/)
"""
import traceback
import numpy as np
import pandas as pd
from functools import partial
from collections import deque

from qtpy.QtGui import *
from qtpy.QtCore import *
from qtpy.QtWidgets import *
from qtpy import QtGui,QtCore
from uiCrosshair import Crosshair
import pyqtgraph as pg




# 字符串转换
#---------------------------------------------------------------------------------------
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

########################################################################
# 键盘鼠标功能
########################################################################
class KeyWraper(QWidget):
    """键盘鼠标功能支持的元类"""
    #初始化
    #----------------------------------------------------------------------
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setMouseTracking(True)

    #重载方法keyPressEvent(self,event),即按键按下事件方法
    #----------------------------------------------------------------------
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Up:
            self.onUp()
        elif event.key() == QtCore.Qt.Key_Down:
            self.onDown()
        elif event.key() == QtCore.Qt.Key_Left:
            self.onLeft()
        elif event.key() == QtCore.Qt.Key_Right:
            self.onRight()
        elif event.key() == QtCore.Qt.Key_PageUp:
            self.onPre()
        elif event.key() == QtCore.Qt.Key_PageDown:
            self.onNxt()

    #重载方法mousePressEvent(self,event),即鼠标点击事件方法
    #----------------------------------------------------------------------
    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.onRClick(event.pos())
        elif event.button() == QtCore.Qt.LeftButton:
            self.onLClick(event.pos())

    #重载方法mouseReleaseEvent(self,event),即鼠标点击事件方法
    #----------------------------------------------------------------------
    def mouseRelease(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.onRRelease(event.pos())
        elif event.button() == QtCore.Qt.LeftButton:
            self.onLRelease(event.pos())
        self.releaseMouse()

    #重载方法wheelEvent(self,event),即滚轮事件方法
    #----------------------------------------------------------------------
    def wheelEvent(self, event):
        return

    #重载方法paintEvent(self,event),即拖动事件方法
    #----------------------------------------------------------------------
    def paintEvent(self, event):
        self.onPaint()

    # PgDown键
    #----------------------------------------------------------------------
    def onNxt(self):
        pass

    # PgUp键
    #----------------------------------------------------------------------
    def onPre(self):
        pass

    # 向上键和滚轮向上
    #----------------------------------------------------------------------
    def onUp(self):
        pass

    # 向下键和滚轮向下
    #----------------------------------------------------------------------
    def onDown(self):
        pass
    
    # 向左键
    #----------------------------------------------------------------------
    def onLeft(self):
        pass

    # 向右键
    #----------------------------------------------------------------------
    def onRight(self):
        pass

    # 鼠标左单击
    #----------------------------------------------------------------------
    def onLClick(self,pos):
        pass

    # 鼠标右单击
    #----------------------------------------------------------------------
    def onRClick(self,pos):
        pass

    # 鼠标左释放
    #----------------------------------------------------------------------
    def onLRelease(self,pos):
        pass

    # 鼠标右释放
    #----------------------------------------------------------------------
    def onRRelease(self,pos):
        pass

    # 画图
    #----------------------------------------------------------------------
    def onPaint(self):
        pass


########################################################################
# 选择缩放功能支持
########################################################################
class CustomViewBox(pg.ViewBox):
    #----------------------------------------------------------------------
    def __init__(self, *args, **kwds):
        pg.ViewBox.__init__(self, *args, **kwds)
        # 拖动放大模式
        #self.setMouseMode(self.RectMode)
        
    ## 右键自适应
    #----------------------------------------------------------------------
    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            self.autoRange()


########################################################################
# 时间序列，横坐标支持
########################################################################
class MyStringAxis(pg.AxisItem):
    """时间序列横坐标支持"""
    
    # 初始化 
    #----------------------------------------------------------------------
    def __init__(self, xdict, *args, **kwargs):
        pg.AxisItem.__init__(self, *args, **kwargs)
        self.minVal = 0 
        self.maxVal = 0
        self.xdict  = xdict
        self.x_values = np.asarray(xdict.keys())
        self.x_strings = xdict.values()
        self.setPen(color=(255, 255, 255, 255), width=0.8)
        self.setStyle(tickFont = QFont("Roman times",10,QFont.Bold),autoExpandTextSpace=True)

    # 更新坐标映射表
    #----------------------------------------------------------------------
    def update_xdict(self, xdict):
        self.xdict.update(xdict)
        self.x_values  = np.asarray(self.xdict.keys())
        self.x_strings = self.xdict.values()

    # 将原始横坐标转换为时间字符串,第一个坐标包含日期
    #----------------------------------------------------------------------
    def tickStrings(self, values, scale, spacing):
        strings = []
        for v in values:
            vs = v * scale
            if vs in self.x_values:
                vstr = self.x_strings[np.abs(self.x_values-vs).argmin()]
                vstr = vstr.strftime('%Y-%m-%d %H:%M:%S')
            else:
                vstr = ""
            strings.append(vstr)
        return strings

########################################################################
# K线图形对象
########################################################################
class CandlestickItem(pg.GraphicsObject):
    """K线图形对象"""

    # 初始化
    #----------------------------------------------------------------------
    def __init__(self, data):
        """初始化"""
        pg.GraphicsObject.__init__(self)
        # 数据格式: [ (time, open, close, low, high),...]
        self.data = data
        # 只重画部分图形，大大提高界面更新速度
        self.rect = None
        self.picture = None
        self.setFlag(self.ItemUsesExtendedStyleOption)
        # 画笔和画刷
        w = 0.4
        self.offset   = 0
        self.low      = 0
        self.high     = 1
        self.picture  = QtGui.QPicture()
        self.pictures = []
        self.bPen     = pg.mkPen(color='#17A63A', width=w*2)
        self.bBrush   = pg.mkBrush('#17A63A')
        self.rPen     = pg.mkPen(color='#D91A2A', width=w*2)
        self.rBrush   = pg.mkBrush('#D91A2A')
        self.rBrush.setStyle(Qt.NoBrush)
        # 刷新K线
        self.generatePicture(self.data)          


    # 画K线
    #----------------------------------------------------------------------
    def generatePicture(self,data=None,redraw=False):
        """重新生成图形对象"""
        # 重画或者只更新最后一个K线
        if redraw:
            self.pictures = []
        elif self.pictures:
            self.pictures.pop()
        w = 0.4
        bPen   = self.bPen
        bBrush = self.bBrush
        rPen   = self.rPen
        rBrush = self.rBrush
        self.low,self.high = (np.min(data['low']),np.max(data['high'])) if len(data)>0 else (0,1)
        npic = len(self.pictures)
        for (t, open0, close0, low0, high0) in data:
            if t >= npic:
                picture = QtGui.QPicture()
                p = QtGui.QPainter(picture)
                # 下跌蓝色（实心）, 上涨红色（空心）
                pen,brush,pmin,pmax = (bPen,bBrush,close0,open0)\
                    if open0 > close0 else (rPen,rBrush,open0,close0)
                p.setPen(pen)  
                p.setBrush(brush)
                # 画K线方块和上下影线
                if open0 == close0:
                    p.drawLine(QtCore.QPointF(t-w,open0), QtCore.QPointF(t+w, close0))
                else:
                    p.drawRect(QtCore.QRectF(t-w, open0, w*2, close0-open0))
                if pmin  > low0:
                    p.drawLine(QtCore.QPointF(t,low0), QtCore.QPointF(t, pmin))
                if high0 > pmax:
                    p.drawLine(QtCore.QPointF(t,pmax), QtCore.QPointF(t, high0))
                p.end()
                self.pictures.append(picture)

    # 手动重画
    #----------------------------------------------------------------------
    def update(self):
        if not self.scene() is None:
            self.scene().update()

    # 自动重画
    #----------------------------------------------------------------------
    def paint(self, painter, opt, w):
        rect = opt.exposedRect
        xmin,xmax = (max(0,int(rect.left())),min(int(len(self.pictures)),int(rect.right())))
        if not self.rect == (rect.left(),rect.right()) or self.picture is None:
            self.rect = (rect.left(),rect.right())
            self.picture = self.createPic(xmin,xmax)
            self.picture.play(painter)
        elif not self.picture is None:
            self.picture.play(painter)

    # 缓存图片
    #----------------------------------------------------------------------
    def createPic(self,xmin,xmax):
        picture = QPicture()
        p = QPainter(picture)
        [pic.play(p) for pic in self.pictures[xmin:xmax]]
        p.end()
        return picture

    # 定义边界
    #----------------------------------------------------------------------
    def boundingRect(self):
        return QtCore.QRectF(0,self.low,len(self.pictures),(self.high-self.low))


########################################################################
class KLineWidget(KeyWraper):
    """用于显示价格走势图"""

    # 窗口标识
    clsId = 0

    # 保存K线数据的列表和Numpy Array对象
    listBar  = []
    listVol  = []
    listHigh = []
    listLow  = []
    listSig  = []
    listOpenInterest = []
    arrows   = []

    # 是否完成了历史数据的读取
    initCompleted = False
    
    #----------------------------------------------------------------------
    def __init__(self,parent=None):
        """Constructor"""
        self.parent = parent
        super(KLineWidget, self).__init__(parent)

        # 当前序号
        self.index    = None    # 下标
        self.countK   = 60      # 显示的Ｋ线范围

        KLineWidget.clsId += 1
        self.windowId = str(KLineWidget.clsId)
        self.xmin = 0
        self.xmax = 1

        # 缓存数据
        self.datas    = []
        self.listBar  = []
        self.listVol  = []
        self.listHigh = []
        self.listLow  = []
        self.listSig  = []
        self.listOpenInterest = []
        self.arrows   = []

        # 所有K线上信号图
        self.allColor = {
                            'MA5' : '#63B8FF',
                            'MA10': '#FFFF00',
                            'MA20': '#6959CD',
                            'MA60': '#ADFF2F'
        }
        self.sigData  = {}
        self.sigColor = {}
        self.sigPlots = {}

        # 所副图上信号图
        self.allSubColor = deque(['blue','green','yellow','white'])
        self.subSigData  = {}
        self.subSigColor = {}
        self.subSigPlots = {}

        # 初始化完成
        self.initCompleted = False

        # 调用函数
        self.initUi()

    def out_xulie(self):
        try:
            self.out_btn.setEnabled(False)
            self.out_btn.setText("导出中…")
            data = np.array(sorted(self.listSig,key=lambda x:x[0]))
            for i in range(len(data)):
                data[i][0] = self.datas[int(data[i][0])][0]
                if data[i][2] == 'high':
                    data[i][2] = '高点'
                else:
                    data[i][2] = '低点'
            df = pd.DataFrame(data,columns=['日期','价格','类型'])
            df.to_excel('标记点统计.xlsx')
            QMessageBox.information(self, "信息",   "已成功导出到当前目录下“标记点统计.xlsx”", QMessageBox.Yes)
            self.out_btn.setEnabled(True)
            self.out_btn.setText("导出子序列点")
        except Exception as e:
            print(traceback.print_exc())

    #----------------------------------------------------------------------
    #  初始化相关 
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'K线工具')
        # 主图
        self.pw = pg.PlotWidget()
        # 界面布局
        self.lay_KL = pg.GraphicsLayout(border=(100,100,100))
        self.lay_KL.setContentsMargins(10, 10, 10, 10)
        self.lay_KL.setSpacing(0)
        self.lay_KL.setBorder(color=(255, 255, 255, 255), width=0.8)
        self.lay_KL.setZValue(0)
        self.KLtitle = self.lay_KL.addLabel(u'')
        self.out_btn = QPushButton('导出子序列点')
        self.out_btn.clicked.connect(self.out_xulie) # 绑定按钮点击信号

        self.pw.setCentralItem(self.lay_KL)
        # 设置横坐标
        xdict = {}
        self.axisTime = MyStringAxis(xdict, orientation='bottom')
        # 初始化子图
        self.initplotKline()
        self.initplotVol()
        self.initplotOI()
        # 注册十字光标
        self.crosshair = Crosshair(self.pw,self)
        # 设置界面
        self.vb = QVBoxLayout()
        self.vb.addWidget(self.out_btn)
        self.vb.addWidget(self.pw)
        self.setLayout(self.vb)
        # 初始化完成
        self.initCompleted = True    

    #----------------------------------------------------------------------
    def makePI(self,name):
        """生成PlotItem对象"""
        vb = CustomViewBox()
        plotItem = pg.PlotItem(viewBox = vb, name=name ,axisItems={'bottom': self.axisTime})
        plotItem.setMenuEnabled(False)
        plotItem.setClipToView(True)
        plotItem.hideAxis('left')
        plotItem.showAxis('right')
        plotItem.setDownsampling(mode='peak')
        plotItem.setRange(xRange = (0,1),yRange = (0,1))
        plotItem.getAxis('right').setWidth(60)
        plotItem.getAxis('right').setStyle(tickFont = QFont("Roman times",10,QFont.Bold))
        plotItem.getAxis('right').setPen(color=(255, 255, 255, 255), width=0.8)
        plotItem.showGrid(True,True)
        plotItem.hideButtons()
        return plotItem

    #----------------------------------------------------------------------
    def initplotVol(self):
        """初始化成交量子图"""
        self.pwVol  = self.makePI('_'.join([self.windowId,'PlotVOL']))
        self.volume = CandlestickItem(self.listVol)
        self.pwVol.addItem(self.volume)
        self.pwVol.setMaximumHeight(5)
        self.pwVol.setXLink('_'.join([self.windowId,'PlotOI']))
        self.pwVol.hideAxis('bottom')

        self.lay_KL.nextRow()
        self.lay_KL.addItem(self.pwVol)

    #----------------------------------------------------------------------
    def initplotKline(self):
        """初始化K线子图"""
        self.pwKL = self.makePI('_'.join([self.windowId,'PlotKL']))
        self.candle = CandlestickItem(self.listBar)
        self.pwKL.addItem(self.candle)
        self.pwKL.setMinimumHeight(350)
        self.pwKL.setXLink('_'.join([self.windowId,'PlotOI']))
        self.pwKL.hideAxis('bottom')

        self.lay_KL.nextRow()
        self.lay_KL.addItem(self.pwKL)

    #----------------------------------------------------------------------
    def initplotOI(self):
        """初始化持仓量子图"""
        self.pwOI = self.makePI('_'.join([self.windowId,'PlotOI']))
        self.pwOI.setMaximumHeight(50)
        self.curveOI = self.pwOI.plot()

        self.lay_KL.nextRow()
        self.lay_KL.addItem(self.pwOI)

    #----------------------------------------------------------------------
    #  画图相关 
    #----------------------------------------------------------------------
    def plotVol(self,redraw=False,xmin=0,xmax=-1):
        """重画成交量子图"""
        if self.initCompleted:
            self.volume.generatePicture(self.listVol[xmin:xmax],redraw)   # 画成交量子图

    #----------------------------------------------------------------------
    def plotKline(self,redraw=False,xmin=0,xmax=-1):
        """重画K线子图"""
        if self.initCompleted:
            self.candle.generatePicture(self.listBar[xmin:xmax],redraw)   # 画K线
            self.showSig(self.sigData)
            self.plotMark()                                               # 显示开平仓信号位置

    #----------------------------------------------------------------------
    def plotOI(self,xmin=0,xmax=-1):
        """重画持仓量子图"""
        if self.initCompleted:
            self.curveOI.setData(np.append(self.listOpenInterest[xmin:xmax],0), pen='w', name="OpenInterest")

    #----------------------------------------------------------------------
    def addSig(self,sig,main=True):
        """新增信号图"""
        if main:
            if sig in self.sigPlots:
                self.pwKL.removeItem(self.sigPlots[sig])
            self.sigPlots[sig] = self.pwKL.plot()
            self.sigColor[sig] = self.allColor[sig]
            # self.allColor.append(self.allColor.popleft())
        else:
            if sig in self.subSigPlots:
                self.pwOI.removeItem(self.subSigPlots[sig])
            self.subSigPlots[sig] = self.pwOI.plot()
            self.subSigColor[sig] = self.allSubColor[0]
            self.allSubColor.append(self.allSubColor.popleft())

    #----------------------------------------------------------------------
    def showSig(self,datas,main=True,clear=False):
        """刷新信号图"""
        if clear:
            self.clearSig(main)
            if datas and not main:
                sigDatas = np.array(datas.values()[0])
                self.listOpenInterest = sigDatas
                self.datas['openInterest'] = sigDatas
                self.plotOI(0,len(sigDatas))
        if main:
            for sig in datas:
                self.addSig(sig,main)
                # self.sigData[sig] = datas[sig]
                self.sigPlots[sig].setData(np.append(datas[sig],0), pen=self.sigColor[sig], name=sig)
        else:
            for sig in datas:
                self.addSig(sig,main)
                self.subSigData[sig] = datas[sig]
                self.subSigPlots[sig].setData(np.append(datas[sig],0), pen=self.subSigColor[sig][0], name=sig)

    #----------------------------------------------------------------------
    def plotMark(self):
        """显示开平仓信号"""
        # 检查是否有数据
        if len(self.datas)==0:
            return
        for i in range(len(self.arrows)):
            arrow = self.arrows[0]
            self.pwKL.removeItem(self.arrows[0])
            self.arrows.remove(self.arrows[0])
        # 画买卖信号
        # for i in range(len(self.listSig)):
        #     # 无信号
        #     if self.listSig[i][0] == 0:
        #         continue
        #     # 买开信号
        #     elif self.listSig[i][0] == 1:
        #         arrow = pg.ArrowItem(pos=(i, self.listSig[i][1]),  angle=90, brush=(255, 0, 0))
        #     # 买平信号
        #     elif self.listSig[i][0] == 3:
        #         arrow = pg.ArrowItem(pos=(i, self.listSig[i][1]),  angle=90, brush=(255, 255, 0))
        #     # 卖开信号
        #     elif self.listSig[i][0] == 2:
        #         arrow = pg.ArrowItem(pos=(i, self.listSig[i][1]), angle=-90, brush=(0, 255, 0))
        #     # 卖平信号
        #     elif self.listSig[i][0] == 4:
        #         arrow = pg.ArrowItem(pos=(i, self.listSig[i][1]), angle=-90, brush=(0, 0, 255))
        #     self.pwKL.addItem(arrow)
        #     self.arrows.append(arrow)
        for i in range(len(self.listSig)):
            arrow = pg.ArrowItem(pos=(self.listSig[i][0], self.listSig[i][1]), angle=-90, brush='y')
            self.pwKL.addItem(arrow)
            if arrow not in self.arrows:
                self.arrows.append(arrow)

    #----------------------------------------------------------------------
    def updateAll(self):
        """
        手动更新所有K线图形，K线播放模式下需要
        """
        datas = self.datas
        self.volume.pictrue = None
        self.candle.pictrue = None
        self.volume.update()
        self.candle.update()
        def update(view,low,high):
            vRange = view.viewRange()
            xmin = max(0,int(vRange[0][0]))
            xmax = max(0,int(vRange[0][1]))
            try:
                xmax = min(xmax,len(datas)-1)
            except:
                xmax = xmax
            if len(datas)>0 and xmax > xmin:
                ymin = min(datas[xmin:xmax][low])
                ymax = max(datas[xmin:xmax][high])
                view.setRange(yRange = (ymin,ymax))
            else:
                view.setRange(yRange = (0,1))
        update(self.pwKL.getViewBox(),'low','high')
        # update(self.pwVol.getViewBox(),'volume','volume')

    #----------------------------------------------------------------------
    def plotAll(self,redraw=True,xMin=0,xMax=-1):
        """
        重画所有界面
        redraw ：False=重画最后一根K线; True=重画所有
        xMin,xMax : 数据范围
        """
        xMax = len(self.datas)-1 if xMax < 0 else xMax
        #self.countK = xMax-xMin
        #self.index = int((xMax+xMin)/2)
        self.pwOI.setLimits(xMin=xMin,xMax=xMax)
        self.pwKL.setLimits(xMin=xMin,xMax=xMax)
        self.pwVol.setLimits(xMin=xMin,xMax=xMax)
        self.plotKline(redraw,xMin,xMax)                       # K线图
        self.plotVol(redraw,xMin,xMax)                         # K线副图，成交量
        self.plotOI(0,len(self.datas))                         # K线副图，持仓量
        self.refresh()

    #----------------------------------------------------------------------
    def refresh(self):
        """
        刷新三个子图的现实范围
        """   
        datas   = self.datas
        minutes = int(self.countK/2)
        xmin    = max(0,self.index-minutes)
        try:
            xmax    = min(xmin+2*minutes,len(self.datas)-1) if self.datas else xmin+2*minutes
        except:
            xmax    = xmin+2*minutes
        self.pwOI.setRange(xRange = (xmin,xmax))
        self.pwKL.setRange(xRange = (xmin,xmax))
        self.pwVol.setRange(xRange = (xmin,xmax))

    #----------------------------------------------------------------------
    #  快捷键相关 
    #----------------------------------------------------------------------
    def onNxt(self):
        """跳转到下一个开平仓点"""
        if len(self.listSig)>0 and not self.index is None:
            datalen = len(self.listSig)
            if self.index < datalen-2 : self.index+=1
            while self.index < datalen-2 and self.listSig[self.index] == 0:
                self.index+=1
            self.refresh()
            x = self.index
            y = self.datas[x]['close']
            self.crosshair.signal.emit((x,y))

    #----------------------------------------------------------------------
    def onPre(self):
        """跳转到上一个开平仓点"""
        if  len(self.listSig)>0 and not self.index is None:
            if self.index > 0: self.index-=1
            while self.index > 0 and self.listSig[self.index] == 0:
                self.index-=1
            self.refresh()
            x = self.index
            y = self.datas[x]['close']
            self.crosshair.signal.emit((x,y))

    #----------------------------------------------------------------------
    def onDown(self):
        """放大显示区间"""
        self.countK = min(len(self.datas),int(self.countK*1.2)+1)
        self.refresh()
        if len(self.datas)>0:
            x = self.index-self.countK/2+2 if int(self.crosshair.xAxis)<self.index-self.countK/2+2 else int(self.crosshair.xAxis)
            x = self.index+self.countK/2-2 if x>self.index+self.countK/2-2 else x
            x = len(self.datas)-1 if x > len(self.datas)-1 else int(x)
            y = self.datas[x][2]
            self.crosshair.signal.emit((x,y))

    #----------------------------------------------------------------------
    def onUp(self):
        """缩小显示区间"""
        self.countK = max(3,int(self.countK/1.2)-1)
        self.refresh()
        if len(self.datas)>0:
            x = self.index-self.countK/2+2 if int(self.crosshair.xAxis)<self.index-self.countK/2+2 else int(self.crosshair.xAxis)
            x = self.index+self.countK/2-2 if x>self.index+self.countK/2-2 else x
            x = len(self.datas)-1 if x > len(self.datas)-1 else int(x)
            y = self.datas[x]['close']
            self.crosshair.signal.emit((x,y))

    #----------------------------------------------------------------------
    def onLeft(self):
        """向左移动"""
        if len(self.datas)>0 and int(self.crosshair.xAxis)>2:
            x = int(self.crosshair.xAxis)-1
            x = len(self.datas)-1 if x > len(self.datas)-1 else int(x)
            y = self.datas[x]['close']
            if x <= self.index-self.countK/2+2 and self.index>1:
                self.index -= 1
                self.refresh()
            self.crosshair.signal.emit((x,y))

    #----------------------------------------------------------------------
    def onRight(self):
        """向右移动"""
        if len(self.datas)>0 and int(self.crosshair.xAxis)<len(self.datas)-1:
            x = int(self.crosshair.xAxis)+1
            x = len(self.datas)-1 if x > len(self.datas)-1 else int(x)
            y = self.datas[x]['close']
            if x >= self.index+int(self.countK/2)-2:
                self.index += 1
                self.refresh()
            self.crosshair.signal.emit((x,y))
    
    #----------------------------------------------------------------------
    # 界面回调相关
    #----------------------------------------------------------------------
    def getdp_add(self,data):
        # n = len(data)
        # result = []
        # seq = []
        # if n > 0:
        #     m = [0] * n
        #     for x in range(n - 2, -1, -1):
        #         for y in range(n - 1, x, -1):
        #             if data[x] < data[y] and m[x] <= m[y]:
        #                 m[x] += 1
        #         max_value = max(m)
        #         result = []
        #         seq = []
        #         for i in range(n):
        #             if m[i] == max_value:
        #                 result.append(data[i])
        #                 seq.append(i)
        #                 # 获取Seq返回
        #                 max_value -= 1
        #     if len(result) == 0:
        #         return None,None
        # return result[-1],seq[-1]
        result = []
        seq = []
        n = len(data)
        longest = 0
        biggest = 0
        for x in range(0,n-1):
            Max = data[x]
            temp = [Max]
            tempseq = [x]
            for y in range(x + 1,n):
                if Max < data[y]:
                    Max = data[y]
                    temp.append(Max)
                    tempseq.append(y)
            if len(temp) > longest:
                result = temp
                seq = tempseq
                longest = len(temp)
                biggest = Max
            elif len(temp) == longest:
                if Max >= biggest:
                    result = temp
                    seq = tempseq
                    longest = len(temp)
                    biggest = Max
        if len(result) == 0:
            return None,None
        return result[-1],seq[-1]

    def getdp_minus(self,data):
        # n = len(data)
        # result = []
        # seq = []
        # if n > 0:
        #     m = [0] * n
        #     for x in range(n - 2, -1, -1):
        #         for y in range(n - 1, x, -1):
        #             if data[x] > data[y] and m[x] <= m[y]:
        #                 m[x] += 1
        #         max_value = max(m)
        #         result = []
        #         seq = []
        #         for i in range(n):
        #             if m[i] == max_value:
        #                 result.append(data[i])
        #                 seq.append(i)
        #                 # 获取Seq返回
        #                 max_value -= 1
        #     if len(result) == 0:
        #         return None,None
        # return result[-1],seq[-1]
        result = []
        seq = []
        n = len(data)
        longest = 0
        biggest = 0
        for x in range(0,n-1):
            Max = data[x]
            temp = [Max]
            tempseq = [x]
            for y in range(x + 1,n):
                if Max > data[y]:
                    Max = data[y]
                    temp.append(Max)
                    tempseq.append(y)
            if len(temp) > longest:
                result = temp
                seq = tempseq
                longest = len(temp)
                biggest = Max
            elif len(temp) == longest:
                if Max <= biggest:
                    result = temp
                    seq = tempseq
                    longest = len(temp)
                    biggest = Max
        if len(result) == 0:
            return None,None
        return result[-1],seq[-1]

    def MarkDpAdd(self,xleft,data,quarterLen):
        rawData = data[:,4]
        SEH,SEHSEQ = self.getdp_add(rawData)
        if SEH != None:
            if SEHSEQ > 0:
                if len(data) - 1 - SEHSEQ > quarterLen:
                    rawData = data[SEHSEQ:]
                    self.MarkDpAdd(xleft + SEHSEQ,rawData,quarterLen)
                self.listSig.append([xleft + SEHSEQ,SEH,'high'])
                #S点和SEH点之间的最低点SEL
                rawData = data[:SEHSEQ,3]
                SELIndex = np.where(rawData == np.min(rawData))
                SEL = rawData[SELIndex][0]
                SELindex = int(SELIndex[0][-1])
                if SELindex > 0 and SEHSEQ - SELindex > 0:
                    if SEHSEQ - SELindex > quarterLen:
                        rawData = data[SELindex:SEHSEQ]
                        self.MarkDpMinus(xleft + SELindex,rawData,quarterLen)
                    self.listSig.append([xleft + SELindex,SEL,'low'])
                if SELindex > quarterLen:
                    rawData = data[:SELindex]
                    self.MarkDpAdd(xleft,rawData,quarterLen)

    def MarkDpMinus(self,xleft,data,quarterLen):
        rawData = data[:,3]
        SEL,SELSEQ = self.getdp_minus(rawData)
        if SEL != None:
            if SELSEQ > 0:
                if len(data) - 1 - SELSEQ > quarterLen:
                    rawData = data[SELSEQ:]
                    self.MarkDpMinus(xleft + SELSEQ,rawData,quarterLen)
                self.listSig.append([xleft + SELSEQ,SEL,'low'])
                #S点和SEL点之间的最高点SEH
                rawData = data[:SELSEQ,4]
                SEHIndex = np.where(rawData == np.max(rawData))
                SEH = rawData[SEHIndex][0]
                SEHindex = int(SEHIndex[0][-1])
                if SEHindex > 0 and SELSEQ - SEHindex > 0:
                    if SELSEQ - SEHindex > quarterLen:
                        rawData = data[SEHindex:SELSEQ]
                        self.MarkDpAdd(xleft + SEHindex,rawData,quarterLen)
                    self.listSig.append([xleft + SEHindex,SEH,'high'])
                if SEHindex > quarterLen:
                    rawData = data[:SEHindex]
                    self.MarkDpMinus(xleft,rawData,quarterLen)

    def onPaint(self):
        """界面刷新回调"""
        view = self.pwKL.getViewBox()
        vRange = view.viewRange()
        xmin = max(0,int(vRange[0][0]))
        xmax = max(0,int(vRange[0][1]))
        self.index  = int((xmin+xmax)/2)+1
        if self.xmin != xmin:
            #数据处理
            try:
                showData = np.array(self.datas[xmin:xmax].tolist())
                quarterLen = len(showData) / 4
                self.listSig = []
                #最高点
                highIndex = np.where(showData[:,4] == np.max(showData[:,4]))
                high = showData[highIndex,4][0][0]
                firstHighIndex = 0
                for i in range(len(list(highIndex)[0]) - 1):
                    if highIndex[0][i + 1] - highIndex[0][i] > 5:
                        firstHighIndex = int(highIndex[0][i])
                        self.listSig.append([xmin + int(highIndex[0][i]),high,'high'])
                if firstHighIndex == 0:
                    firstHighIndex = int(highIndex[0][-1])
                self.listSig.append([xmin + int(highIndex[0][-1]),high,'high'])
                #最低点
                lowIndex = np.where(showData[:,3] == np.min(showData[:,3]))
                low = showData[lowIndex,3][0][0]
                firstLowIndex = 0
                for i in range(len(list(lowIndex)[0]) - 1):
                    if lowIndex[0][i + 1] - lowIndex[0][i] > 5:
                        firstLowIndex = int(lowIndex[0][i])
                        self.listSig.append([xmin + int(lowIndex[0][i]),low,'low'])
                if firstLowIndex == 0:
                    firstLowIndex = int(lowIndex[0][-1])
                self.listSig.append([xmin + int(lowIndex[0][-1]),low,'low'])

                #低点先于高点
                if firstHighIndex > firstLowIndex:
                    #K线开始（S）至L点间最大递增子序列
                    rawData = showData[0:firstLowIndex]
                    self.MarkDpAdd(xmin,rawData,quarterLen)
                    #L点和H点之间的最大递减子序列
                    rawData = showData[firstLowIndex:firstHighIndex]
                    self.MarkDpMinus(xmin + firstLowIndex,rawData,quarterLen)
                    #H点和k线结束点E之间的最大递增子序列点HEH1点
                    rawData = showData[firstHighIndex:]
                    self.MarkDpAdd(xmin + firstHighIndex,rawData,quarterLen)
                else:
                    rawData = showData[0:firstHighIndex]
                    self.MarkDpMinus(xmin,rawData,quarterLen)
                    rawData = showData[firstHighIndex:firstLowIndex]
                    self.MarkDpAdd(xmin + firstHighIndex,rawData,quarterLen)
                    rawData = showData[firstLowIndex:]
                    self.MarkDpMinus(xmin + firstLowIndex,rawData,quarterLen)
                self.plotMark()

                self.xmin = xmin
                self.xmax = xmax
            except Exception as e:
                print(e)


    #----------------------------------------------------------------------
    def resignData(self,datas):
        """更新数据，用于Y坐标自适应"""
        self.crosshair.datas = datas
        def viewXRangeChanged(low,high,self):
            vRange = self.viewRange()
            xmin = max(0,int(vRange[0][0]))
            xmax = max(0,int(vRange[0][1]))
            xmax = min(xmax,len(datas))
            if len(datas)>0 and xmax > xmin:
                ymin = min(datas[xmin:xmax][low])
                ymax = max(datas[xmin:xmax][high])
                ymin,ymax = (-1,1) if ymin==ymax else (ymin,ymax)
                self.setRange(yRange = (ymin,ymax))
            else:
                self.setRange(yRange = (0,1))

        view = self.pwKL.getViewBox()
        view.sigXRangeChanged.connect(partial(viewXRangeChanged,'low','high'))
        # view = self.pwVol.getViewBox()
        # view.sigXRangeChanged.connect(partial(viewXRangeChanged,'volume','volume'))
        #
        # view = self.pwOI.getViewBox()
        # view.sigXRangeChanged.connect(partial(viewXRangeChanged,'openInterest','openInterest'))

    #----------------------------------------------------------------------
    # 数据相关
    #----------------------------------------------------------------------
    def clearData(self):
        """清空数据"""
        # 清空数据，重新画图
        self.time_index = []
        self.listBar = []
        self.listVol = []
        self.listLow = []
        self.listHigh = []
        self.listOpenInterest = []
        self.listSig = []
        self.sigData = {}
        self.datas = None

    #----------------------------------------------------------------------
    def clearSig(self,main=True):
        """清空信号图形"""
        # 清空信号图
        if main:
            for sig in self.sigPlots:
                self.pwKL.removeItem(self.sigPlots[sig])
            self.sigData  = {}
            self.sigPlots = {}
        else:
            for sig in self.subSigPlots:
                self.pwOI.removeItem(self.subSigPlots[sig])
            self.subSigData  = {}
            self.subSigPlots = {}

    #----------------------------------------------------------------------
    def updateSig(self,sig):
        """刷新买卖信号"""
        self.listSig = sig
        self.plotMark()

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """
        新增K线数据,K线播放模式
        """
        # 是否需要更新K线
        newBar = False if len(self.datas)>0 and bar.datetime==self.datas[-1].datetime else True
        nrecords = len(self.datas) if newBar else len(self.datas)-1
        bar.openInterest = np.random.randint(0,3) if bar.openInterest==np.inf or bar.openInterest==-np.inf else bar.openInterest
        recordVol = (nrecords,abs(bar.volume),0,0,abs(bar.volume)) if bar.close < bar.open else (nrecords,0,abs(bar.volume),0,abs(bar.volume))

        if newBar and any(self.datas):
            self.datas.resize(nrecords+1,refcheck=0)
            self.listBar.resize(nrecords+1,refcheck=0)
            self.listVol.resize(nrecords+1,refcheck=0)
        elif any(self.datas):
            self.listLow.pop()
            self.listHigh.pop()
            self.listOpenInterest.pop()
        if any(self.datas):
            self.datas[-1]   = (bar.datetime, bar.open, bar.close, bar.low, bar.high, bar.volume, bar.openInterest)
            self.listBar[-1] = (nrecords, bar.open, bar.close, bar.low, bar.high)
            self.listVol[-1] = recordVol
        else:
            self.datas     = np.rec.array([(bar.datetime, bar.open, bar.close, bar.low, bar.high, bar.volume, bar.openInterest)],\
                                        names=('datetime','open','close','low','high','volume','openInterest'))
            self.listBar   = np.rec.array([(nrecords, bar.open, bar.close, bar.low, bar.high)],\
                                     names=('time_int','open','close','low','high'))
            self.listVol   = np.rec.array([recordVol],names=('time_int','open','close','low','high'))
            self.resignData(self.datas)

        self.axisTime.update_xdict({nrecords:bar.datetime})
        self.listLow.append(bar.low)
        self.listHigh.append(bar.high)
        self.listOpenInterest.append(bar.openInterest)
        self.resignData(self.datas)
        return newBar

    #----------------------------------------------------------------------
    def loadData(self, datas, sigs = None):
        """
        载入pandas.DataFrame数据
        datas : 数据格式，cols : datetime, open, close, low, high
        """
        # 设置中心点时间
        # 绑定数据，更新横坐标映射，更新Y轴自适应函数，更新十字光标映射
        datas['time_int'] = np.array(range(len(datas.index)))
        self.datas = datas[['open','close','low','high']].to_records()
        self.axisTime.xdict={}
        xdict = dict(enumerate(datas.index.tolist()))
        self.axisTime.update_xdict(xdict)
        #移动平均值
        self.sigData["MA5"] = datas['close'].rolling(5).mean().values
        self.sigData["MA10"] = datas['close'].rolling(10).mean().values
        self.sigData["MA20"] = datas['close'].rolling(20).mean().values
        self.sigData["MA60"] = datas['close'].rolling(60).mean().values
        self.resignData(self.datas)
        # 更新画图用到的数据
        self.listBar          = datas[['time_int','open','close','low','high']].to_records(False)
        self.listHigh         = list(datas['high'])
        self.listLow          = list(datas['low'])
        # self.listOpenInterest = list(datas['openInterest'])
        # self.listSig          = np.zeros((len(datas)-1,2)) if sigs is None else sigs
        self.listSig = []
        # 成交量颜色和涨跌同步，K线方向由涨跌决定
        # datas0                = pd.DataFrame()
        # datas0['open']        = datas.apply(lambda x:0 if x['close'] >= x['open'] else x['volume'],axis=1)
        # datas0['close']       = datas.apply(lambda x:0 if x['close'] <  x['open'] else x['volume'],axis=1)
        # datas0['low']         = 0
        # datas0['high']        = datas['volume']
        # datas0['time_int']    = np.array(range(len(datas.index)))
        # self.listVol          = datas0[['time_int','open','close','low','high']].to_records(False)


    #----------------------------------------------------------------------
    def refreshAll(self, redraw=True, update=False):
        """
        更新所有界面
        """
        # 调用画图函数
        self.index = len(self.datas)
        self.plotAll(redraw,0,len(self.datas))
        if not update:
            self.updateAll()
        self.crosshair.signal.emit((None,None))

########################################################################
# 功能测试
########################################################################
import sys

def preLoadData(loadName, barInterval, startDate, endDate):
    barInterval = str(barInterval)
    data = pd.DataFrame.from_csv('./DataFiles/'+ loadName +'.csv')
    data = data[startDate:endDate]
    data.index = pd.to_datetime(data.index)
    ChangeData = data.resample(barInterval + 'S').last()
    ChangeData['open'] = data['open'].resample(barInterval + 'S').first()
    ChangeData['high'] = data['high'].resample(barInterval + 'S').max()
    ChangeData['low'] = data['low'].resample(barInterval + 'S').min()
    ChangeData['close'] = data['close'].resample(barInterval + 'S').last()
    ChangeData = ChangeData.dropna(axis=0,how='all')
    return ChangeData

if __name__ == '__main__':
    loadName = 'cfIF1811_future_quarter_1min'
    barInterval = 60
    startDate = '2018-11-01'
    endDate = '2018-11-03'
    preData = preLoadData(loadName, barInterval, startDate, endDate)
    app = QApplication(sys.argv)
    # 界面设置
    cfgfile = QtCore.QFile('css.qss')
    cfgfile.open(QtCore.QFile.ReadOnly)
    styleSheet = cfgfile.readAll()
    styleSheet = str(styleSheet, encoding='utf8')
    app.setStyleSheet(styleSheet)
    # K线界面
    ui = KLineWidget()
    ui.show()
    ui.KLtitle.setText(loadName, size='20pt')

    #sig = np.array(pd.DataFrame.from_csv('../PolicyBtcFuture0226-300-60-006-02-01Sig.csv',header=None,index_col=None))
    #ui.loadData(pd.DataFrame.from_csv('../okex_EOS_future_quarter_1min.csv'),sig)

    ui.loadData(preData)
    ui.refreshAll()
    app.exec_()
