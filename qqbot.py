#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
QQBot -- A conversation robot base on Tencent's SmartQQ
website: https://github.com/pandolia/qqbot/
author: pandolia@yeah.net
"""

QQBotVersion = "QQBot-v1.8.2"

import json, os, logging, pickle, sys, time, random, platform, subprocess
import requests, queue, threading
import config

# 'utf8', 'UTF8', 'utf-8', 'utf_8', None are all represent the same encoding
def codingEqual(coding1, coding2):
    return coding1 is None or coding2 is None or \
           coding1.replace('-', '').replace('_', '').lower() == \
           coding2.replace('-', '').replace('_', '').lower()

class CodingWrappedWriter:
    def __init__(self, coding, writer):
        self.coding, self.writer = coding, writer

    def write(self, s):
        return self.writer.write(s.decode(self.coding).encode(self.writer.encoding))

    def flush(self):
        return self.writer.flush()

# 在 windows consoler 下， 运行 print "中文" 会出现乱码
# 请使用： utf8_stdout.write("中文\n")
# 相当于： sys.stdout.write("中文\n".decode('utf8').encode(sys.stdout.encoding))
if codingEqual('utf8', sys.stdout.encoding):
    utf8_stdout = sys.stdout
else:
    utf8_stdout = CodingWrappedWriter('utf8', sys.stdout)

def QLogger(msg):
    try:
        print(str(msg).encode('gbk').decode('gbk','ignore'))
    except UnicodeEncodeError as error:
        pass

class RequestError(Exception):
    pass

class QQBot:
    def Login(self):
        if not os.path.exists('log.log'):
            QLogger('登录方式：手动登录')
            self.manualLogin()
        else:
            try:
                QLogger('登录方式：自动登录')
                self.autoLogin()
            except Exception as e:
                if not isinstance(e, RequestError):
                    QLogger('', exc_info=True)
                QLogger('自动登录失败，改用手动登录')
                self.manualLogin()

        QLogger('登录成功。登录账号：%s (%d)' % (self.nick, self.qqNum))

    def manualLogin(self):
        self.prepareLogin()
        self.getQrcode()
        self.waitForAuth()
        self.getPtwebqq()
        self.getVfwebqq()
        self.getUinAndPsessionid()
        self.testLogin()
        self.fetchBuddies()
        self.fetchGroups()
        self.fetchDiscusses()
        self.dumpSessionInfo()

    def autoLogin(self):
        self.loadSessionInfo()
        self.testLogin()

    def dumpSessionInfo(self):
        picklePath = os.path.join('log.log')
        try:
            with open(picklePath, 'wb') as f:
                pickle.dump(self.__dict__, f)
        except:
            QLogger('', exc_info=True)
            QLogger('保存登录 Session info 失败')
        else:
            QLogger('登录信息已保')
        self.pollSession = pickle.loads(pickle.dumps(self.session))

    def loadSessionInfo(self):
        picklePath = 'log.log'
        with open(picklePath, 'rb') as f:
            self.__dict__ = pickle.load(f)
            QLogger('成功从文件恢复登录')
        self.pollSession = pickle.loads(pickle.dumps(self.session))

    def prepareLogin(self):
        self.clientid = 53999199
        self.msgId = 6000000
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:27.0) Gecko/20100101 Firefox/27.0',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'
        })    
        self.urlGet(
            'https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&target=self&style=16&mibao_css=m_webqq&' + \
            'appid=501004106&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fw.qq.com%2Fproxy.html&' + \
            'f_url=loginerroralert&strong_login=1&login_state=10&t=20131024001'
        )
        self.session.cookies.update(dict(
            RK='OfeLBai4FB', ptcz='ad3bf14f9da2738e09e498bfeb93dd9da7540dea2b7a71acfb97ed4d3da4e277',
            pgv_pvi='911366144', pgv_info='ssid pgv_pvid=1051433466',
            qrsig='hJ9GvNx*oIvLjP5I5dQ19KPa3zwxNI62eALLO*g2JLbKPYsZIRsnbJIxNe74NzQQ'
        ))
        self.getAuthStatus()
        self.session.cookies.pop('qrsig')

    def getAuthStatus(self):
        return self.urlGet(
            url = 'https://ssl.ptlogin2.qq.com/ptqrlogin?webqq_type=10&remember_uin=1&login2qq=1&aid=501004106&' + \
                  'u1=http%3A%2F%2Fw.qq.com%2Fproxy.html%3Flogin2qq%3D1%26webqq_type%3D10&' + \
                  'ptredirect=0&ptlang=2052&daid=164&from_ui=1&pttype=1&dumy=&fp=loginerroralert&' + \
                  'action=0-0-' + repr(random.random() * 900000 + 1000000) + \
                  '&mibao_css=m_webqq&t=undefined&g=1&js_type=0&js_ver=10141&login_sig=&pt_randsalt=0',
            Referer = 'https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&target=self&style=16&mibao_css=m_webqq&' + \
                      'appid=501004106&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fw.qq.com%2Fproxy.html&' + \
                      'f_url=loginerroralert&strong_login=1&login_state=10&t=20131024001'
        ).text
    
    def getQrcode(self):
        QLogger(' 获取二维码')
        if not hasattr(self, 'qrcodePath'):
            self.qrcodePath = 'qrcode.png'
        qrcode = self.urlGet(
            'https://ssl.ptlogin2.qq.com/ptqrshow?appid=501004106&e=0&l=M&s=5&d=72&v=4&t=' + repr(random.random())
        ).content
        with open(self.qrcodePath, 'wb') as f:
            f.write(qrcode)
        thread = threading.Thread(target=show_qr, args=(self.qrcodePath, ))
        thread.setDaemon(True)
        thread.start()
    
    def waitForAuth(self):
        while True:
            time.sleep(3)
            authStatus = self.getAuthStatus()
            if '二维码未失效' in authStatus:
                QLogger('二维码未失效,等待扫描')
            elif '二维码认证中' in authStatus:
                # "ptuiCB('67','0','','0','二维码认证中。(1006641921)', '');\r\n"
                QLogger('二维码已扫描，等待授权')
            elif '二维码已失效' in authStatus:
                # "ptuiCB('65','0','','0','二维码已失效。(4171256442)', '');\r\n"
                QLogger('二维码已失效, 重新获取二维码')
                self.getQrcode()
            elif '登录成功' in authStatus:
                # ptuiCB('0','0','http://ptlogin4.web2.qq.com/check_sig?...','0','登录成功！', 'nickname');\r\n"
                QLogger('已获授权')
                items = authStatus.split(',')
                self.nick = items[-1].split("'")[1]
                self.qqNum = int(self.session.cookies['superuin'][1:])
                self.urlPtwebqq = items[2].strip().strip("'")
                try:
                    os.remove(self.qrcodePath)
                except:
                    pass
                delattr(self, 'qrcodePath')
                break
            else:
                raise Exception('获取二维码扫描状态时出错, html="%s"' % authStatus)
    
    def getPtwebqq(self):
        QLogger('获取ptwebqq')
        self.urlGet(self.urlPtwebqq)
        self.ptwebqq = self.session.cookies['ptwebqq']
    
    def getVfwebqq(self):
        QLogger('获取vfwebqq')
        self.vfwebqq = self.smartRequest(
            url = 'http://s.web2.qq.com/api/getvfwebqq?ptwebqq=%s&clientid=%s&psessionid=&t=%s' % \
                  (self.ptwebqq, self.clientid, repr(random.random())),
            Referer = 'http://s.web2.qq.com/proxy.html?v=20130916001&callback=1&id=1',
            Origin = 'http://s.web2.qq.com'
        )['vfwebqq']
    
    def getUinAndPsessionid(self):
        QLogger('获取uin和psessionid')
        result = self.smartRequest(
            url = 'http://d1.web2.qq.com/channel/login2',
            data = {
                'r': json.dumps({
                    "ptwebqq":self.ptwebqq, "clientid":self.clientid, "psessionid":"", "status":"online"
                })
            },
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2',
            Origin = 'http://d1.web2.qq.com'
        )
        self.uin = result['uin']
        self.psessionid = result['psessionid']
        self.hash = qHash(self.uin, self.ptwebqq)

    def testLogin(self):
        # 请求一下 get_online_buddies 页面，似乎可以避免103错误。若请求无错误发生，则表明登录成功
        self.smartRequest(
            url = 'http://d1.web2.qq.com/channel/get_online_buddies2?vfwebqq=%s&clientid=%d&psessionid=%s&t=%s' % \
                  (self.vfwebqq, self.clientid, self.psessionid, repr(random.random())),
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2',
            Origin = 'http://d1.web2.qq.com',
            repeatOnDeny = 0
        )

    def fetchBuddies(self):
        QLogger('获取好友列表')
        result = self.smartRequest(
            url = 'http://s.web2.qq.com/api/get_user_friends2',
            data = {'r': json.dumps({"vfwebqq":self.vfwebqq, "hash":self.hash})},
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        self.buddies = {}

        for info in result['info']:
            uin = info['uin']
            name = info['nick']
            qq = self.smartRequest(
                url = 'http://s.web2.qq.com/api/get_friend_uin2?tuin=%d&type=1&vfwebqq=%s&t=0.1' % \
                      (uin, self.vfwebqq),
                Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
            )['account']
            self.buddies[uin] = [qq, name]
        QLogger(str(self.buddies))
        QLogger('获取朋友列表成功，共 %d 个朋友' % len(self.buddies))

    def fetchGroups(self):
        QLogger('获取群列表')
        result = self.smartRequest(
            url = 'http://s.web2.qq.com/api/get_group_name_list_mask2',
            data = {'r': json.dumps({"vfwebqq":self.vfwebqq, "hash":self.hash})},
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        ss, self.groups, self.groupsDictU, self.groupsDictQ = [], [], {}, {}
        res = result['gnamelist']
        self.groups = {i['gid']: i['name'] for i in res}
        self.groupStr = '群列表:\n' + str(self.groups)
        QLogger('获取群列表成功，共 %d 个群' % len(self.groups))

    def fetchDiscusses(self):
        QLogger('获取讨论组列表')
        result = self.smartRequest(
            url = 'http://s.web2.qq.com/api/get_discus_list?clientid=%s&psessionid=%s&vfwebqq=%s&t=%s' % \
                  (self.clientid, self.psessionid, self.vfwebqq, repr(random.random())),
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        ss, self.discusses, self.discussesDict = [], [], {}
        for info in result['dnamelist']:
            uin = info['did']
            name = info['name']
            discuss = dict(uin=uin, name=name)
            self.discusses.append(discuss)
            self.discussesDict[uin] = discuss
            s = '%s, uin%d' % (name, uin)
            ss.append(s)
            QLogger('讨论组： ' + s)
        self.discussStr = '讨论组列表:\n' + '\n'.join(ss)
        QLogger('获取讨论组，共 %d 个' % len(self.discusses))
    
    def refetch(self):
        self.fetchBuddies()
        self.fetchGroups()
        #self.fetchDiscusses()
        self.nick = self.fetchBuddyDetailInfo(self.uin)['nick']
    
    def fetchBuddyDetailInfo(self, uin):
        return self.smartRequest(
            url = 'http://s.web2.qq.com/api/get_friend_info2?tuin={uin}'.format(uin=uin) + \
                  '&vfwebqq={vfwebqq}&clientid=53999199&psessionid={psessionid}&t=0.1'.format(**self.__dict__),
            Referer = 'http://s.web2.qq.com/proxy.html?v=20130916001&callback=1&id=1'
        )

    def poll(self):
        result = self.smartRequest(
            url = 'http://d1.web2.qq.com/channel/poll2',
            data = {
                'r': json.dumps({
                    "ptwebqq":self.ptwebqq, "clientid":self.clientid,
                    "psessionid":self.psessionid, "key":""
                })
            },
            sessionObj = self.pollSession,
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        if 'errmsg' in result:
            return None
        else:
            result = result[0]
            msgType = {'message':'buddy', 'group_message':'group', 'discu_message':'discuss'}[result['poll_type']]
            from_uin = result['value']['from_uin']
            buddy_uin = result['value'].get('send_uin', from_uin)

            msg = ''.join([str(m) for m in result['value']['content'][1:]])
            try:
                face = result['value']['content'][2][2]
            except :
                face=0
            pollResult = msgType, from_uin, buddy_uin, msg, face
            if msgType == 'buddy':
                try:
                    name =self.buddies[from_uin]
                except KeyError as error:
                    name = "未知qq"
                print('来自 %s(%s) 的消息: "%s"' % (name[1], name[0], msg))
            else:
                print('来自群: %s (%d) 的消息: %s ' % (self.groups[pollResult[1]], pollResult[2], pollResult[3]))
                if not self.groups[pollResult[1]] in config.groups:
                    print('不在qq')
                    return None
        return pollResult
    
    def send(self, msgType, to_uin, msg, face):
        while msg:
            front, msg = utf8Partition(msg, 600)
            self._send(msgType, to_uin, front, face)

    def _send(self, msgType, to_uin, msg, face):
        self.msgId += 1        
        if self.msgId % 10 == 0:
            QLogger('已连续发送10条消息暂停5秒，请等待...')
            time.sleep(10)
        else:
            time.sleep(random.randint(3, 5))
        sendUrl = {
            'buddy': 'http://d1.web2.qq.com/channel/send_buddy_msg2',
            'group': 'http://d1.web2.qq.com/channel/send_qun_msg2',
            'discuss': 'http://d1.web2.qq.com/channel/send_discu_msg2'
        }
        sendTag = {"buddy": "to", "group": "group_uin", "discuss": "did"}
        self.smartRequest(
                url=sendUrl[msgType],
                data={
                    'r': json.dumps({
                    sendTag[msgType]: to_uin,
                    "content":
                        json.dumps([msg, ["font", {"name": "宋体", "size": 10, "style": [0, 0, 0], "color": "000000"}]]),
                        "face":face,
                        "clientid": self.clientid,
                    "msg_id": self.msgId,
                    "psessionid": self.psessionid})
                },
            Referer='http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )


    def urlGet(self, url, **kw):
        time.sleep(0.2)
        self.session.headers.update(kw)
        return self.session.get(url)

    def smartRequest(self, url, data=None, repeatOnDeny=2, sessionObj=None, **kw):
        time.sleep(0.1)
        session = sessionObj or self.session
        i, j = 0, 0
        while True:
            html = ''
            session.headers.update(**kw)
            try:
                if data is None:
                    html = session.get(url).text
                else:
                    html = session.post(url, data=data).text
                result = json.loads(html)
            except (requests.ConnectionError, ValueError):
                i += 1
                errorInfo = '网络错误或url地址错误'
            else:
                retcode = result.get('retcode', result.get('errCode', -1))
                if retcode in (0, 1202, 100003):
                    return result.get('result', result)
                else:
                    j += 1
                    errorInfo = '请求被拒绝错误'
            errMsg = '第%d次请求“%s”时出现“%s”，html=%s' % (i+j, url, errorInfo, html)

            # 出现网络错误可以多试几次；若网络没问题，但 retcode 有误，一般连续 3 次都出错就没必要再试了
            if i <= 5 and j <= repeatOnDeny:
                QLogger(errMsg + '！等待重试。')
                time.sleep(3)
            else:
                QLogger(errMsg + '！停止重试')
                raise RequestError

    def Run(self):
        self.msgQueue = queue.Queue()
        self.stopped = False

        pullThread = threading.Thread(target=self.pullForever)
        pullThread.setDaemon(True)
        pullThread.start()
        
        while True:
            try:
                pullResult = self.msgQueue.get()
                if pullResult is None:
                    continue
                self.onPollComplete(*pullResult)
            except KeyboardInterrupt:
                self.stopped = True
                break
            except RequestError:
                QLogger('向 QQ 服务器请求数据时出错')
                continue
            except TypeError as error:
                QLogger(error)
                continue
        
        if self.stopped:
            QLogger("QQBot正常退出")
        else:
            QLogger('QQBot异常退出')

    def pullForever(self):
        while not self.stopped:
            try:
                pullResult = self.poll()
                self.msgQueue.put(pullResult)
            except KeyboardInterrupt:
                self.stopped = True
                self.msgQueue.put(None)
            except RequestError:
                QLogger('向 QQ 服务器请求数据时出错')
                self.msgQueue.put(None)
                break

    def onPollComplete(self, msgType, from_uin, buddy_uin, message, face):
        from roboot import getMsg
        if message:
            msg = getMsg(message)
            self.send(msgType, from_uin, msg, face)
        try:
            name =self.buddies[from_uin]
        except IndexError as error:
            return
        except TypeError as error:
            return
        except KeyError as error:
            return
        print('向%s(%s) 回复消息(%s)成功' % (name[1], name[0], msg))

def qHash(x, K):
    N = [0] * 4
    for T in range(len(K)):
        N[T%4] ^= ord(K[T])

    U = "ECOK"
    V = [0] * 4    
    V[0] = ((x >> 24) & 255) ^ ord(U[0])
    V[1] = ((x >> 16) & 255) ^ ord(U[1])
    V[2] = ((x >>  8) & 255) ^ ord(U[2])
    V[3] = ((x >>  0) & 255) ^ ord(U[3])

    U1 = [0] * 8

    for T in range(8):
        U1[T] = N[T >> 1] if T % 2 == 0 else V[T >> 1]

    N1 = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A", "B", "C", "D", "E", "F"]
    V1 = ""
    for aU1 in U1:
        V1 += N1[((aU1 >> 4) & 15)]
        V1 += N1[((aU1 >> 0) & 15)]

    return V1

def utf8Partition(msg, n):
    if n >= len(msg):
        return msg, ''
    else:
        while n > 0 and ord(msg[n]) >> 6 == 2:
            n -= 1
        return msg[:n], msg[n:]
def show_qr(path):
    from tkinter import Tk ,Label
    try:
        from PIL import ImageTk, Image
    except ImportError:
        raise SystemError('缺少PIL模块, 可使用sudo pip install PIL尝试安装')
    root = Tk()
    img = ImageTk.PhotoImage(
		Image.open(path)
	)
    panel = Label(root, image=img)
    panel.pack(side="bottom", fill="both", expand="yes")
    root.mainloop()
def main():
    bot = QQBot()
    bot.Login()
    bot.Run()

if __name__ == '__main__':
    main()
