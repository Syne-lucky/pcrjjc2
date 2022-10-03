from hoshino import Service, priv
from .text2img import image_draw
from hoshino.typing import NoticeSession, CQHttpError
from json import load, dump, dumps, loads
from os.path import dirname, join, exists
import asyncio
from asyncio import Lock
from .safeservice import SafeService
from copy import deepcopy
import re
import time
from .cron0.__init__ import query0
from .cron1.__init__ import query1
from .cron2.__init__ import query2
from nonebot import on_command, get_bot
bot_list=[2500831574]           #填bot的qq号
bot_name=['小真步']            #填bot的昵称
adm_list = [3588116504]         #填管理员qq，管理员可以删别人绑定。【请确保第一个管理员qq和bot是好友！】
friendList = []
pcrid_list = []
pcrid_list_cron1 = []
pcrid_list_cron2 = []
bind_change = False
bot = get_bot()
today_notice = 0
yesterday_notice = 0

sv_help='''\t\t\t\t【竞技场帮助】
可以添加的订阅：[jjc][pjjc][排名上升][上线提醒]
#上线提醒仅在14：30~15：00播报
#排名上升提醒对jjc和pjjc同时生效
#每个QQ号至多添加8个uid的订阅
#默认开启jjc、pjjc，关闭排名上升、上线提醒
#手动查询时，返回昵称、jjc/pjjc排名、场次、
jjc/pjjc当天排名上升次数、最后登录时间。
#支持群聊/私聊使用。建议群聊使用，大量私聊号会寄。
------------------------------------------------
命令格式：
#只绑定1个uid时，绑定的序号可以不填。
[绑定的序号]1~8对应绑定的第1~8个uid，序号0表示全部
1）竞技场绑定[uid][昵称]（昵称可省略）
2）删除竞技场绑定[绑定的序号]（这里序号不可省略）
3）开启/关闭竞技场推送（不会删除绑定）
4）清空竞技场绑定
5）竞技场查询[uid]（uid可省略）
6）竞技场订阅状态
7）竞技场修改昵称 [绑定的序号] [新昵称] 
8）竞技场设置[开启/关闭][订阅内容][绑定的序号]
9）竞技场/击剑记录[绑定的序号]（序号可省略）
10）竞技场设置1110[绑定的序号]
#0表示关闭，1表示开启
#4个数字依次代表jjc、pjjc、排名上升、上线提醒
#例如：“竞技场设置1011 2” “竞技场设置1110 0”
11）换私聊推送（限私聊发送，需要好友）
12）在本群推送（限群聊发送，无需好友）
'''

sv_help_adm='''------------------------------------------------
管理员帮助：
1）pcrjjc负载查询
2）pcrjjc删除绑定[qq号]
3）pcrjjc关闭私聊推送
'''

sv = SafeService('竞技场推送', help_=sv_help, bundle='pcr查询', visible=False)

def ban(session):
    ban_group = [114514]    #禁用的群
    ban_qq = [114514]       #禁用的qq
    if session.ctx['user_id'] in ban_qq or session.ctx['message_type'] == 'group' and session.ctx['group_id'] in ban_group:
        return True
    else:
        return False
    

@on_command('jjchelp', aliases=('竞技场帮助','击剑帮助'), only_to_me=False)
async def jjc_help(session):
    global adm_list
    if session.ctx['user_id'] not in adm_list:
        pic = image_draw(sv_help)
    else:
        pic = image_draw(sv_help+sv_help_adm)
    await session.send(f'[CQ:image,file={pic}]') 

parpath = dirname(__file__)
curpath = dirname(__file__)
config = join(parpath, 'binds.json')
root = {'arena_bind': {}}

cache = {}
jjc_log = {}
client = None
lck = Lock()
lck_friendList = Lock()

if exists(config):
    with open(config) as fp:
        root = load(fp)
        
bind_cache = root['arena_bind']
captcha_lck = Lock()    



def save_binds():
    with open(config, 'w') as fp:
        dump(root, fp, ensure_ascii=False, indent=4)
        
async def sendNotice(new:int, old:int, pcrid:int, noticeType:int):   #noticeType：1:jjc排名变动   2:pjjc排名变动  3:登录时间刷新
    global bind_cache
    global bot_list
    global timeStamp, jjc_log, today_notice
    print('sendNotice   sendNotice    sendNotice')
    bot = get_bot()
    if noticeType == 3:
        change = '上线了！'
    else:
        jjc_log_new = (timeStamp, noticeType, new, old)
        if pcrid in jjc_log:
            if len(jjc_log[pcrid]) >= 60:
                del jjc_log[pcrid][0]
            jjc_log[pcrid].append(jjc_log_new)
        else:
            jjc_log_new_tmp = []
            jjc_log_new_tmp.append(jjc_log_new)
            jjc_log[pcrid] = jjc_log_new_tmp
        if noticeType == 1:
            change = '\njjc: '
        elif noticeType == 2:
            change = '\npjjc: '
        if new < old:
            change += f'''{old}->{new} [▲{old-new}]'''
        else:
            change += f'''{old}->{new} [▽{new-old}]'''
