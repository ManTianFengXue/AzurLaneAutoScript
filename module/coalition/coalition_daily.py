import random

from module.base.button import Button
from module.base.timer import Timer
from module.campaign.assets import OCR_OIL_CHECK
from module.coalition.assets import (
    TRUTH_ATTACK,
    TRUTH_EXP_CHECK,
    TRUTH_MAIN_BAR,
    TRUTH_MAIN_CHECK,
    TRUTH_REWARD_CHECK,
    TRUTH_CONFIRM,
    TRUTH_MODE_BATTLE,
    TRUTH_REWARD_CONFIRM,
    TRUTH_SWITCH_MULTI,
    TRUTH_SWITCH_SINGLE,
    TRUTH_TOUCH_CONTINUE,
    TRUTH_VICTORY_TEXT,
    TRUTH_FLEET_PREPARATION,
    TRUTH_PT_CHECK,
    TRUTH_PT_TEXT,
    TRUTH_PAGE_CHECK,
    TRUTH_HARD,
)
from module.coalition.coalition import Coalition
from module.combat.assets import BATTLE_PREPARATION, BATTLE_STATUS_A, BATTLE_STATUS_B, BATTLE_STATUS_S
from module.coalition.assets import COALITION_REWARD_CONFIRM
from module.exception import CampaignEnd, CampaignNameError, RequestHumanTakeover
from module.os_ash.assets import BATTLE_STATUS
from module.logger import logger


