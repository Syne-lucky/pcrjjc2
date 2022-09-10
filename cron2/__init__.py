from json import load, dump, dumps, loads
from nonebot import get_bot, on_command
from nonebot import on_notice, NoticeSession
from hoshino import priv
from hoshino.typing import NoticeSession
from .pcrclient import pcrclient, ApiException, bsdkclient
from asyncio import Lock
from os.path import dirname, join, exists
from traceback import format_exc
from .safeservice import SafeService
from hoshino.aiorequests import post, get
import asyncio

ordd = 2

parpath = dirname(dirname(__file__))
curpath = dirname(__file__)

cache = {}
client = None
lck = Lock()



captcha_lck = Lock()

with open(join(curpath, 'account.json')) as fp:
    acinfo = load(fp)

bot = get_bot()
validate = None
validating = False
otto = True
acfirst = False


captcha_cnt = 0
async def captchaVerifier(*args):
    global otto
    if len(args) == 0:
        return otto
    global captcha_cnt
    if len(args) == 1 and type(args[0]) == int:
        captcha_cnt = args[0]
        return captcha_cnt

    global acfirst, validating
    global binds, lck, validate, captcha_lck
    if not acfirst:
        await captcha_lck.acquire()
        acfirst = True

    validating = True
    if otto == False:
        gt = args[0]
        challenge = args[1]
        userid = args[2]
        url = f"https://help.tencentbot.top/geetest/?captcha_type=1&challenge={challenge}&gt={gt}&userid={userid}&gs=1"
        await bot.send_private_msg(
            user_id=acinfo['admin'],
            message=f'pcr账号登录需要验证码，请完成以下链接中的验证内容后将第1个方框的内容点击复制，并加上"validate{ordd} "前缀发送给机器人完成验证\n验证链接：{url}\n示例：validate{ordd} 123456789\n您也可以发送 validate{ordd} auto 命令bot自动过验证码')
        await captcha_lck.acquire()
        validating = False
        return validate

    while captcha_cnt < 5:
        captcha_cnt += 1
        try:
            print(f'测试新版自动过码中，当前尝试第{captcha_cnt}次。')

            await asyncio.sleep(1)
            uuid = loads(await (await get(url="https://pcrd.tencentbot.top/geetest")).content)["uuid"]
            print(f'uuid={uuid}')

            ccnt = 0
            while ccnt < 3:
                ccnt += 1
                await asyncio.sleep(5)
                res = await (await get(url=f"https://pcrd.tencentbot.top/check/{uuid}")).content
                res = loads(res)
                if "queue_num" in res:
                    nu = res["queue_num"]
                    print(f"queue_num={nu}")
                    tim = min(int(nu), 3) * 5
                    print(f"sleep={tim}")
                    await asyncio.sleep(tim)
                else:
                    info = res["info"]
                    if info in ["fail", "url invalid"]:
                        break
                    elif info == "in running":
                        await asyncio.sleep(5)
                    else:
                        print(f'info={info}')
                        validating = False
                        return info
        except:
            pass

    if captcha_cnt >= 5:
        otto = False
        await bot.send_private_msg(user_id=acinfo['admin'], message=f'thread{ordd}: 自动过码多次尝试失败，可能为服务器错误，自动切换为手动。\n确实服务器无误后，可发送 validate{ordd} auto重新触发自动过码。')
        await bot.send_private_msg(user_id=acinfo['admin'], message=f'thread{ordd}: Changed to manual')
        validating = False
        return "manual"

    await errlogger("captchaVerifier: uncaught exception")
    validating = False
    return False



async def errlogger(msg):
    if msg == 'geetest or captcha succeed':
        return
    await bot.send_private_msg(user_id=acinfo['admin'], message=f'thread{ordd}: {msg}')


bclient = bsdkclient(acinfo, captchaVerifier, errlogger)
client = pcrclient(bclient)

qlck2 = Lock()


async def query2(id: int):
    if validating:
        raise ApiException('账号被风控，请联系管理员输入验证码并重新登录', -1)
    async with qlck2:
        while client.shouldLogin:
            await client.login()
        res = (await client.callapi('/profile/get_profile', {'target_viewer_id': id}))['user_info']
        return res


def save_binds():
    with open(config, 'w') as fp:
        dump(root, fp, indent=4)


@on_command(f'validate{ordd}')
async def validate(session):
    global binds, lck, validate, validating, captcha_lck, otto
    if session.ctx['user_id'] == acinfo['admin']:
        validate = session.ctx['message'].extract_plain_text().replace(f"validate{ordd}", "").strip()
        if validate == "manual":
            otto = False
            await bot.send_private_msg(user_id=acinfo['admin'], message=f'thread{ordd}: Changed to manual')
        elif validate == "auto":
            otto = True
            await bot.send_private_msg(user_id=acinfo['admin'], message=f'thread{ordd}: Changed to auto')
        try:
            captcha_lck.release()
        except:
            pass

