"""
美大客服独立站 - Apple 风格支持网站

运行方式：
- 安装：pip install -r requirements.txt
- 启动：uvicorn main:app --reload
- 打开：http://127.0.0.1:8000/
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from datetime import date, timedelta

app = FastAPI(title="美大客服支持中心")

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板配置
templates = Jinja2Templates(directory="templates")

# 内置数据
products = [
    {"slug": "integrated-stove", "name": "集成灶", "icon": "🔥"},
    {"slug": "range-hood", "name": "油烟机", "icon": "🌫️"},
    {"slug": "hob", "name": "灶具", "icon": "🍳"},
    {"slug": "sterilizer", "name": "消毒柜", "icon": "🧼"},
    {"slug": "water-heater", "name": "热水器", "icon": "🚿"}
]

issues = {
    "integrated-stove": [
        {"code": "E0", "title": "燃气安全监测（E0）"},
        {"code": "E1", "title": "点火系统监测（E1）"},
        {"code": "E2", "title": "意外熄火监测（E2）"},
        {"code": "E3", "title": "定时功能监测（E3）"},
        {"code": "E4", "title": "门控开关监测（E4）"},
        {"code": "E5", "title": "电磁灶锅具监测（E5）"},
        {"code": "E6", "title": "防火墙功能启动（E6）"},
        {"code": "E7", "title": "防火墙功能监测（E7）"},
        {"code": "E8", "title": "炉头温度传感器监测（E8）"},
        {"code": "E9", "title": "炉头过热监测（E9）"},
        {"code": "E10", "title": "档位信号监测（E10）"},
        {"code": "E11", "title": "鼓风机监测（E11）"},
        {"code": "E12", "title": "鼓风机转速偏离监测（E12）"},
        {"code": "E13", "title": "风机联动信号监测（E13）"},
        {"code": "E14", "title": "变频电路过压监测（E14）"},
        {"code": "E15", "title": "变频电路欠压监测（E15）"},
        {"code": "E16", "title": "变频电路过流监测（E16）"},
        {"code": "E17", "title": "变频电路过温监测（E17）"},
        {"code": "E18", "title": "变频电机缺相监测（E18）"},
        {"code": "E19", "title": "变频电机堵转监测（E19）"},
        {"code": "E20", "title": "变频电机失步监测（E20）"},
        {"code": "E21", "title": "变频电机超速监测（E21）"},
        {"code": "E22", "title": "电动风门开闭监测（E22）"},
        {"code": "other", "title": "其他现象（无故障码）"}
    ],
    "range-hood": [
        {"code": "noise", "title": "噪音异常"},
        {"code": "low-suction", "title": "吸力变弱"},
        {"code": "shake", "title": "机身抖动"},
        {"code": "other", "title": "其他问题"}
    ],
    "hob": [
        {"code": "ignite", "title": "打不着火 / 火焰不稳"},
        {"code": "smell", "title": "异味/疑似漏气"},
        {"code": "other", "title": "其他问题"}
    ],
    "sterilizer": [
        {"code": "not-heat", "title": "不加热/温度异常"},
        {"code": "odor", "title": "异味"},
        {"code": "other", "title": "其他问题"}
    ],
    "water-heater": [
        {"code": "temp-fluct", "title": "忽冷忽热"},
        {"code": "no-ignite", "title": "无法点火"},
        {"code": "other", "title": "其他问题"}
    ]
}

# 解决方案数据
solutions = {
    "integrated-stove": {
        "E0": {
            "steps": [
                "关闭燃气总阀，切断燃气供应",
                "检查室内是否有燃气泄漏的气味",
                "确保室内通风良好",
                "等待10分钟后，重新打开燃气阀门",
                "重启设备，观察故障是否消失"
            ],
            "note": "E0故障表示燃气安全监测异常，可能是燃气泄漏或燃气传感器故障，如果问题持续存在，请立即联系专业技术人员检修",
            "causes": [
                "漏气报警",
                "燃烧不充分报警气敏头报警",
                "异味报警",
                "气敏头太灵敏",
                "气敏头线短路"
            ],
            "user_check": [
                "检查燃气是否有存在泄漏现象",
                "厨房是否喷有味道比较重的喷剂"
            ],
            "solution_advice": "断电重启后仍无法处理，联系售后上门检测"
        },
        "E1": {
            "steps": [
                "检查燃气阀门是否打开，确保燃气供应正常",
                "检查燃气是否用尽，如使用液化气请检查气罐",
                "尝试重新启动设备，观察是否恢复正常",
                "检查点火针是否有污垢或损坏"
            ],
            "note": "E1故障表示点火系统监测异常，如果以上步骤无法解决问题，可能是点火装置故障，建议预约专业技术人员上门检修",
            "causes": [
                "燃气表电池",
                "燃气自闭阀跳闸",
                "内火圈火孔堵塞",
                "电池故障"
            ],
            "user_check": [
                "检查燃气表电池是否有充足电量",
                "检查燃气自闭阀是否打开",
                "用牙签通下内火圈出火孔",
                "检查机子里储电池盒是否需要更换电池"
            ],
            "solution_advice": "若仍无法点火，联系售后上门检查"
        },
        "E2": {
            "steps": [
                "检查使用环境是否有强风导致意外熄火",
                "确保燃气供应稳定，检查气压是否正常",
                "清洁燃烧器表面的污垢",
                "关闭设备，等待5分钟后重新启动"
            ],
            "note": "E2故障表示意外熄火监测，通常是因为火焰意外熄灭或熄火保护装置触发，如果问题持续存在，可能需要检查熄火保护装置",
            "causes": [
                "空气不足",
                "汤水溢出",
                "出火孔堵塞"
            ],
            "user_check": [
                "检查机子台面上是否垫有锡纸引起空气不足导致的熄火情况",
                "汤水溢出拿吹风机吹干出火炉盘，清理后方可使用",
                "牙签通小炉盖的出火孔"
            ],
            "solution_advice": "若仍无法点火，联系售后上门检查"
        },
        "E3": {
            "steps": [
                "关闭电源，等待10秒后重新启动",
                "重置定时功能设置",
                "检查控制面板是否有按键卡住的情况",
                "恢复出厂设置（参考说明书中的具体操作）"
            ],
            "note": "E3故障与定时功能监测有关，通常是定时器电路或控制面板问题",
            "causes": [
                "连接插件松脱，重新连接后使用",
                "显示屏损坏，更换显示屏",
                "脉冲坏，更换脉冲"
            ],
            "user_check": [
                "连接插件松脱，重新连接后使用",
                "显示屏损坏，更换显示屏",
                "脉冲坏，更换脉冲"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E4": {
            "steps": [
                "检查设备门是否完全关闭",
                "清洁门控开关周围的污垢",
                "轻轻开关设备门几次，确保门控开关正常工作",
                "关闭电源，等待10秒后重新启动"
            ],
            "note": "E4故障表示门控开关监测异常，可能是门控开关松动或损坏",
            "causes": [
                "E4 代表在消毒或烘干时门控开关断开或门未关好",
                "检查门是否关好",
                "门控开关是否松脱"
            ],
            "user_check": [
                "消毒柜机子E4报警检查是否有东西卡住",
                "检查消毒柜门是否关好"
            ],
            "solution_advice": "若检查后还无法处理需要专业师傅上门"
        },
        "E5": {
            "steps": [
                "检查电磁灶上的锅具是否适合电磁炉使用",
                "移除锅具，清洁电磁灶表面",
                "确保锅具底部平整且干净",
                "重新放置锅具，确保其位于电磁灶中央",
                "重启设备，观察故障是否消失"
            ],
            "note": "E5故障表示电磁灶锅具监测异常，通常是因为锅具不适合或放置不当",
            "causes": [
                "使用适合锅具或锅具未放好"
            ],
            "user_check": [
                "使用适合锅具或锅具未放好"
            ],
            "solution_advice": "若检查后还无法处理需专业师傅上门"
        },
        "E6": {
            "steps": [
                "关闭设备，等待设备冷却（约30分钟）",
                "检查设备周围是否有易燃物品，确保安全距离",
                "确保设备通风良好",
                "重启设备，观察故障是否消失"
            ],
            "note": "E6故障表示防火墙功能启动，这是一种安全保护机制，通常在检测到潜在火灾风险时触发",
            "causes": [
                "防火墙线坏",
                "显示屏坏",
                "显示屏或电源板(白防火墙线插那跟那有关系)"
            ],
            "user_check": [
                "防火墙线坏",
                "显示屏坏",
                "显示屏或电源板(白防火墙线插那跟那有关系)"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E7": {
            "steps": [
                "关闭设备，等待设备冷却",
                "检查防火墙组件是否有明显损坏",
                "清洁设备内部可能的灰尘和油污",
                "重启设备，观察故障是否消失"
            ],
            "note": "E7故障表示防火墙功能监测异常，可能是防火墙组件故障或传感器异常",
            "causes": [
                "防火墙线未插好",
                "防火墙线坏",
                "显示屏坏或电源板(白防火墙线插那跟那有关系)"
            ],
            "user_check": [
                "防火墙线未插好",
                "防火墙线坏",
                "显示屏坏或电源板(白防火墙线插那跟那有关系)"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E8": {
            "steps": [
                "关闭设备，等待设备冷却",
                "检查炉头周围是否有异物或油污堆积",
                "清洁炉头表面",
                "重启设备，观察故障是否消失"
            ],
            "note": "E8故障表示炉头温度传感器监测异常，可能是温度传感器损坏或连接松动",
            "causes": [
                "连接插件松脱，重新连接后使用",
                "温度传感器损坏，更换温度传感器",
                "控制器损坏，更换控制器"
            ],
            "user_check": [
                "连接插件松脱，重新连接后使用",
                "温度传感器损坏，更换温度传感器",
                "控制器损坏，更换控制器"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E9": {
            "steps": [
                "立即关闭设备，等待设备完全冷却（至少1小时）",
                "检查炉头周围是否有异物或油污堆积",
                "确保设备通风良好",
                "检查是否长时间高温烹饪导致过热",
                "设备冷却后重新启动，观察故障是否消失"
            ],
            "note": "E9故障表示炉头过热监测，这是一种安全保护机制，在炉头温度过高时触发",
            "causes": [
                "燃烧器温度过高，待降温后再使用",
                "温度传感器异常，更换燃烧器温度传感器",
                "控制器坏，更换控制器"
            ],
            "user_check": [
                "燃烧器温度过高，待降温后再使用",
                "温度传感器异常，更换燃烧器温度传感器",
                "控制器坏，更换控制器"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E10": {
            "steps": [
                "关闭设备，等待10秒后重新启动",
                "检查控制面板是否有按键卡住的情况",
                "旋转火力调节旋钮几次，确保其灵活转动",
                "恢复出厂设置（参考说明书中的具体操作）"
            ],
            "note": "E10故障表示档位信号监测异常，通常与控制面板或火力调节系统有关",
            "causes": [
                "点火时，旋钮没有旋到档位，关闭重新打开",
                "霍尔开关线松脱，重新接插",
                "总成内磁感应块坏，更换磁感应块"
            ],
            "user_check": [
                "点火时，旋钮没有旋到档位，关闭重新打开",
                "霍尔开关线松脱，重新接插",
                "总成内磁感应块坏，更换磁感应块"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E11": {
            "steps": [
                "关闭设备，等待5分钟后重新启动",
                "检查鼓风机周围是否有异物阻挡",
                "清洁鼓风机进风口和出风口",
                "检查鼓风机是否有异常声音"
            ],
            "note": "E11故障表示鼓风机监测异常，可能是鼓风机损坏或连接松动",
            "causes": [
                "异物长堵，清理后使用",
                "鼓风机坏，更换鼓风机"
            ],
            "user_check": [
                "异物长堵，清理后使用",
                "鼓风机坏，更换鼓风机"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E12": {
            "steps": [
                "关闭设备，等待5分钟后重新启动",
                "检查并清洁鼓风机进风口和出风口是否有异物堵塞",
                "检查鼓风机叶片是否有油污堆积，如有请清洁",
                "检查排风管道是否畅通，清除可能的堵塞物"
            ],
            "note": "E12故障表示鼓风机转速偏离监测，通常是因为鼓风机转速异常或传感器故障",
            "causes": [
                "连接线松脱，重新连接",
                "鼓风机坏，更换鼓风机",
                "控制器坏，更换控制器"
            ],
            "user_check": [
                "连接线松脱，重新连接",
                "鼓风机坏，更换鼓风机",
                "控制器坏，更换控制器"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E13": {
            "steps": [
                "关闭设备，等待5分钟后重新启动",
                "检查风机连接线是否松动",
                "确保排风管道安装正确且无变形",
                "重启设备，观察故障是否消失"
            ],
            "note": "E13故障表示风机联动信号监测异常，可能是风机控制系统或连接线路问题",
            "causes": [
                "脉冲损坏，更换脉冲"
            ],
            "user_check": [
                "脉冲损坏，更换脉冲"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E14": {
            "steps": [
                "关闭设备，切断电源",
                "检查家庭电源电压是否稳定",
                "等待10分钟后恢复电源并重启设备",
                "避免与大功率电器同时使用同一电路"
            ],
            "note": "E14故障表示变频电路过压监测，通常是因为电源电压过高或电路保护机制触发",
            "causes": [
                "点火开关坏，更换点火开关"
            ],
            "user_check": [
                "点火开关坏，更换点火开关"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E15": {
            "steps": [
                "关闭设备，检查家庭电源电压是否稳定",
                "避免使用过长或不合规格的电源延长线",
                "等待10分钟后重启设备",
                "检查是否有其他大功率电器同时使用导致电压下降"
            ],
            "note": "E15故障表示变频电路欠压监测，通常是因为电源电压过低或电路保护机制触发",
            "causes": [
                "用户市电压过高，等电压稳定后，恢复正常",
                "电源板被干扰，检查点火针位置是否碎裂或靠近脉冲接地端",
                "电源板故障误报警，更换电源板"
            ],
            "user_check": [
                "用户市电压过高，等电压稳定后，恢复正常",
                "电源板被干扰，检查点火针位置是否碎裂或靠近脉冲接地端",
                "电源板故障误报警，更换电源板"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E16": {
            "steps": [
                "关闭设备，切断电源",
                "检查设备是否过载运行",
                "等待设备冷却（约30分钟）",
                "重新接通电源并启动设备，避免立即使用高功率模式"
            ],
            "note": "E16故障表示变频电路过流监测，通常是因为电路负载过大或短路保护机制触发",
            "causes": [
                "电机连接线接触不良;检查电机插线是否有松脱情况，重新插好即可",
                "电源板被干扰，检查点火针是否碎裂或靠近脉冲接地端",
                "电源板故障误报警，更换电源板"
            ],
            "user_check": [
                "电压不稳",
                "电源板故障误报警"
            ],
            "solution_advice": "断电重启后仍无法处理，联系售后上门检测"
        },
        "E17": {
            "steps": [
                "关闭设备，切断电源",
                "确保设备通风良好，散热孔未被堵塞",
                "等待设备完全冷却（至少1小时）",
                "重新接通电源并启动设备，观察故障是否消失"
            ],
            "note": "E17故障表示变频电路过温监测，通常是因为散热不良或环境温度过高",
            "causes": [
                "电机连接线接触不良;检查电机插线是否有松脱情况，重新插好即可",
                "电源板被干扰，检查点火针是否碎裂或靠近脉冲接地端",
                "电源板故障误报警，更换电源板"
            ],
            "user_check": [
                "电机连接线接触不良;检查电机插线是否有松脱情况，重新插好即可",
                "电源板被干扰，检查点火针是否碎裂或靠近脉冲接地端",
                "电源板故障误报警，更换电源板"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E18": {
            "steps": [
                "关闭设备，切断电源",
                "检查电源线是否完好无损",
                "确保电源插座接触良好",
                "等待10分钟后重新接通电源并启动设备"
            ],
            "note": "E18故障表示变频电机缺相监测，通常是因为电源相线连接异常或电机线路问题",
            "causes": [
                "电机连接线是否存在脱线情况(未接触)",
                "电机连接线线序错误;更换电机线"
            ],
            "user_check": [
                "电机连接线是否存在脱线情况(未接触)",
                "电机连接线线序错误;更换电机线"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E19": {
            "steps": [
                "关闭设备，切断电源",
                "检查风机或电机是否被异物卡住",
                "手动转动风机叶片（断电状态下），确认是否能自由转动",
                "清除可能的堵塞物",
                "等待10分钟后重新启动设备"
            ],
            "note": "E19故障表示变频电机堵转监测，通常是因为电机转动受阻或机械故障",
            "causes": [
                "叶轮卡住，无法运转",
                "电源板故障，误报警，更换电源板"
            ],
            "user_check": [
                "叶轮卡住，无法运转",
                "电源板故障，误报警，更换电源板"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E20": {
            "steps": [
                "关闭设备，切断电源",
                "等待10分钟后重新接通电源",
                "启动设备时避免立即使用高速档位",
                "观察设备运行是否平稳"
            ],
            "note": "E20故障表示变频电机失步监测，通常是因为电机控制系统异常或负载突变",
            "causes": [
                "电源板被干扰，检查点火针是否碎裂"
            ],
            "user_check": [
                "电源板被干扰，检查点火针是否碎裂"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E21": {
            "steps": [
                "关闭设备，切断电源",
                "等待10分钟后重新接通电源",
                "启动设备时使用低速档位，逐渐调整至所需档位",
                "避免频繁快速调整档位"
            ],
            "note": "E21故障表示变频电机超速监测，通常是因为电机控制系统异常或速度传感器故障",
            "causes": [
                "电源板故障，误报警，更换电源板"
            ],
            "user_check": [
                "电源板故障，误报警，更换电源板"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "E22": {
            "steps": [
                "关闭设备，切断电源",
                "检查风门是否有异物卡住",
                "清洁风门周围的灰尘和油污",
                "手动轻轻推动风门（断电状态下），确认其是否能自由移动",
                "重新接通电源并启动设备"
            ],
            "note": "E22故障表示电动风门开闭监测异常，通常是因为风门机构卡住或电机故障",
            "causes": [
                "检查止逆风门开启、关闭是否正常",
                "检查止逆风门侧板连接端是否存在短路现像",
                "止逆风门连接线短路象",
                "电源板故障，更换电源板"
            ],
            "user_check": [
                "检查止逆风门开启、关闭是否正常",
                "检查止逆风门侧板连接端是否存在短路现像",
                "止逆风门连接线短路象",
                "电源板故障，更换电源板"
            ],
            "solution_advice": "需要联系售后安排专业师傅上门"
        },
        "other": {
            "steps": [
                "关闭电源和燃气阀门",
                "检查设备是否有明显的异常声音或气味",
                "检查电源和燃气连接是否正常",
                "尝试重新启动设备"
            ],
            "note": "由于故障现象多样，建议详细描述您遇到的具体问题，以便我们提供更精准的解决方案"
        }
    }
}

# 工具函数
def get_product_by_slug(slug: str):
    """根据 slug 获取产品信息"""
    for product in products:
        if product["slug"] == slug:
            return product
    return None

def get_issues_by_slug(slug: str):
    """根据产品 slug 获取问题列表"""
    return issues.get(slug, [])

def get_issue_by_code(product_slug: str, issue_code: str):
    """根据产品 slug 和问题代码获取问题信息"""
    product_issues = issues.get(product_slug, [])
    for issue in product_issues:
        if issue["code"] == issue_code:
            return issue
    return None

def get_solution(product_slug: str, issue_code: str):
    """获取解决方案"""
    product_solutions = solutions.get(product_slug, {})
    return product_solutions.get(issue_code, {"steps": [], "note": "暂无具体解决方案，请联系客服"})

# 路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """产品选择页"""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "products": products}
    )

@app.get("/issues/{slug}", response_class=HTMLResponse)
async def product_issues(request: Request, slug: str):
    """问题选择页"""
    product = get_product_by_slug(slug)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    product_issues = get_issues_by_slug(slug)
    
    # 调试输出
    print(f"产品: {product['name']}")
    print(f"故障代码数量: {len(product_issues)}")
    for i, issue in enumerate(product_issues):
        print(f"{i+1}. {issue['code']}: {issue['title']}")
    
    return templates.TemplateResponse(
        "issues.html",
        {
            "request": request,
            "product": product,
            "issues": product_issues
        }
    )

@app.get("/solution/{product_slug}/{issue_code}", response_class=HTMLResponse)
async def solution_page(request: Request, product_slug: str, issue_code: str):
    """解决方案页面"""
    product = get_product_by_slug(product_slug)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    
    issue = get_issue_by_code(product_slug, issue_code)
    if not issue:
        raise HTTPException(status_code=404, detail="问题不存在")
    
    solution = get_solution(product_slug, issue_code)
    today = date.today().isoformat()  # 当前日期，用于日期选择器的最小值
    
    return templates.TemplateResponse(
        "solution.html",
        {
            "request": request,
            "product": product,
            "issue": issue,
            "solution": solution,
            "today": today
        }
    )

# 404 页面处理
@app.exception_handler(404)
async def not_found_exception_handler(request: Request, exc: HTTPException):
    """自定义 404 页面"""
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "error": True,
            "error_msg": "页面不存在",
            "error_detail": "您访问的页面不存在或已被移除"
        },
        status_code=404
    )

# 添加此函数用于Cloudflare Pages
def create_app():
    return app 