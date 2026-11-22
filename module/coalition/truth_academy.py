from module.coalition.coalition_daily import CoalitionDaily


class TruthAcademy(CoalitionDaily):
    """
    真理学院的转校生

    本期共斗活动（coalition_20261124）的专属任务。
    逻辑与「多队出击活动通用」完全相同，只是固定了活动、并使用独立的配置组，
    方便在「活动」分类里单独启用和设置难度。
    """

    CONFIG_GROUP = 'TruthAcademy'
    EVENT = 'coalition_20261124'