#-----------------------------------------------------------------  
    for qid in bind_cache:
        if bind_cache[qid]["notice_on"] == False:
            continue
        for i in range(len(bind_cache[qid]["pcrid"])):
            if bind_cache[qid]["pcrid"][i] == pcrid:
                msg = ''
                tmp = bind_cache[qid]["noticeType"][i]
                name = bind_cache[qid]["pcrName"][i]
                #bot_id = (tmp//10000)-1
                bot_id = 0
                jjcNotice = True if tmp//1000 else False
                pjjcNotice = True if (tmp%1000)//100 else False
                riseNotice = True if (tmp%100)//10 else False
                onlineNotice = True if tmp%10 else False
                if (((noticeType == 1 and jjcNotice) or (noticeType == 2 and pjjcNotice)) and (riseNotice or (new>old))) or (noticeType ==3 and onlineNotice):
                    msg = name + change
                    today_notice += 1
                    if bind_cache[qid]["private"] == True:
                        try:
                            await bot.send_private_msg(user_id=int(qid), message=msg)
                        except:
                            bind_cache[qid][notice_on] = False
                            coffee = hoshino.config.SUPERUSERS[0]
                            await bot.send_private_msg(self_id=bot_list[bot_id], user_id=coffee, message='jjc私聊推送发送失败！\n user_id:'+qid+'\n' + msg)
                    else:
                        try:
                            gid = bind_cache[qid]["gid"]
                            msg += '[CQ:at,qq=' + qid + ']'
                            await bot.send_group_msg(group_id=int(gid), message=msg)
                        except Exception as e:
                            sv.logger.info(f'bot账号不在群{gid}中，将忽略该消息')
                break
               
@on_command('jjc_log_query', patterns=('^(击剑|竞技场)记录 ?\d?$'), only_to_me=False)              
async def jjc_log_query(session):
    global jjc_log, bind_cache
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    msg = str(session.ctx['message'])
    print(msg)
    name = session.ctx['sender']['nickname']
    print_all = False
    too_long = False
    if qid not in bind_cache:
        reply = '您还没有绑定竞技场！'
        await session.send(reply)
        return  
    pcrid_num = len(bind_cache[qid]['pcrid'])
    try:
        ret = re.match(r'^ ?(?:击剑|竞技场)记录 ?(\d)?$',msg)
        pcrid_id_input = int(ret.group(1))
    except:
        if pcrid_num == 1:
            pcrid_id_input = 1
        else:
            print_all = True
    if print_all == False:
        if pcrid_id_input == 0 or pcrid_id_input > pcrid_num:
            reply = '序号超出范围，请检查您绑定的竞技场列表'
            await session.send(reply)
            return
    if print_all:
        msg = f'''\t\t\t\t【{name}的击剑记录】\n'''
        jjc_log_cache = []
        len_pcrName = []
        for pcrid_id in range(pcrid_num):       #复制相关的log，并排序
            pcrid = bind_cache[qid]['pcrid'][pcrid_id]
            pcrName = bind_cache[qid]['pcrName'][pcrid_id]
            if pcrid in jjc_log:                    #计算名字长度
                width = 0
                for c in pcrName:
                    if len(c.encode('utf8')) == 3:  # 中文
                        width += 2
                    else:
                        width += 1
                len_pcrName.append(width)
                for log in jjc_log[pcrid]:
                    log_tmp = list(log)
                    log_tmp.append(pcrid_id)
                    jjc_log_cache.append(log_tmp)
            else:
                len_pcrName.append(0)           #没有击剑记录的uid名字长度写0
        longest_pcrName = max(len_pcrName)
        print(longest_pcrName)
        for i in range(len(len_pcrName)):
            len_pcrName[i] = longest_pcrName - len_pcrName[i]       #改成补空格的数量
        print(jjc_log_cache)
        jjc_log_cache_num = len(jjc_log_cache)
        if jjc_log_cache_num:
            jjc_log_cache.sort(key = lambda x:x[0], reverse=True)        
            if jjc_log_cache_num > 100:
                too_long = True
                jjc_log_cache_num = 100
            for i in range(jjc_log_cache_num):
                timeStamp = jjc_log_cache[i][0]
                timeArray = time.localtime(timeStamp)
                otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
                pcrid_id = jjc_log_cache[i][4]
                pcrName = bind_cache[qid]['pcrName'][pcrid_id]
                space = ' '*len_pcrName[pcrid_id]
                jjc_pjjc = 'jjc ' if jjc_log_cache[i][1] == 1 else 'pjjc'
                new = jjc_log_cache[i][2]
                old = jjc_log_cache[i][3]
                if new < old:
                    change = f'''{old}->{new} [▲{old-new}]'''
                else:
                    change = f'''{old}->{new} [▽{new-old}]'''
                msg += f'''{otherStyleTime} {pcrName}{space} {jjc_pjjc}：{change}\n'''
            if too_long:
                msg += '###由于您订阅了太多账号，记录显示不下嘞~\n###如有需要，可以在查询时加上序号。'
        else:
            msg += '没有击剑记录！'
    else:
        msg = f'''\t\t\t【{name}的击剑记录】\n'''
        pcrid_id = pcrid_id_input-1
        pcrid = bind_cache[qid]['pcrid'][pcrid_id]
        pcrName = bind_cache[qid]['pcrName'][pcrid_id]
        msg += f'''{pcrName}（{pcrid}）\n'''
        if pcrid in jjc_log:
            jjc_log_num = len(jjc_log[pcrid])
            for i in range(jjc_log_num):
                n = jjc_log_num-1-i         #倒序输出，是最近的log在上面
                timeStamp = jjc_log[pcrid][n][0]
                timeArray = time.localtime(timeStamp)
                otherStyleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
                jjc_pjjc = 'jjc' if jjc_log[pcrid][n][1] == 1 else 'pjjc'
                new = jjc_log[pcrid][n][2]
                old = jjc_log[pcrid][n][3]
                if new < old:
                    change = f'''{old}->{new} [▲{old-new}]'''
                else:
                    change = f'''{old}->{new} [▽{new-old}]'''
                msg += f'''{otherStyleTime} {jjc_pjjc}：{change}\n'''
        else:
            msg += '没有击剑记录！'
    pic = image_draw(msg)
    await session.send(f'[CQ:image,file={pic}]')
    
    
                
