import requests as req
import json
import unicodedata as uni
def getMsg(question):
    param = {'question': question,
             'limit': 3,
             'api_secret': 'gf6ekgq32hin',
            'api_key': '2c0b56474d0368c0b12b436699f33508',
            'type': 'json'
            }
    header = {'UserAgent': 'Mozilla/5.0 (Windows NT 6.1) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/53.0.2785.116 Safari/537.36'
             }
    res = req.post('http://i.itpk.cn/api.php', data=param, headers=header)
    rettype = ['笑话',
            '观音灵签',
            '月老灵签',
            '财神爷灵签']
    if question in rettype:
        text = json.loads(res.text.encode('utf8')[3:].decode('utf8'))
        return '\n'.join([i for i in text.values()])
    return res.text
getMsg('@qq516742171')