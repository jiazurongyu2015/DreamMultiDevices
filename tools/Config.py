﻿    # -*- coding: utf-8 -*-
__author__ = "无声"
import configparser
import os
con = configparser.ConfigParser()

#解析config文件并将其结果转成一个list，对单个的value，到时候可以用[0]来取到。
def getValue(path,key):
    con.read(path)
    result = con.get("config",key)
    list=result.split(",")
    return list

def getTestCase(path,device=""):
    if device!="":
        con.read(path)
        result = con.get("TestCaseforDevice",device)
        list=result.split(",")
        return list
    else:
        return []

def setValue(configpath,key,value):
    if  key!="" and value!="":
        con.set("config",key,value)
        con.write(open(configpath, "w"))



