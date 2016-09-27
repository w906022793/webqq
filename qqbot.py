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

# �� windows consoler �£� ���� print "����" ���������
# ��ʹ�ã� utf8_stdout.write("����\n")
# �൱�ڣ� sys.stdout.write("����\n".decode('utf8').encode(sys.stdout.encoding))
if codingEqual('utf8', sys.stdout.encoding):
    utf8_stdout = sys.stdout
else:
    utf8_stdout = CodingWrappedWriter('utf8', sys.stdout)

def QLogger(msg):
    print(str(msg))



try:
    TmpDir = os.path.join(os.path.expanduser('~'), '.qqbot-tmp')
    if not os.path.exists(TmpDir):
        os.mkdir(TmpDir)
    tmpfile = os.path.join(TmpDir, 'tmptest%f' % random.random())
    with open(tmpfile, 'w') as f:
        f.write('test')
    os.remove(tmpfile)
except:
    TmpDir = os.getcwd()

class RequestError(Exception):
    pass

class QQBot:
    def Login(self, qqNum=None):
        if qqNum is None and len(sys.argv) == 2 and sys.argv[1].isdigit():
            qqNum = int(sys.argv[1])

        if qqNum is None:
            QLogger('��¼��ʽ���ֶ���¼')
            self.manualLogin()
        else:
            try:
                QLogger('��¼��ʽ���Զ���¼')
                self.autoLogin(qqNum)
            except Exception as e:
                if not isinstance(e, RequestError):
                    QLogger('', exc_info=True)
                QLogger('�Զ���¼ʧ�ܣ������ֶ���¼')
                self.manualLogin()

        QLogger('��¼�ɹ�����¼�˺ţ�%s (%d)' % (self.nick, self.qqNum))

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

    def autoLogin(self, qqNum):
        self.loadSessionInfo(qqNum)
        self.testLogin()

    def dumpSessionInfo(self):
        picklePath = os.path.join('log%d.log' %  self.qqNum)
        try:
            with open(picklePath, 'wb') as f:
                pickle.dump(self.__dict__, f)
        except:
            QLogger('', exc_info=True)
            QLogger('�����¼ Session info ʧ��')
        else:
            QLogger('��¼��Ϣ�ѱ�')
        self.pollSession = pickle.loads(pickle.dumps(self.session))

    def loadSessionInfo(self, qqNum):
        picklePath = os.path.join(TmpDir, '%s-%d.pickle' % (QQBotVersion[:-2], qqNum))
        with open(picklePath, 'rb') as f:
            self.__dict__ = pickle.load(f)
            QLogger('�ɹ����ļ� file://%s �лָ���¼��Ϣ' % picklePath)
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
        QLogger(' ��ȡ��ά��')
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
            if '��ά��δʧЧ' in authStatus:
                QLogger('��ά��δʧЧ,�ȴ�ɨ��')
            elif '��ά����֤��' in authStatus:
                # "ptuiCB('67','0','','0','��ά����֤�С�(1006641921)', '');\r\n"
                QLogger('��ά����ɨ�裬�ȴ���Ȩ')
            elif '��ά����ʧЧ' in authStatus:
                # "ptuiCB('65','0','','0','��ά����ʧЧ��(4171256442)', '');\r\n"
                QLogger('��ά����ʧЧ, ���»�ȡ��ά��')
                self.getQrcode()
            elif '��¼�ɹ�' in authStatus:
                # ptuiCB('0','0','http://ptlogin4.web2.qq.com/check_sig?...','0','��¼�ɹ���', 'nickname');\r\n"
                QLogger('�ѻ���Ȩ')
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
                raise Exception('��ȡ��ά��ɨ��״̬ʱ����, html="%s"' % authStatus)
    
    def getPtwebqq(self):
        QLogger('��ȡptwebqq')
        self.urlGet(self.urlPtwebqq)
        self.ptwebqq = self.session.cookies['ptwebqq']
    
    def getVfwebqq(self):
        QLogger('��ȡvfwebqq')
        self.vfwebqq = self.smartRequest(
            url = 'http://s.web2.qq.com/api/getvfwebqq?ptwebqq=%s&clientid=%s&psessionid=&t=%s' % \
                  (self.ptwebqq, self.clientid, repr(random.random())),
            Referer = 'http://s.web2.qq.com/proxy.html?v=20130916001&callback=1&id=1',
            Origin = 'http://s.web2.qq.com'
        )['vfwebqq']
    
    def getUinAndPsessionid(self):
        QLogger('��ȡuin��psessionid')
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
        # ����һ�� get_online_buddies ҳ�棬�ƺ����Ա���103�����������޴��������������¼�ɹ�
        self.smartRequest(
            url = 'http://d1.web2.qq.com/channel/get_online_buddies2?vfwebqq=%s&clientid=%d&psessionid=%s&t=%s' % \
                  (self.vfwebqq, self.clientid, self.psessionid, repr(random.random())),
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2',
            Origin = 'http://d1.web2.qq.com',
            repeatOnDeny = 0
        )

    def fetchBuddies(self):
        QLogger('��ȡ�����б�')
        result = self.smartRequest(
            url = 'http://s.web2.qq.com/api/get_user_friends2',
            data = {'r': json.dumps({"vfwebqq":self.vfwebqq, "hash":self.hash})},
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        self.buddies = {}
        self.buddiess = {}

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
        QLogger('��ȡ�����б�ɹ����� %d ������' % len(self.buddies))

    def fetchGroups(self):
        QLogger('��ȡȺ�б�')
        result = self.smartRequest(
            url = 'http://s.web2.qq.com/api/get_group_name_list_mask2',
            data = {'r': json.dumps({"vfwebqq":self.vfwebqq, "hash":self.hash})},
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        ss, self.groups, self.groupsDictU, self.groupsDictQ = [], [], {}, {}
        res = result['gnamelist']
        self.groups = {i['gid']: i['name'] for i in res}
        self.groupStr = 'Ⱥ�б�:\n' + str(self.groups)
        QLogger('��ȡȺ�б�ɹ����� %d ������' % len(self.groups))

    def fetchDiscusses(self):
        QLogger('��ȡ�������б�')
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
            QLogger('�����飺 ' + s)
        self.discussStr = '�������б�:\n' + '\n'.join(ss)
        QLogger('��ȡ�������б�ɹ����� %d ��������' % len(self.discusses))
    
    def refetch(self):
        #self.fetchBuddies()
        self.fetchGroups()
        self.fetchDiscusses()
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
            pollResult = ('', 0, 0, '')  # ����Ϣ
        else:
            result = result[0]
            msgType = {'message':'buddy', 'group_message':'group', 'discu_message':'discuss'}[result['poll_type']]
            from_uin = result['value']['from_uin']
            buddy_uin = result['value'].get('send_uin', from_uin)
            msg = ''.join(
                [m for m in result['value']['content'][1:]]
            )
            pollResult = msgType, from_uin, buddy_uin, msg
            if msgType == 'buddy':
                try:
                    name =self.buddies[from_uin]
                except:
                    name = "δ֪qq"
                print('���� %s(%s) ����Ϣ: "%s"' % (name[1], name[0], msg))
            else:
                print('����Ⱥ: %s (%d) ����Ϣ: %s ' % (self.groups[pollResult[1]], pollResult[2], pollResult[3]))
        return pollResult
    
    def send(self, msgType, to_uin, msg):
        while msg:
            front, msg = utf8Partition(msg, 600)
            self._send(msgType, to_uin, front)

    def _send(self, msgType, to_uin, msg):
        self.msgId += 1        
        if self.msgId % 10 == 0:
            QLogger('����������10����Ϣ��ǿ�� sleep 10�룬��ȴ�...')
            time.sleep(10)
        else:
            time.sleep(random.randint(3,5))
        sendUrl = {
            'buddy': 'http://d1.web2.qq.com/channel/send_buddy_msg2',
            'group': 'http://d1.web2.qq.com/channel/send_qun_msg2',
            'discuss': 'http://d1.web2.qq.com/channel/send_discu_msg2'
        }
        sendTag = {"buddy":"to", "group":"group_uin", "discuss":"did"}
        self.smartRequest(
            url = sendUrl[msgType], 
            data = {
                'r': json.dumps({
                    sendTag[msgType]: to_uin,
                    "content": json.dumps([
                        msg,
                        ["font", {"name": "����", "size": 10, "style": [0,0,0], "color": "000000"}]
                    ]),
                    "face": 522,
                    "clientid": self.clientid,
                    "msg_id": self.msgId,
                    "psessionid": self.psessionid
                })
            },
            Referer = 'http://d1.web2.qq.com/proxy.html?v=20151105001&callback=1&id=2'
        )
        try:
            name =self.buddies[to_uin]
        except :
            name ='δ֪qq'
            return None
        print('��%s(%s) �ظ���Ϣ�ɹ�' % (name[1], name[0]))

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
                errorInfo = '��������url��ַ����'
            else:
                retcode = result.get('retcode', result.get('errCode', -1))
                if retcode in (0, 1202, 100003):
                    return result.get('result', result)
                else:
                    j += 1
                    errorInfo = '���󱻾ܾ�����'
            errMsg = '��%d������%s��ʱ���֡�%s����html=%s' % (i+j, url, errorInfo, html)

            # �������������Զ��Լ��Σ�������û���⣬�� retcode ����һ������ 3 �ζ������û��Ҫ������
            if i <= 5 and j <= repeatOnDeny:
                QLogger(errMsg + '���ȴ����ԡ�')
                time.sleep(3)
            else:
                QLogger(errMsg + '��ֹͣ����')
                raise RequestError

    def Run(self):
        self.msgQueue = queue.Queue()
        self.stopped = False

        pullThread = threading.Thread(target=self.pullForever)
        pullThread.setDaemon(True)
        pullThread.start()
        
        while not self.stopped:
            try:
                pullResult = self.msgQueue.get()
                if pullResult is None:
                    break
                self.onPollComplete(*pullResult)
            except KeyboardInterrupt:
                self.stopped = True
            except RequestError:
                QLogger('�� QQ ��������������ʱ����')
                break
            except:
                QLogger('����δ֪�����Ѻ���')
        
        if self.stopped:
            QLogger("QQBot�����˳�")
        else:
            QLogger('QQBot�쳣�˳�')

    def pullForever(self):
        while not self.stopped:
            try:
                pullResult = self.poll()
                self.msgQueue.put(pullResult)
            except KeyboardInterrupt:
                self.stopped = True
                self.msgQueue.put(None)
            except RequestError:
                QLogger('�� QQ ��������������ʱ����')
                self.msgQueue.put(None)
                break
            except:
                QLogger('', exc_info=True)
                QLogger(' poll ���������Ѻ���')

    # overload this method to build your own QQ-bot.    
    def onPollComplete(self, msgType, from_uin, buddy_uin, message):
        if message:
            self.send(msgType, from_uin, message)

# $filename must be an utf8 string

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
        # All utf8 characters start with '0xxx-xxxx' or '11xx-xxxx'
        while n > 0 and ord(msg[n]) >> 6 == 2:
            n -= 1
        return msg[:n], msg[n:]
def show_qr(path):
    from tkinter import Tk ,Label
    try:
        from PIL import ImageTk, Image
    except ImportError:
        raise SystemError('ȱ��PILģ��, ��ʹ��sudo pip install PIL���԰�װ')
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