#notice_cache = []      #令牌桶限速，超出部分缓存。这部分还没写
@on_command('jjc_set', patterns=('^竞技场设置'), only_to_me=False)
async def set_noticeType(session):
    global bind_cache, lck
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    msg = str(session.ctx['message'])
    print(session.ctx)
    print(msg)
    error = False  #输入错误时的回复
    try:
        ret = re.match(r'^ ?竞技场设置 ?(开启|关闭) ?(jjc|pjjc|排名上升|上线提醒) ?(\d)?$', msg)       
        turn_on = True if str(ret.group(1))=='开启'else False
        change = ret.group(2)
        try:
            pcrid_id = int(ret.group(3))
        except:
            pcrid_id = None
        quick_set = False
    except:
        try:
            ret = re.match(r'^ ?竞技场设置 ?([01]{4}) ?(\d)?$',msg)
            change = ret.group(1)       #change: str
            try:
                pcrid_id = int(ret.group(2))
            except:
                pcrid_id = None
            quick_set = True
        except:
            error = True
            reply = '输入的格式不太对呢~'
    
    async with lck:
        if qid in bind_cache:
            if error == False:
                pcrid_num = len(bind_cache[qid]["pcrid"])       #这个qq号绑定的pcrid个数
                if pcrid_id is None:        #只绑定1个uid时，绑定的序号可以不填。
                    if pcrid_num == 1:
                        pcrid_id = 1
                    else:
                        error = True
                        reply = '您绑定了多个uid，更改设置时需要加上序号。'
                if error == False:
                    if 0 <= pcrid_id and pcrid_id <= pcrid_num: ##设置成功！                
                        if quick_set == True:
                            change_quick_set = int(change)
                            if pcrid_id ==0:
                                for i in range(pcrid_num):
                                    bind_cache[qid]["noticeType"][i] = change_quick_set
                            else:
                                pcrid_id -= 1                       #从0开始计数，-1
                                bind_cache[qid]["noticeType"][pcrid_id] = change_quick_set
                        else:
                            if pcrid_id ==0:
                                for i in range(pcrid_num):                           
                                    tmp = int(bind_cache[qid]["noticeType"][i])
                                    jjcNotice = True if tmp//1000 else False
                                    pjjcNotice = True if (tmp%1000)//100 else False
                                    riseNotice = True if (tmp%100)//10 else False
                                    onlineNotice = True if tmp%10 else False
                                    if change == 'jjc':
                                        jjcNotice = turn_on
                                    elif change == 'pjjc':
                                        pjjcNotice = turn_on
                                    elif change == '排名上升':
                                        riseNotice = turn_on
                                    elif change == '上线提醒':
                                        onlineNotice = turn_on
                                    tmp = jjcNotice*1000 + pjjcNotice*100 + riseNotice*10 + onlineNotice
                                    bind_cache[qid]["noticeType"][i] = tmp
                            else:
                                pcrid_id -= 1                         #从0开始计数，-1
                                tmp = int(bind_cache[qid]["noticeType"][pcrid_id])
                                jjcNotice = True if tmp//1000 else False
                                pjjcNotice = True if (tmp%1000)//100 else False
                                riseNotice = True if (tmp%100)//10 else False
                                onlineNotice = True if tmp%10 else False
                                if change == 'jjc':
                                    jjcNotice = turn_on
                                elif change == 'pjjc':
                                    pjjcNotice = turn_on
                                elif change == '排名上升':
                                    riseNotice = turn_on
                                elif change == '上线提醒':
                                    onlineNotice = turn_on
                                tmp = jjcNotice*1000 + pjjcNotice*100 + riseNotice*10 + onlineNotice
                                bind_cache[qid]["noticeType"][pcrid_id] = tmp
                        reply = '设置成功！' 
                        save_binds()
                    else:
                        error = True
                        reply = '序号超出范围，请检查您绑定的竞技场列表'
        else:
            error = True
            reply = '您还没有绑定jjc，绑定方式：\n[竞技场绑定 uid] uid为pcr(b服)个人简介内13位数字'
    await session.send(reply)                
    #if error == True:        
    #    pic = image_draw(sv_help)
    #    await session.send(f'[CQ:image,file={pic}]')
    #else:
    #    pass
        #jjc_check(qid)
 
