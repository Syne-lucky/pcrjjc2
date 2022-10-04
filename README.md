基于怡宝魔改的多线程自动过验证码的jjc2魔改。

警告：本插件代码质量很差，介意请使用[公版pcrjjc2](https://github.com/cc004/pcrjjc2)。目前手动过验证码的部分有问题，如果路路的自动过验证码服务器寄了，会导致本插件不可用！欢迎大佬改了pr。

支持：1）多线程 2）自动过验证码 3）每个人可以绑定多个uid
4）每个uid可以设置不同的推送内容 5）内存记录击剑记录，重启bot会清空
6）所有指令支持私聊/群聊，支持私聊/群聊推送。

部署方法：
1）按照注释，填写main.py第16~18行
第68、69行，填写ban_group和ban_qq（黑名单）

~~2）下载字体文件 sarasa-mono-sc-regular.ttf~~
~~链接：https://pan.baidu.com/s/12syDRW6Jx-0IlPJKPM5fcA~~
~~提取码：8080~~
~~放在合适的位置，建议放res文件夹。~~
~~在text2img.py填入这个字体文件的路径~~

3）在cron0~2的accoun.json里面填入pcr查询号（过了新手教程就行，不用解锁jjc）

注：默认2线程，cron0手动查询使用，别的定时查询用。可以自己加线程。n个线程需要n+1个pcr查询号。默认5秒查询一次。
短时间内太多私聊，可能导致封号。默认最多3个用户使用私聊推送，你可以把上限改成5，再多就不建议了。如果用户都是不怎么卡点击剑的，上限可以设置的更高，但有风险！实测14：56~15：01给>5个qq发送>15条私聊消息，可能就会导致封号。有用户开启私聊推送的时候，bot会私聊通知主人。
会有3条指令重复注册的warning，无视就行，目前不影响使用。手动过验证码的部分有问题，如果路路的自动过验证码服务器寄了，会导致本插件不可用！欢迎大佬改了pr。
C:\Users\Administrator\AppData\Local\Programs\Python\Python38\lib\site-packages\nonebot\command\__init__.py:224: UserWarning: Command ('validate0',) already exists
  warnings.warn(f"Command {cmd_name} already exists")

ps：感谢路路的自动过验证码的服务器。
有问题可以在星乃群（813563151）找那个春田头像的（3588116504）。
免费jjcbot群498774643。

![](C:\Users\zly\AppData\Roaming\marktext\images\2022-10-03-14-20-07-_{O6~]NXY5N7ZQ39I%RZ91I.PNG)
