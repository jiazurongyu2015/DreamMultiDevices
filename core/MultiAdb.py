# -*- coding: utf-8 -*-
__author__ = "无声"

import os,inspect
import sys
import threading
import queue
from DreamMultiDevices.core import RunTestCase
from DreamMultiDevices.tools import Config
from airtest.core.api import *
from airtest.core.error import *
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
from airtest.core.android.adb import ADB
import  subprocess

_print = print
def print(*args, **kwargs):
    _print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), *args, **kwargs)

adb = ADB().adb_path
q = queue.Queue()

class MultiAdb:

    def __init__(self,mdevice=""):
        self._parentPath=os.path.abspath(os.path.dirname(inspect.getfile(inspect.currentframe())) + os.path.sep + ".")
        self._rootPath=os.path.abspath(os.path.dirname(self._parentPath) + os.path.sep + ".")
        self._configPath=self._rootPath+"\config.ini"
        self._devicesList = Config.getValue(self._configPath, "deviceslist", )
        self._packagePath = Config.getValue(self._configPath, "apkpath")[0]
        self._packageName = Config.getValue(self._configPath, "packName")[0]
        self._needClickInstall = Config.getValue(self._configPath, "needclickinstall")[0]
        self._needClickStartApp = Config.getValue(self._configPath, "needclickstartapp")[0]
        self._startTime=time.time()
        self._timeoutAction=int(Config.getValue(self._configPath, "timeoutperaction")[0])
        self._timeoutStartApp=int(Config.getValue(self._configPath, "timeoutofstartapp")[0])
        self._mdevice=mdevice
        # 处理模拟器端口用的冒号
        if ":" in self._mdevice:
            self._nickName = self._mdevice.split(":")[1]
        else:
            self._nickName=self._mdevice
        self._iteration=int(Config.getValue(self._configPath, "iteration")[0])
        self._allTestcase=Config.getValue(self._configPath, "testcase")
        try:
            self._testcaseForSelfDevice =Config.getTestCase(self._configPath, self._nickName)
            if self._testcaseForSelfDevice[0]=="":
                self._testcaseForSelfDevice = self._allTestcase
        except Exception:
            self._testcaseForSelfDevice=self._allTestcase
        self._testCasePath=Config.getValue(self._configPath, "testcasepath")
        if self._testCasePath[0]=="":
            self._testCasePath=os.path.join(self._rootPath, "TestCase")

    def get_devicesList(self):
        return self._devicesList

    def get_apkpath(self):
        return self._packagePath

    def get_packagename(self):
        return self._packageName

    def get_needclickinstall(self):
        return self._needClickInstall

    def get_needclickstartapp(self):
        return self._needClickStartApp

    def get_mdevice(self):
        return self._mdevice

    def get_nickname(self):
        return self._nickName

    def get_timeoustartspp(self):
        return self._timeoutStartApp

    def get_timeoutaction(self):
        return self._timeoutAction

    def get_iteration(self):
        return self._iteration

    def get_alltestcase(self):
        return self._allTestcase

    def get_testcaseforselfdevice(self):
        return self._testcaseForSelfDevice

    def get_TestCasePath(self):
        return self._testCasePath

    def set_mdevice(self,device):
        self._mdevice=device

    #写回包名、包路径、测试用例路径等等到配置文件

    def set_packagename(self,packagename):
        configPath=self._configPath
        Config.setValue(configPath,"packname",packagename)

    def set_packagepath(self, packagepath):
        configPath = self._configPath
        Config.setValue(configPath, "apkpath", packagepath)

    def set_TestCasePath(self,TestCasepath):
        configPath=self._configPath
        Config.setValue(configPath,"testcasepath",TestCasepath)

    # 本方法用于读取实时的设备连接
    def getdevices(self):
        deviceslist=[]
        for devices in os.popen(adb + " devices"):
            if "\t" in devices:
                if devices.find("emulator")<0:
                    if devices.split("\t")[1] == "device\n":
                        deviceslist.append(devices.split("\t")[0])
                        print("设备{}被添加到deviceslist中".format(deviceslist))
        return deviceslist

    def StartApp(self):
        devices=self.get_mdevice()
        needclickstartapp=self.get_needclickstartapp()
        print("{}进入StartAPP函数".format(devices))
        start_app(self.get_packagename())
        if needclickstartapp=="True":
            print("设备{}，needclickstartapp为{}，开始初始化pocoui，处理应用权限".format(devices,needclickstartapp))
            # 获取andorid的poco代理对象，准备进行开启应用权限（例如申请文件存储、定位等权限）点击操作
            pocoAndroid = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)
            n=self.get_iteration()
            if devices == "127.0.0.1:62001":
                # 这里是针对不同机型进行不同控件的选取，需要用户根据自己的实际机型实际控件进行修改
                count = 0
                while not pocoAndroid("android.view.View").exists():
                    print("{}开启应用的权限点击，循环第{}次".format(devices,count))
                    if count >= n:
                        break
                    if pocoAndroid("com.android.packageinstaller:id/permission_allow_button").exists():
                        pocoAndroid("com.android.packageinstaller:id/permission_allow_button").oclick()
                    else:
                        time.sleep(self.get_timeoutaction())
                        count += 1
            elif devices == "127.0.0.1:62025":
                count = 0
                while not pocoAndroid("android.view.View").exists():
                    print("{}开启应用的权限点击，循环第{}次".format(devices,count))
                    if count >= 3:
                        break
                    if pocoAndroid("android:id/button1").exists():
                        pocoAndroid("android:id/button1").click()
                    else:
                        time.sleep(3)
                        count += 1
        else:
            print("设备{}，needclickstartapp不为True，不做开启权限点击操作".format(devices))
        return None

    #推送apk到设备上的函数，读配置决定要不要进行权限点击操作。
    def PushApk2Devices(self):
        device=self.get_mdevice()
        needclickinstall=self.get_needclickinstall()
        try:
            installThread = threading.Thread(target=self.AppInstall, args=())
            installThread.start()
            result = q.get()
            if needclickinstall=="True":
                print("设备{}，needclickinstall为{}，开始进行安装点击权限操作".format(device,needclickinstall))
                inputThread = threading.Thread(target=self.InputEvent, args=(self,))
                inputThread.start()
                inputThread.join()
            else:
                print("设备{}，needclickinstall不为True，不进行安装点击权限操作".format(device))
            installThread.join()
            if result=="Install Success":
                return "Success"
            else:
                return "Fail"
        except Exception as e:
            print(e)
            pass

    def AppInstall(self):
        devices=self.get_mdevice()
        apkpath=self.get_apkpath()
        package=self.get_packagename()
        print("设备{}开始进行自动安装".format(devices))
        try:
            if self.isinstalled():
                uninstallcommand = adb + " -s " + str(devices) + " uninstall " + package
                print("正在{}上卸载{},卸载命令为：{}".format(devices, package, uninstallcommand))
                os.popen(uninstallcommand)
            time.sleep(self.get_timeoutaction())
            installcommand = adb + " -s " + str(devices) + " install -r " + apkpath
            result=os.popen(installcommand)
            for line in result:
                print("output={}".format(line))
            print("正在{}上安装{},安装命令为：{}".format(devices, package, installcommand))
            if self.isinstalled():
                print("{}上安装成功，退出AppInstall线程".format(devices))
                q.put("Install Success")
                return True
            else:
                print("{}上安装未成功".format(devices))
                q.put("Install Fail")
                return False
        except Exception as e:
            print("{}上安装异常".format(devices))
            print(e)
            q.put("Install Fail")

    def InputEvent(self):
        devices=self.get_mdevice()
        print("设备{}开始进行自动处理权限".format(devices))
        # 获取andorid的poco代理对象，准备进行开启安装权限（例如各个品牌的自定义系统普遍要求的二次安装确认、vivo/oppo特别要求的输入手机账号密码等）的点击操作。
        pocoAndroid = AndroidUiautomationPoco(use_airtest_input=True, screenshot_each_action=False)
        # 这里是针对不同机型进行不同控件的选取，需要用户根据自己的实际机型实际控件进行修改
        n = self.get_iteration()
        if devices == "127.0.0.1:62021":
            count = 0
            # 找n次或找到对象以后跳出，否则等5秒重试。
            while True:
                print("{}安装应用的权限点击，循环第{}次".format(devices,count))
                if count >= n:
                    print("{}退出InputEvent线程".format(devices))
                    break
                if pocoAndroid("com.coloros.safecenter:id/et_login_passwd_edit").exists():
                    pocoAndroid("com.coloros.safecenter:id/et_login_passwd_edit").set_text("qatest2019")
                    time.sleep(2)
                    if pocoAndroid("android.widget.FrameLayout").offspring("android:id/buttonPanel").offspring("android:id/button1").exists():
                        pocoAndroid("android.widget.FrameLayout").offspring("android:id/buttonPanel").offspring(
                            "android:id/button1").click()
                    break
                else:
                    time.sleep(5)
                count += 1
        elif devices == "127.0.0.1:62025":
            count = 0
            while True:
                print("{}安装应用的权限点击，循环第{}次".format(devices,count))
                if count >= n:
                    break
                if pocoAndroid("com.android.packageinstaller:id/continue_button").exists():
                    pocoAndroid("com.android.packageinstaller:id/continue_button").click()
                else:
                    time.sleep(5)
                count += 1

    #判断给定设备里是否已经安装了指定apk
    def isinstalled(self):
        devices=self.get_mdevice()
        package=self.get_packagename()
        command=adb + " -s {} shell pm list package".format(devices)
        commandresult=os.popen(command)
        print("设备{}进入isinstalled方法，package={}".format(devices,package))
        for pkg in commandresult:
            #print(pkg)
            if "package:" + package in pkg:
                print("在{}上发现已安装{}".format(devices,package))
                return True
        print("在{}上没找到包{}".format(devices,package))
        return False

    #判断给定设备的安卓版本号
    def get_androidversion(self):
        command=adb+" -s {} shell getprop ro.build.version.release".format(self.get_mdevice())
        version=os.popen(command).read()[0]
        return int(version)

    #判断给定设备运行指定apk时的内存占用
    def get_allocated_memory(self):
        command=adb + " -s {} shell dumpsys meminfo {}".format(self.get_mdevice(),self.get_packagename())
        print(command)
        memory=os.popen(command)
        list=[]
        for line in memory:
            line=line.strip()
            list=line.split(' ')
            if list[0]=="TOTAL":
                while '' in list:
                    list.remove('')
                allocated_memory=format(int(list[1])/1024,".2f")
                q.put(allocated_memory)
                return allocated_memory
        q.put("N/a")
        return "N/a"

    #判断给定设备运行时的内存总占用
    def get_totalmemory(self):
        command = adb + " -s {} shell dumpsys meminfo ".format(self.get_mdevice())
        print(command)
        memory=os.popen(command)
        TotalRAM=0
        for line in memory:
            line=line.strip()
            list = line.split(":")
            if list[0]=="Total RAM":
                if self.get_androidversion()<7:
                    TotalRAM = format(int(list[1].split(" ")[1])/1024,".2f")
                elif self.get_androidversion()>6:
                    TotalRAM = format(int(list[1].split("K")[0].replace(",",""))/1024,".2f")
                break
        q.put(TotalRAM)
        return  TotalRAM

    #判断给定设备运行时的空闲内存
    def get_freememory(self):
        command = adb + " -s {} shell dumpsys meminfo ".format(self.get_mdevice())
        print(command)
        memory = os.popen(command)
        FreeRAM=0
        for line in memory:
            line = line.strip()
            list = line.split(":")
            if list[0]=="Free RAM":
                if self.get_androidversion()<7:
                    FreeRAM = format(int(list[1].split(" ")[1])/1024,".2f")
                elif self.get_androidversion()>6:
                    FreeRAM = format(int(list[1].split("K")[0].replace(",",""))/1024,".2f")
                break
        q.put(FreeRAM)
        return  FreeRAM

    #判断给定设备运行时的总使用内存
    def get_usedmemory(self):
        command = adb + " -s {} shell dumpsys meminfo ".format(self.get_mdevice())
        print(command)
        memory = os.popen(command)
        UsedRAM=0
        for line in memory:
            line = line.strip()
            list = line.split(":")
            if list[0]=="Used RAM":
                if self.get_androidversion()<7:
                    UsedRAM = format(int(list[1].split(" ")[1])/1024,".2f")
                elif self.get_androidversion()>6:
                    UsedRAM = format(int(list[1].split("K")[0].replace(",",""))/1024,".2f")
                break
        q.put(UsedRAM)
        return  UsedRAM

    #判断给定设备运行时的Total/Free/Used内存,一次dump，加快获取速度
    def get_memoryinfo(self):
        command = adb + " -s {} shell dumpsys meminfo ".format(self.get_mdevice())
        #print(command)
        memory = os.popen(command)
        androidversion=self.get_androidversion()
        for line in memory:
            line = line.strip()
            list = line.split(":")
            if list[0]=="Total RAM":
                if androidversion<7:
                    TotalRAM = format(int(list[1].split(" ")[1])/1024,".2f")
                elif androidversion>6:
                    TotalRAM = format(int(list[1].split("K")[0].replace(",",""))/1024,".2f")
            elif list[0]=="Free RAM":
                if androidversion<7:
                    FreeRAM = format(int(list[1].split(" ")[1])/1024,".2f")
                elif androidversion > 6:
                    FreeRAM = format(int(list[1].split("K")[0].replace(",",""))/1024,".2f")
            elif list[0] == "Used RAM":
                if androidversion<7:
                    UsedRAM = format(int(list[1].split(" ")[1]) / 1024, ".2f")
                elif androidversion > 6:
                    UsedRAM = format(int(list[1].split("K")[0].replace(",", "")) / 1024, ".2f")
        q.put(TotalRAM,FreeRAM,UsedRAM)
        return  TotalRAM, FreeRAM,UsedRAM

    #判断给定设备运行时的总CPU占用，对安卓8以上，CPU总数不一定是100%，视手机CPU内核数决定。
    def get_totalcpu(self):
        starttime =time.time()
        command = adb + " -s {} shell top -n 1 ".format(self.get_mdevice())
        print(command)
        commandresult =os.popen(command)
        cputotal=0
        andversion=self.get_androidversion()
        #print("get_totalcpu",time.time()-starttime)
        maxcpu=""
        for line in commandresult:
            list=line.strip().split(" ")
            while '' in list:
                list.remove('')
            #print(list)
            if len(list)>8:
                if andversion <7:
                    print(list)
                    if ("%" in list[2]and list[2]!="CPU%"):
                        cpu=int(list[2][:-1])
                        if cpu!=0:
                            cputotal=cputotal+cpu
                        else:
                            break
                elif andversion ==7 :
                    #print(list)
                    if ("%" in list[4] and list[4] != "CPU%"):
                        cpu = int(list[4][:-1])
                        if cpu != 0:
                            cputotal = cputotal + cpu
                        else:
                            break
                elif andversion >7:
                    #print(list)
                    if "%cpu" in list[0]:
                        maxcpu = list[0]
                        #print(list)
                        #print(maxcpu)
                    try :
                        cpu=float(list[8])
                        if cpu != 0:
                            cputotal = cputotal + cpu
                        else:
                            break
                    except:
                        pass

        #print(time.time()-starttime,"cputotal=",cputotal,"%")
        totalcpu=str(format(cputotal, ".2f")) + "%"
        q.put(totalcpu,maxcpu)
        #print(totalcpu,maxcpu)
        return  totalcpu,maxcpu

    #判断给定设备运行时的总使用CPU
    def get_allocated_cpu(self):
        start=time.time()
        packagename=self.get_packagename()[0:11]
        command = adb + " -s {} shell top -n 1 |findstr {} ".format(self.get_mdevice(),packagename)
        print(command)
        subresult= os.popen(command).read()
        version=self.get_androidversion()
        if subresult == "" :
            q.put("N/a")
            return "N/a"
        else:
            cpuresult = subresult.split(" ")
            #去空白项
            while '' in cpuresult:
                cpuresult.remove('')
            #print(self.get_mdevice(),"cpuresult=",cpuresult)
            if version==6:
                cpu = cpuresult[2]
            elif version ==7:
                cpu=cpuresult[4]
            elif version>7:
                cpu = cpuresult[8]+"%"
            q.put(cpu)
            return cpu

if __name__ == "__main__":
    madb = MultiAdb("127.0.0.1:62025")
    madb.get_totalcpu()