class CoalitionDaily(Coalition):
    """
    多队出击活动通用

    流程与「怪谈纪实」（Coalition）一致，区别只有难度可选 简单/普通/困难/SP/EX。
    出击菜单里嵌着本期活动的宣传横幅，用局部素材判断「是否在活动页」会串台，
    因此进入活动页、选难度、切队伍、立即前往全部使用固定坐标，
    每次点击附加 ±10 像素随机偏移与 0.5~1 秒随机延迟。
    """

    # 难度标签中心点（1280x720）
    # 难度入口：整体比标签中心下移 10 像素，偏上会点不中
    STAGE_POINTS = {
        'easy': (175, 300),
        'normal': (350, 145),
        'hard': (695, 192),
        'sp': (828, 534),
        'ex': (975, 268),
    }
    # 右上角「返回主页」
    GOTO_MAIN_POINT = (1228, 64)   # 右上角圆形主页按钮的圆心
    # 主界面「出击」按钮
    SORTIE_POINT = (1200, 525)
    # 出击菜单里的活动横幅
    BANNER_POINT = (750, 220)
    # 主界面右侧的活动横幅，直接进活动页
    MAIN_EVENT_BANNER = (1190, 385)
    # 舰队准备界面
    SWITCH_MULTI_POINT = (1137, 397)
    SWITCH_SINGLE_POINT = (997, 397)
    START_POINT = (1025, 545)
    # 编队界面的「出击」
    ATTACK_POINT = (1150, 633)
    # 战斗与结算的时间节奏（秒）
    SCAN_TIMEOUT = 190          # 每次扫描窗口
    SCAN_INTERVAL = 1           # 扫描间隔
    AFTER_CLICK_WAIT = 5        # 点完屏幕正中后等待

    STEP_WAIT = 1.5             # 固定坐标点击后的等待

    # 战斗结算界面：点屏幕正中继续
    SCREEN_CENTER = (640, 360)
    EXP_CONFIRM_POINT = (1137, 660)
    REWARD_CONFIRM_POINT = (842, 623)
    CONFIRM_POINT = (1150, 660)
    REWARD_CONFIRM_POINT = (842, 623)
    REWARD_SCAN_TIMEOUT = 10
    VICTORY_STATUS = (TRUTH_VICTORY_TEXT, TRUTH_TOUCH_CONTINUE)

    @staticmethod
    def _point(point, size=12, name=None):
        """
        把坐标包装成可点击的 Button。

        注意：Alas 有「同一按钮短时间内点击过多即判定卡死」的保护，
        因此每次点击都用带坐标与随机数的唯一名字，避免误触发。

        Args:
            point (tuple): (x, y)
            size (int): 点击框半径
            name (str): 按钮名，默认自动生成唯一名字

        Returns:
            Button:
        """
        x, y = point
        if name is None:
            name = f'DAILY_POINT_{x}_{y}_{random.randint(0, 99999)}'
        box = (x - size, y - size, x + size, y + size)
        return Button(area=box, color=(0, 0, 0), button=box, name=name)

    def _click(self, point, times=1, jitter=10, delay=(0.5, 1.0)):
        """
        点击坐标，附加随机偏移与随机延迟。

        Args:
            point (tuple): (x, y)
            times (int): 点击次数，2 即为双击
            jitter (int): 随机偏移半径
            delay (tuple): 延迟区间，单位秒
        """
        for _ in range(times):
            x = point[0] + random.randint(-jitter, jitter)
            y = point[1] + random.randint(-jitter, jitter)
            logger.info(f'点击 ({x}, {y})')
            self.device.click(self._point((x, y)))
            self.device.sleep(random.uniform(*delay))

    def _wait_for(self, button, timeout=10):
        """
        在指定时间内循环等待按钮出现。

        Args:
            button (Button): 目标按钮
            timeout (int): 超时秒数

        Returns:
            bool: 是否出现
        """
        timer = Timer(timeout, count=timeout * 5).start()
        while 1:
            if self.appear(button, offset=(20, 20)):
                return True
            if timer.reached():
                logger.warning(f'等待 {button.name} 超时')
                return False

    def triggered_stop_condition(self, oil_check=False, pt_check=False):
        """
        油量统一在进入活动前（出击菜单）判定一次，这里不再重复判断。

        父类会在每场战斗前和每轮开始时各查一次油量，而这两个时机都在
        活动页上，那里看不到顶部资源栏，必然读不到油量，只会刷「未识别到
        油量图标」的日志。因此这里直接把油量检查关掉。
        """
        return super().triggered_stop_condition(oil_check=False, pt_check=pt_check)

    def _on_main_page(self):
        """
        是否在主界面。

        Returns:
            bool:
        """
        # 用纯颜色比对（appear_on），模板匹配在委托等界面上会误判
        self.device.screenshot()
        return bool(TRUTH_MAIN_CHECK.appear_on(self.device.image))

    def _ensure_main_page(self):
        """
        在主界面时右上角是「设置」按钮，点了会打开设置面板，
        因此必须先判断是否在主界面：用底部导航栏（只有主界面才有）。

        Returns:
            bool: 是否已经在主界面
        """
        self.device.screenshot()
        if TRUTH_MAIN_BAR.appear_on(self.device.image):
            logger.info('已在主界面，无需返回')
            return True

        logger.info(f'不在主界面，点击右上角返回主页 {self.GOTO_MAIN_POINT}')
        self._click(self.GOTO_MAIN_POINT)
        self.device.sleep(2)

        self.device.screenshot()
        if TRUTH_MAIN_BAR.appear_on(self.device.image):
            logger.info('已返回主界面')
        else:
            logger.warning('未能确认回到主界面，继续流程')
        return True

    def _on_coalition_page(self):
        """
        是否停在活动页。

        要求三处同时命中，避免结算画面 / 半透明遮罩等误判：
        1. PT页   —— 右上角三个按钮里的第一个
        2. 右侧整列（PT页 + 排行榜 + 任务）
        3. 困难   —— 难度标签

        未通过时记录缺少哪一项，便于排查卡在哪里。

        Returns:
            bool:
        """
        self.device.screenshot()
        missing = []
        if not self.appear(TRUTH_PT_TEXT, offset=(5, 5)):
            missing.append('PT页')
        if not self.appear(TRUTH_PAGE_CHECK, offset=(5, 5)):
            missing.append('右侧整列')
        if not self.appear(TRUTH_HARD, offset=(5, 5)):
            missing.append('困难')

        if not missing:
            self._page_missing_logged = False
            return True

        # 连续失败只打一次，避免循环里刷屏；重新命中后复位
        if not getattr(self, '_page_missing_logged', False):
            logger.info(f'活动页判定未通过，缺少：{"、".join(missing)}')
            self._page_missing_logged = True
        return False

    def in_coalition(self):
        """
        父类用这个判断本回合是否结束。

        官方实现用的是页面检查图（模板匹配、容差大），在战斗结算画面上
        会误判成已回地图导致回合立刻结束，这里换成 PT页文字判定。
        """
        return self._on_coalition_page()

    def ui_goto_coalition(self, *args, **kwargs):
        """
        主界面 -> 出击 -> 出击菜单判定油量 -> 活动横幅 -> 活动页

        油量高于停止条件下限才继续，低于下限则停止任务。

        Pages:
            in: Any page
            out: page_coalition
        """
        # 1) 确保在主界面
        self._ensure_main_page()

        # 2) 主界面点「出击」
        logger.info(f'点击主界面出击按钮 {self.SORTIE_POINT}')
        self._click(self.SORTIE_POINT)
        self.device.sleep(2)

        # 3) 出击后可能有弹窗遮挡，先清掉再读油量（与官方 ui.py 一致）
        for _ in range(3):
            self.device.screenshot()
            if self.handle_guild_popup_cancel() \
                    or self.handle_popup_single('COALITION') \
                    or self.handle_popup_confirm('COALITION') \
                    or self.handle_popup_cancel('COALITION'):
                logger.info('关闭出击菜单上的弹窗')
                self.device.sleep(1)
                continue
            break

        # 4) 出击菜单里判定油量
        oil = self.get_oil()
        limit = max(500, self.config.StopCondition_OilLimit)
        logger.info(f'当前油量 {oil}，停止下限 {limit}')

        if oil and oil < limit:
            logger.warning(f'油量 {oil} 低于设定下限 {limit}，停止运行')
            self.config.task_delay(minute=(120, 240))
            self.config.task_stop()
            return
        if not oil:
            logger.warning('未能读取油量，跳过油量判定继续运行')

        # 4) 出击菜单点活动横幅
        logger.info(f'点击活动横幅 {self.BANNER_POINT}')
        self._click(self.BANNER_POINT)

        # 5) 等 PT页 确认进入活动页
        timer = Timer(5, count=50).start()
        while 1:
            if timer.reached():
                logger.critical('未能进入活动页：5 秒内没有识别到 PT页')
                raise RequestHumanTakeover
            if self._on_coalition_page():
                delay = random.uniform(0.5, 1.0)
                logger.info(f'已到达活动页，随机等待 {delay:.2f}s')
                self.device.sleep(delay)
                return

    def coalition_set_fleet(self, event, mode):
        """
        本期活动的队伍切换按钮颜色判定不通过（Switch 一直返回 single），
        改为点一次即返回，不做状态校验，避免反复点击。
        """
        button = TRUTH_SWITCH_MULTI if mode == 'multi' else TRUTH_SWITCH_SINGLE
        if self.appear(button, offset=(20, 10)):
            logger.info(f'点击队伍切换 {mode}（{button.name}）')
            self.device.click(button)
            self.device.sleep(0.5)
            return True

        logger.info(f'未找到队伍切换按钮 {mode}，保持当前设置')
        return False

    def handle_fleet_preparation(self, event, stage, mode):
        """
        简单/SP/EX 不允许切队伍，与官方一致；其余难度点一次切换。
        """
        if stage in ['easy', 'sp', 'ex']:
            return False

        self.coalition_set_fleet(event, mode)
        return False

    def _fallback_enter(self, stage, mode):
        """
        素材没点中时用固定坐标兜底，不再抛异常，保证任务继续。

        Args:
            stage (str): 难度
            mode (str): 队伍模式
        """
        point = self.STAGE_POINTS.get(str(stage).lower())
        if point is None:
            logger.critical(f'未知难度：{stage}')
            raise CampaignNameError

        logger.info(f'兜底：点击难度坐标 {point}')
        self._click(point)
        self.device.sleep(self.STEP_WAIT)

        switch = self.SWITCH_MULTI_POINT if mode == 'multi' else self.SWITCH_SINGLE_POINT
        logger.info(f'兜底：点击队伍 {mode} 坐标 {switch}')
        self._click(switch)
        self.device.sleep(self.STEP_WAIT)

        logger.info(f'兜底：点击立即前往坐标 {self.START_POINT}')
        self._click(self.START_POINT)

        if self._wait_for(BATTLE_PREPARATION, timeout=20):
            logger.info('兜底流程已进入编队界面')
        else:
            logger.warning('兜底流程未检测到编队界面')

    def enter_map(self, event, stage, mode):
        """
        进入关卡：固定坐标 + 固定等待。

        本期活动地图颜色复杂，素材在主页上会互相误匹配（实测难度/队伍/立即前往
        三个素材 50 毫秒内全部命中），因此这一步不再依赖素材判定，
        只用最后的 BATTLE_PREPARATION 确认是否真的进了编队界面。

        Pages:
            in: page_coalition
            out: BATTLE_PREPARATION
        """
        stage = str(stage).lower()
        point = self.STAGE_POINTS.get(stage)
        if point is None:
            logger.critical(f'未知难度：{stage}')
            raise CampaignNameError

        logger.info(f'点击难度 {stage}，坐标 {point}')
        self._click(point)

        # 正向检测：等「立即前往」按钮出现（一般 1~2 秒），最多等 6 秒。
        # 不能用"是否离开活动页"判断——舰队准备界面是半透明遮罩，
        # PT页 素材在那上面仍会误命中，导致白等 6 秒。
        wait_timer = Timer(6, count=12).start()
        arrived = False
        while 1:
            if self.appear(TRUTH_FLEET_PREPARATION, offset=(10, 5)):
                arrived = True
                break
            if wait_timer.reached():
                break
            self.device.sleep(0.5)

        if arrived:
            logger.info('已进入舰队准备界面')
        else:
            logger.warning('未检测到舰队准备界面，继续按固定坐标点击')

        switch = self.SWITCH_MULTI_POINT if mode == 'multi' else self.SWITCH_SINGLE_POINT
        logger.info(f'点击队伍 {mode} at {switch}')
        self._click(switch)
        self.device.sleep(1)

        logger.info(f'点击立即前往 {self.START_POINT}')
        self._click(self.START_POINT)
        # 编队界面与「出击」交给官方 combat_preparation 处理，
        # 它会在界面就绪后立刻点击，不需要我们等待

    def _appear_settlement(self):
        """
        是否还停在结算界面（EXP 结算或合计获得奖励弹窗）。

        Returns:
            bool:
        """
        # 纯颜色比对：模板匹配 + ±10 在活动页底部会误命中
        self.device.screenshot()
        return bool(TRUTH_EXP_CHECK.appear_on(self.device.image)
                    or TRUTH_REWARD_CHECK.appear_on(self.device.image))

    def _wait_settlement_gone(self, button, timeout=15):
        """
        点完确定后等结算界面消失，避免反复点击同一屏。

        Args:
            button (Button): 结算界面判定素材
            timeout (int): 最长等待秒数
        """
        timer = Timer(timeout, count=timeout).start()
        while self.appear(button, offset=(10, 5)):
            if timer.reached():
                logger.warning(f'{button.name} 超过 {timeout} 秒仍未消失')
                return
            self.device.sleep(1)
        logger.info(f'{button.name} 已消失')

    def coalition_combat_re_enter(self, skip_first_screenshot=True):
        """
        与官方 coalition_combat_re_enter 相同，额外识别本期活动的两种结算按钮：

        - EXP 结算：右下角「确定」          TRUTH_CONFIRM
        - 合计获得奖励弹窗：右下角「确定」  TRUTH_REWARD_CONFIRM

        最多尝试 6 次，之后按本回合结束处理。
        """
        logger.info('进入战斗结算循环')
        settlement_click = 0
        status_clicked = False
        click_timer = Timer(0.3)
        click_last = Timer(1, count=3)

        while 1:
            if skip_first_screenshot:
                skip_first_screenshot = False
            else:
                self.device.screenshot()

            if self.is_combat_loading():
                logger.info('检测到战斗加载中，退出结算循环')
                break
            if self.is_combat_executing():
                logger.info('检测到战斗进行中，退出结算循环')
                break

            # 各类弹窗统一交给官方处理器收拾，按可靠性从高到低依次尝试
            # 1) 大舰队弹窗（舰队任务完成的「我知道了」）
            if self.handle_guild_popup_cancel():
                logger.info('关闭大舰队弹窗')
                continue
            # 2) 单按钮弹窗（信息框、目标要求已完成等）
            if self.handle_popup_single('COALITION'):
                logger.info('关闭单按钮弹窗')
                continue
            # 3) 双按钮弹窗 → 确定
            if self.handle_popup_confirm('COALITION'):
                logger.info('关闭确定弹窗')
                continue
            # 4) 双按钮弹窗 → 取消
            if self.handle_popup_cancel('COALITION'):
                logger.info('关闭取消弹窗')
                continue

            # 结算界面：EXP 结算与合计获得奖励的确定位置不同，
            # 两个都点一次，哪一屏在都能点掉，点空处也无害
            if self._appear_settlement():
                if settlement_click >= 6:
                    logger.warning('连续 6 次未能关闭结算界面，按本回合结束处理')
                    raise CampaignEnd
                logger.info('检测到结算界面，依次点击两个确定')
                self.device.click(self._point(self.REWARD_CONFIRM_POINT))
                self.device.sleep(1)
                self.device.click(self._point(self.EXP_CONFIRM_POINT))
                self.device.sleep(1)
                settlement_click += 1

                # 每轮点完检查是否真的结算完了：
                # 必须「结算界面已经消失」且「PT页可见」才算回到活动主页。
                # 只判 PT页 是不行的——合计获得奖励弹窗盖不住右侧，
                # PT页 在对话框旁边仍然可见，会被误判成已回地图。
                if not self._appear_settlement() and self.in_coalition():
                    logger.info('结算完成，已回到活动界面，结束本回合前往下一轮')
                    raise CampaignEnd

                continue

            # 单场胜利界面：看到「大获全胜」或「点击继续」就点屏幕中间过掉
            # 放在结算判断之后，避免 EXP 结算（界面里也有三个大获全胜）被抢走
            if self.appear(TRUTH_VICTORY_TEXT, offset=(20, 20)) or \
                    self.appear(TRUTH_TOUCH_CONTINUE, offset=(20, 20)):
                logger.info('检测到胜利界面，点击屏幕中间')
                self.device.click(self._point(self.SCREEN_CENTER))
                self.device.sleep(1)
                continue

            if self.appear_then_click(BATTLE_STATUS, offset=(80, 20), interval=2):
                continue

            if self.handle_get_ship():
                continue
            if self.handle_battle_status():
                status_clicked = True
                click_last.reset()
                continue

            # 回到活动页：多队出击会连续打好几场，这里不能立刻结束回合，
            # 先等几秒看游戏会不会自动开下一场。
            if not self._appear_settlement() and self.in_coalition():
                logger.info('已回到活动页，等待是否还有下一场战斗')
                wait_next = Timer(10, count=20).start()
                battle_again = False
                while 1:
                    if self.is_combat_loading() or self.is_combat_executing():
                        battle_again = True
                        break
                    if wait_next.reached():
                        break
                    self.device.sleep(0.5)

                if battle_again:
                    logger.info('下一场战斗已开始，继续结算循环')
                    continue

                logger.info('10 秒内没有新的战斗，结束本回合')
                raise CampaignEnd

            # Keep clicking BATTLE_STATUS to skip animations
            if status_clicked:
                if click_timer.reached() and not click_last.reached():
                    self.device.click(BATTLE_STATUS)
                    click_timer.reset()

    def coalition_combat(self, *args, **kwargs):
        """
        战斗与结算完全复用官方实现（怪谈纪实同一套）：

        combat_preparation() -> auto_search_combat_execute()
        -> coalition_combat_re_enter() 循环，直到回到活动地图
        """
        logger.info('交付官方战斗与结算流程')
        return super().coalition_combat()

    def run(self, *args, **kwargs):
        event = self.config.Campaign_Event
        stage = str(self.config.CoalitionDaily_Mode).lower()
        fleet = str(self.config.CoalitionDaily_Fleet).lower()

        if not event or not str(event).startswith('coalition_'):
            logger.critical(f'活动选择不是共斗活动："{event}"')
            logger.critical('请先在「关卡设置」里选择本期共斗活动再运行')
            raise CampaignNameError

        logger.hr('Coalition daily', level=1)
        logger.attr('Event', event)
        logger.attr('Difficulty', stage)
        logger.attr('Fleet', fleet)

        # 让父类内部的情绪判断、SP 强制多队等逻辑读到本任务的队伍设置
        self.config.override(
            Coalition_Mode=stage,
            Coalition_Fleet=fleet,
        )

        super().run(event=event, mode=stage, fleet=fleet)