async def renew_pcrid_list():
    global bind_cache, pcrid_list, lck, bind_change, lck_friendList, friendList
    print(bind_cache)
    pcrid_list=[]
    async with lck_friendList:
        copy_friendList = friendList
    if len(copy_friendList)==0:
        await renew_friendlist()
        async with lck_friendList:
            copy_friendList = friendList
    if len(copy_friendList)==0:
        return
    async with lck:        
        for qid in bind_cache:
            if bind_cache[qid]["notice_on"] == False:
                continue
            else:
                if qid not in copy_friendList:
                    bind_cache[qid]["notice_on"] = False
                    continue
                for i in bind_cache[qid]["pcrid"]:
                    pcrid_list.append(int(i))
    bind_change = False
    print('renew_pcrid_list')
    pcrid_list = list(set(pcrid_list))


@sv.scheduled_job('cron', hour='5')
def clear_ranking_rise_time():
    global cache, today_notice ,yesterday_notice
    yesterday_notice = today_notice
    today_notice = 0
    cache_del = []
    for pcrid in cache:
        if pcrid in pcrid_list_cron1 or pcrid in pcrid_list_cron2:
            cache[pcrid][3] = 0
            cache[pcrid][4] = 0
        else:
            cache_del.append(pcrid)
    for pcrid in cache_del:
        del cache[pcrid]
            
async def schedule_query_processing(pcrid:int, arena_rank:int, grand_arena_rank:int, last_login_time:int):
    res = [arena_rank, grand_arena_rank, last_login_time, 0, 0]     #后面两个0：jjc/pjjc今日排名上升次数
    global cache
    #print('###1')
    if pcrid not in cache:
        cache[pcrid] = res
    else:
        last = deepcopy(cache[pcrid])
        cache[pcrid][0] = res[0]
        cache[pcrid][1] = res[1]
        cache[pcrid][2] = res[2]
        if res[0] != last[0]:
            if res[0] < last[0]:
                cache[pcrid][3] += 1    #今日jjc排名上升次数+1
            await sendNotice(res[0],last[0],pcrid,1)
        if res[1] != last[1]:
            if res[1] < last[1]:
                cache[pcrid][4] += 1    #今日pjjc排名上升次数+1
            await sendNotice(res[1],last[1],pcrid,2)
        if res[2] != last[2]:
            if (res[2]-last[2]) < 300:      #最后上线时间变动小于300秒，不提醒，不刷新缓存。
                cache[pcrid][2] = last[2]
            else:
                last_login_hour = (res[2]%86400//3600+8)%24
                last_login_min = res[2]%3600//60
                if last_login_hour ==14 and last_login_min >=30:
                    await sendNotice(res[2],0,pcrid,3)
                    
async def auto_query1():
    global pcrid_list_cron1
    query1_failed = []
    for pcrid in pcrid_list_cron1:
        try:
            re = await query1(pcrid)            
        except:
            query1_failed.append(pcrid)
            continue
        await schedule_query_processing(pcrid, int(re['arena_rank']), int(re['grand_arena_rank']), int(re['last_login_time']))
    if len(query1_failed):
        print('线程1检查出错！pcrid：',query1_failed)
    return 1

async def auto_query2():
    global pcrid_list_cron2
    query2_failed = []
    for pcrid in pcrid_list_cron2:
        try:
            re = await query2(pcrid)
        except:
            query2_failed.append(pcrid)
            continue
        await schedule_query_processing(pcrid, int(re['arena_rank']), int(re['grand_arena_rank']), int(re['last_login_time']))
    if len(query2_failed):
        print('线程2检查出错！pcrid：',query2_failed)
    return 2

@sv.scheduled_job('interval', seconds=5)            
async def schedule_query():
    global pcrid_list, bind_change, pcrid_list_cron1, pcrid_list_cron2, timeStamp
    if bind_change == True or len(pcrid_list) ==0:
        await renew_pcrid_list()
        pcrid_num = len(pcrid_list)
        query_cron = 0
        pcrid_list_cron1 = []
        pcrid_list_cron2 = []
        for i in pcrid_list:
            query_cron += 1
            if query_cron == 1:
                pcrid_list_cron1.append(i)
            elif query_cron ==2:
                pcrid_list_cron2.append(i)
            if query_cron >=2:
                query_cron = 0
    #print(pcrid_list)
    timeStamp = int(time.time())
    task1 = asyncio.create_task(
        auto_query1())
    task2 = asyncio.create_task(
        auto_query2())
    #print(f"start at {time.strftime('%X')}")

    ret1 = await task1
    ret2 = await task2

    #print('pcrjjc',ret1,ret2)

    #print(f"finsidhed at {time.strftime('%X')}")
        
          

#async def on_arena_schedule():
#    await schedule_query()
            

@on_command('bind_add',patterns=('^竞技场绑定'), only_to_me=False)
async def bind_add(session):
    global bind_cache, bind_change, lck, friendList, adm_list
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    if session.ctx['message_type'] == 'group':
        gid = session.ctx['group_id']
    else:
        gid = 0
    msg = str(session.ctx['message']) 
    error = False
    try:                #检查输入格式
        ret = re.match(r'^ ?竞技场绑定 ?(\d+) ?(\S+)?$', msg)
        pcrid = int(ret.group(1))
        print(pcrid)
        print(len(ret.group(1)))
        if len(ret.group(1)) != 13:
            reply = '位数不对，uid是13位的！'
            error = True
        else:
            try:        #是否指定昵称
                if len(ret.group(2)) <=12:
                    nickname = ret.group(2)
                    use_nickname = True
                else:
                    reply = '昵称不能超过12个字，换个短一点的昵称吧~'
                    error = True
            except:
                use_nickname = False
    except:
        reply = '输入的格式不太对呢~'
        error = True
    if error == False:
        try:            #检测uid是否有效
            res = await query0(pcrid)
        except:
            try:        #失败后再试一次。
                res = await query0(pcrid)
            except:
                reply = '找不到这个uid，大概率是你输错了！'
                error = True
    if error:
        #reply += '\n发送”竞技场帮助“获取帮助文档。'
        await session.send(reply)
        return
    async with lck:
        if qid in bind_cache:
            bind_num = len(bind_cache[qid]["pcrid"])
            if bind_num >= 8:
                reply = '您订阅了太多账号啦！'
                await session.send(reply)
                return
            else:
                if pcrid in bind_cache[qid]["pcrid"]:
                    reply = '这个uid您已经订阅过了，不要重复订阅！'
                    await session.send(reply)
                    return
                else:
                    bind_cache[qid]["pcrid"].append(pcrid)
                    if use_nickname == False:
                        nickname = res["user_name"]
                    bind_cache[qid]["pcrName"].append(nickname)
                    bind_cache[qid]["noticeType"].append(1100)
                    reply = '添加成功！'
        else:
            if use_nickname == False:
                nickname = res["user_name"]              
            bind_cache[qid] = {
                "pcrid": [pcrid],
                "noticeType": [1100],
                "pcrName": [nickname],
                "gid": gid,
                "bot_id": 0,
                "private":False,
                "notice_on":False
            }
            reply = '添加成功！'
            if gid == 0:
                bind_cache[qid]["private"] = True
                if len(friendList):
                    await renew_friendlist()
                if qid in friendList:
                    pri_user = 0
                    for i in bind_cache:
                        if bind_cache[i]['notice_on'] and bind_cache[i]['private']:
                            pri_user += 1
                    if pri_user >= 3:
                        reply += '私聊推送用户已达上限！无法开启私聊推送。你可以发送“在本群推送”，改为群聊推送。'
                    else:
                        bind_cache[qid]["notice_on"] = True
                        reply_adm = f'''{qid}添加了私聊pcrjjc推送'''
                        await bot.send_private_msg(user_id = adm_list[0], message = reply_adm)
                        reply += '已为您开启推送。由于是私聊推送，已通知管理员！'
                else:
                    reply += '开启私聊推送需要先加好友！你也可以发送“在本群推送”，改为群聊推送。'
            else:
                bind_cache[qid]["notice_on"] = True
                reply +='已为您开启群聊推送！'

        save_binds()
    bind_change = True
    
    await session.send(reply)


@on_command('bind_del',patterns=('^删除竞技场绑定'), only_to_me=False)
async def bind_del(session):
    global bind_cache, bind_change, lck
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    msg = str(session.ctx['message']) 
    try:
        ret = re.match(r'^ ?删除竞技场绑定 ?(\d)$', msg)
        pcrid_id = int(ret.group(1))
    except:
        reply = '输入格式不对！“删除竞技场绑定+【序号】”（序号不可省略）'
        await session.send(reply)
        return
    async with lck:
        if qid in bind_cache:
            pcrid_num = len(bind_cache[qid]["pcrid"])
            if pcrid_num == 1:
                reply = '您只有一个绑定的uid，请使用“清空竞技场绑定”删除'
                await session.send(reply)
                return 
            if pcrid_id > 0 and  pcrid_id <= pcrid_num:
                pcrid_id -= 1
                reply = f'''您已成功删除：【{pcrid_id+1}】{bind_cache[qid]["pcrName"][pcrid_id]}（{bind_cache[qid]["pcrid"][pcrid_id]}）'''
                del bind_cache[qid]["pcrid"][pcrid_id]
                del bind_cache[qid]["noticeType"][pcrid_id]
                del bind_cache[qid]["pcrName"][pcrid_id]
            else:
                reply = '输入的序号超出范围！'
                await session.send(reply)
        save_binds()
    bind_change = True
    await session.send(reply)
    
@on_command('bind_clear',aliases=('清空竞技场绑定'), only_to_me=False)
async def bind_clear(session):
    global bind_cache, bind_change, lck
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    async with lck:
        if qid in bind_cache:
            reply = '删除成功！\n'
            for pcrid_id in range(len(bind_cache[qid]["pcrid"])):
                reply += f'''【{pcrid_id+1}】{bind_cache[qid]["pcrName"][pcrid_id]}\n（{bind_cache[qid]["pcrid"][pcrid_id]}）\n'''
            del bind_cache[qid]
        else:
            reply = '您还没有绑定竞技场！'
            await session.send(reply)
            return
        save_binds()
    bind_change = True
    await session.send(reply)

@on_command('notice_on_change',patterns=('^(开启|关闭)竞技场推送$'), only_to_me=False)
async def notice_on_change(session):
    global bind_cache, bind_change, lck ,friendList, adm_list
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    msg = str(session.ctx['message'])
    try:
        ret = re.match(r'^ ?(开启|关闭)竞技场推送$', msg)
        turn_on =True if ret.group(1) == '开启' else False
    except:
        reply = '出错了，请联系管理员！'
        await session.send(reply)
        return
    async with lck:
        if qid in bind_cache:
            if bind_cache[qid]["notice_on"] == turn_on:
                reply = f'''您的竞技场推送，已经是{ret.group(1)}状态，不要重复{ret.group(1)}！'''
                await session.send(reply)
                return
            else:
                if turn_on:
                    if len(friendList):
                        await renew_friendlist()
                    if bind_cache[qid]["private"]:
                        if qid not in friendList:
                            reply = '开启私聊推送需要先加好友！你也可以发送“在本群推送”，改为群聊推送。'
                            await session.send(reply)
                            return
                        else:
                            for i in bind_cache:
                                if bind_cache[i]['notice_on'] and bind_cache[i]['private']:
                                    pri_user += 1
                            if pri_user >= 3:
                                await session.send('私聊推送用户已达上限！')
                                return
                            reply_adm = f'''{qid}开启了私聊jjc推送！''' 
                            await session.send('已通知管理员')
                            await bot.send_private_msg(user_id = adm_list[0], message = reply_adm)
                bind_cache[qid]["notice_on"] = turn_on
        else:
            reply = '您还没有绑定竞技场！'
            await session.send(reply)
            return
        save_binds()
    bind_change = True
    reply = f'''竞技场推送{ret.group(1)}成功！'''
    await session.send(reply)            

@on_command('manual_query',patterns=('^竞技场查询'), only_to_me=False)
async def manual_query(session):
    global bind_cache, cache
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    #name = session.ctx['sender']['nickname']
    msg = str(session.ctx['message'])
    error = False
    use_nickname = False
    try:
        ret = re.match(r'^ ?竞技场查询 ?(\d+)?$', msg)             
        try:
            pcrid = int(ret.group(1))
            if(len(ret.group(1))) != 13:
                reply = '位数不对，uid是13位的！'
                error = True
            else:
                manual_query_list = [pcrid]     #手动查询的列表
        except:
            if qid in bind_cache:
                manual_query_list = bind_cache[qid]["pcrid"]
                manual_query_list_name = bind_cache[qid]["pcrName"]
                #if bind_cache[qid]["notice_on"]:
                    
                use_nickname = True
            else:
                reply = '木有找到绑定信息，查询时不能省略13位uid！'
                error = True
    except:
        reply = '输入的格式不太对呢~'
        error = True
    if error:
        await session.send(reply)
    else:
        st = ''
        for i in range(len(manual_query_list)):
            pcrid = manual_query_list[i]
            res = await query0(pcrid)
            last_login_hour = (int(res["last_login_time"])%86400//3600+8)%24
            last_login_min = int(res["last_login_time"])%3600//60
            last_login_min = '%02d' % last_login_min        #分钟补零，变成2位
            if use_nickname:
                res["user_name"] = manual_query_list_name[i] 
            extra = ''
            if pcrid in cache:
                extra = f'''上升: {cache[pcrid][3]}次 / {cache[pcrid][4]}次\n'''
            st = st + f'''【{i+1}】{res["user_name"]}\n{res["arena_rank"]}({res["arena_group"]}场) / {res["grand_arena_rank"]}({res["grand_arena_group"]}场)\n{extra}最近上号{last_login_hour}：{last_login_min}\n\n'''
        #pic = await to_img_msg(st,title=f'''{name}的查询结果''')
        pic = image_draw(st)
        await session.send(f'[CQ:image,file={pic}]')
        
@on_command('status_query',aliases=('竞技场订阅状态'), only_to_me=False)
async def status_query(session):
    global bind_cache, bot_list, bot_name
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    name = session.ctx['sender']['nickname']
    if qid in bind_cache:
        bot_id = bind_cache[qid]["bot_id"]
        private = '私聊推送' if bind_cache[qid]["private"] else '群聊推送'
        notice_on = '推送已开启' if bind_cache[qid]["notice_on"] else '推送未开启'
        reply = f'''{name}（{qid}）的竞技场订阅列表：\n\n'''
        reply += f'''群号：{bind_cache[qid]["gid"]}\n推送bot：{bot_name[bot_id]}({bot_list[bot_id]})\n'''
        reply += f'''推送方式：{private}\n状态：{notice_on}\n'''
        for pcrid_id in range(len(bind_cache[qid]["pcrid"])):
            reply += f'''\n【{pcrid_id+1}】{bind_cache[qid]["pcrName"][pcrid_id]}（{bind_cache[qid]["pcrid"][pcrid_id]}）\n'''
            tmp = bind_cache[qid]["noticeType"][pcrid_id]
            jjcNotice = True if tmp//1000 else False
            pjjcNotice = True if (tmp%1000)//100 else False
            riseNotice = True if (tmp%100)//10 else False
            onlineNotice = True if tmp%10 else False
            noticeType = '推送内容：'
            if jjcNotice:
                noticeType += 'jjc、'
            if pjjcNotice:
                noticeType += 'pjjc、'
            if riseNotice:
                noticeType += '排名上升、'
            if onlineNotice:
                noticeType += '上线提醒、'
            if noticeType == '推送内容：':
                noticeType += '无'
            else:
                noticeType = noticeType.strip('、')
            reply += noticeType
            reply += '\n'                
        pic = image_draw(reply)
        #pic = await to_img_msg(reply,title = f'''{name}（{qid}）的竞技场订阅列表''')
        await session.send(f'[CQ:image,file={pic}]')
    else:
        reply = '您还没有绑定竞技场！'
        await session.send(reply)

@on_command('change_nickname',patterns=('^竞技场修改昵称'), only_to_me=False)
async def change_nickname(session):
    global bind_cache, bind_change, lck
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    msg = str(session.ctx['message']) 
    if qid not in bind_cache:
        reply = '您还没有绑定竞技场！'
        await session.send(reply)
        return
    try:
        ret = re.match(r'^ ?竞技场修改昵称 ?(\d)? (\S+)$', msg)
        try:
            pcrid_id = int(ret.group(1))
        except:
            pcrid_id = None 
        if len(ret.group(2)) <= 12:
            name = ret.group(2)
        else:
            reply = '昵称不能超过12个字，换个短一点的昵称吧~'
            await session.send(reply)
            return
    except:
        reply = '输入格式不对！“竞技场修改昵称 [序号] 新的昵称”\n（序号可以通过“竞技场查询”、“竞技场订阅状态”获取）'
        await session.send(reply)
        return
    pcrid_num = len(bind_cache[qid]["pcrid"])
    if pcrid_id is None:
        if pcrid_num == 1:
            pcrid_id = 1
        else:
            reply = '您绑定了多个uid，更改昵称时需要加上序号。'
            await session.send(reply)
            return
    if pcrid_id ==0 or pcrid_id > pcrid_num:
        reply = '序号超出范围，请检查您绑定的竞技场列表'
        await session.send(reply)
        return
    async with lck:
        pcrid_id -= 1
        bind_cache[qid]["pcrName"][pcrid_id] = name
        save_binds()
    bind_change = True
    reply = '更改成功！'
    await session.send(reply)
        
@sv.scheduled_job('interval', hours = 5)
async def renew_friendlist():
    global friendList, bind_change, lck_friendList
    bot = get_bot()
    old_friendList = friendList
    #flist = await bot.get_friend_list(self_id = )
    flist = await bot.get_friend_list()
    print(f'''好友列表已全部刷新''')
    async with lck_friendList:
        friendList = []
        for i in flist:
            friendList.append(str(i['user_id']))
        old_friendList = list(set(old_friendList))
        friendList = list(set(friendList))
        if old_friendList != friendList:
            bind_change = True
            print('friendList change!!!')
    print(friendList)
    
@sv.on_notice('friend_add')     #新增好友时，不全部刷新好友列表
async def friend_add(session: NoticeSession):
    global friendList
    print(session.event)
    ev = session.event
    new_friend = str(ev.user_id)
    self_id = ev.self_id
    #print('new_friend',new_friend,type(new_friend))
    #print('self_id',self_id,type(self_id))
    async with lck_friendList:
        friendList.append(new_friend)

        

@on_command('load_query',aliases=('pcrjjc负载查询'), only_to_me=False)
async def load_query(session):
    global bind_cache, today_notice, yesterday_notice, adm_list
    qid = session.ctx['user_id']
    if qid not in adm_list:
        return
    #qid_num = 0
    qid_notice_on_private = 0
    qid_notice_on_group = 0
    pcrid_num_private = 0
    pcrid_num_group = 0
    for qid in bind_cache:
        if bind_cache[qid]['notice_on']:
            if bind_cache[qid]['private']:
                qid_notice_on_private += 1
                pcrid_num_private += len(bind_cache[qid]['pcrid'])
            else:
                qid_notice_on_group += 1
                pcrid_num_group += len(bind_cache[qid]['pcrid'])
    msg = f'''小真步的负载：\n群聊用户数量：{qid_notice_on_group} 群聊绑定的uid：{pcrid_num_group}个\n私聊用户数量：{qid_notice_on_private} 私聊绑定的uid：{pcrid_num_private}个\n昨天推送次数：{yesterday_notice} 今天推送次数：{today_notice}'''
    pic = image_draw(msg)
    await session.send(f'[CQ:image,file={pic}]')
    
@on_command('group_set',aliases=('在本群推送'),only_to_me=False)
async def group_set(session):
    global bind_cache, lck, adm_list, auth_list, bind_change
    if ban(session):
        return
    qid = str(session.ctx['user_id'])
    if session.ctx['message_type'] != 'group':
        return
    gid = session.ctx['group_id']
    if qid in bind_cache:
        async with lck:
            bind_cache[qid]['gid'] = gid
            bind_cache[qid]['private'] = False
            bind_cache[qid]['notice_on'] = True
            reply = '设置成功！已为您开启推送。'
            save_binds()   
            bind_change = True
    await session.send(reply)

@on_command('private_notice',aliases=('换私聊推送'),only_to_me= False)
async def private_notice(session):
    global bind_cache, lck, friendList, adm_list, bind_change
    if ban(session):
        return
    pri_user = 0
    qid = str(session.ctx['user_id'])
    for i in bind_cache:
        if bind_cache[i]['notice_on'] and bind_cache[i]['private']:
            pri_user += 1
    if pri_user >= 3:
        await session.send('私聊推送用户已达上限！')
        return
    if session.ctx['message_type'] != 'private':
        await session.send('仅限好友私聊使用！')
        return
    if len(friendList):
        await renew_friendlist()
    if qid not in friendList:
        return
    async with lck:
        bind_cache[qid]['private'] = True
        bind_cache[qid]['notice_on'] = True
        save_binds()
        bind_change = True
    reply = '设置成功！已为您开启推送。已通知管理员！'
    reply_adm = f'''{qid}开启了私聊jjc推送！'''
    await session.send(reply)
    await bot.send_private_msg(user_id = adm_list[0], message = reply_adm)
    
    
@on_command('no_private',aliases=('pcrjjc关闭私聊推送'),only_to_me=False)
async def no_private(session):
    global bind_cache ,lck, adm_list, bind_change
    user_id = session.ctx['user_id']
    if user_id not in adm_list:
        return
    async with lck:
        for qid in bind_cache:
            if bind_cache[qid]['private'] and bind_cache[qid]['notice_on']:
                bind_cache[qid]['notice_on'] = False
        save_binds()
        bind_change = True
    await session.send('所有设置为私聊推送的用户的推送已关闭！')

@on_command('del_binds',patterns=('^pcrjjc删除绑定 ?\d{6,10}'),only_to_me=False)
async def del_binds(session):
    global bind_cache, lck, adm_list, bind_change
    user_id = session.ctx['user_id']
    if user_id not in adm_list:
        return
    msg = str(session.ctx['message'])
    ret = re.match(r'^ ?pcrjjc删除绑定 ?(\d{6,10})',msg)
    qid = str(ret.group(1))
    if qid in bind_cache:
        async with lck:
            del bind_cache[qid]
            save_binds()
            bind_change = True
        reply = '删除成功！'
    else:
        reply = '绑定列表中找不到这个qq号！'
    await session.send(reply)