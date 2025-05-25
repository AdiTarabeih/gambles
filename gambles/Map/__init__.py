# -*- coding: utf-8 -*-
"""
oTree app: new_decision_making_experiment
Two experimental treatments:

• random_grid – 7×6 board randomly shuffled for every participant
• avg_zones   – two fixed grids (Zone A vs. Zone B) shown side-by-side

The treatment is stored both in participant.vars['condition'] and in
Player.condition so it appears in every export file.
"""
from datetime import datetime
import random, json
from otree.api import *

# ─────────────────────────────────────────────────────────────
# 1.  HARD-CODED CELLS (do NOT change values or initials)
# ─────────────────────────────────────────────────────────────
GRID_ZONE_A = [
    (1,  18.7, 'KF'), (2, 19.2, 'DL'), (3, 18.9, 'TJ'),
    (4, 19.4, 'QS'), (5, 19.1, 'BP'), (6, 18.6, 'ZM'),
    (7, 19.3, 'HR'), (8, 18.6, 'VC'), (9, 18.8, 'NW'),
    (10, 19.2, 'GL'), (11, 19.5, 'EX'), (12, 18.7, 'UY'),
    (13,  0.0, '--'),                          # invest button A
    (14, 19.0, 'JB'), (15, 18.9, 'SO'), (16, 19.8, 'PK'),
    (17, 18.8, 'RA'), (18, 19.2, 'LM'), (19, 19.3, 'FD'),
    (20, 18.9, 'QT'), (21, 18.1, 'CX'),
]

GRID_ZONE_B = [
    (1,  13.9, 'HV'), (2, 14.2, 'AB'), (3, 14.1, 'PO'),
    (4, 14.3, 'MI'), (5, 14.0, 'RU'), (6, 13.4, 'CY'),
    (7, 13.3, 'TZ'), (8, 13.4, 'EG'), (9, 14.5, 'KB'),
    (10, 114.0, 'DS'), (11, 14.3, 'LN'), (12, 14.2, 'WI'),
    (13,  0.0, '--'),                          # invest button B
    (14, 14.1, 'QF'), (15, 14.4, 'SM'), (16, 14.2, 'JO'),
    (17, 14.0, 'VB'), (18, 14.3, 'CP'), (19, 13.8, 'UA'),
    (20, 13.4, 'NK'), (21, 14.2, 'GD'),
]

# ─────────────────────────────────────────────────────────────
# 2.  LOOK-UP TABLES
# ─────────────────────────────────────────────────────────────
TAG2ZONE = {t: 'A' for _, _, t in GRID_ZONE_A if t != '--'}
TAG2ZONE.update({t: 'B' for _, _, t in GRID_ZONE_B if t != '--'})

CELLS_MOVABLE = [                        # 40 tuples (payoff, tag)
    (pay, tag)
    for (_, pay, tag) in GRID_ZONE_A + GRID_ZONE_B
    if tag != '--'
]

# ─────────────────────────────────────────────────────────────
# 3.  GRID BUILDER  (random_grid treatment)
# ─────────────────────────────────────────────────────────────
def build_random_grid():
    """Return 42 triples (index, payoff, tag) for a 7×6 board."""
    cells = CELLS_MOVABLE[:]
    random.shuffle(cells)
    cell_iter = iter(cells)
    grid = []
    for pos in range(1, 43):
        if pos in (13, 34):                   # fixed invest buttons
            grid.append((pos, 0.0, '--'))
        else:
            pay, tag = next(cell_iter)
            grid.append((pos, pay, tag))
    return grid

# ─────────────────────────────────────────────────────────────
# 4.  PAYOFF HELPER
# ─────────────────────────────────────────────────────────────
def assign_payoff(player, tag):
    zone = TAG2ZONE[tag]                      # 'A' or 'B'
    player.raw_choice_val = tag
    player.choice_val     = 'A' if zone == 'A' else 'B'

    if player.choice_val == 'B':
        player.points_this_round = (
            C.risky_pointsRT_5rare
            if random.random() <= C.prob_5 else
            C.risky_pointsRT_5
        )
    else:
        player.points_this_round = C.safe_pointsRT_5

    player.total_points = player.points_this_round

# ─────────────────────────────────────────────────────────────
# 5.  oTree MODELS
# ─────────────────────────────────────────────────────────────
class C(BaseConstants):
    NAME_IN_URL = 'new_decision_making_experiment'
    PLAYERS_PER_GROUP = None
    NUM_ROUNDS = 1

    safe_pointsRT_5      = 19
    risky_pointsRT_5     = 14
    risky_pointsRT_5rare = 114
    prob_5 = 0.05        # 5 % rare outcome

    base_pay  = 0.2
    bonus_pay = 0.2


class Subsession(BaseSubsession):
    pass


class Group(BaseGroup):
    pass


class Player(BasePlayer):
    # demographics
    gender     = models.StringField(choices=['Male', 'Female', 'Other'])
    age        = models.IntegerField(min=15, max=90)
    connect_id = models.StringField()

    # treatment flag (saved to data)
    condition  = models.StringField()

    # choice tracking
    chosen_initials = models.StringField(blank=True)
    raw_choice_val  = models.StringField()
    choice_val      = models.StringField()

    points_this_round = models.FloatField(initial=0)
    total_points      = models.FloatField(initial=0)

    # payoff page fields
    total_payoff   = models.FloatField(initial=0)
    received_bonus = models.BooleanField(initial=False)

    # timing
    start_time = models.StringField()
    end_time   = models.StringField()
    total_time = models.FloatField()

    # board layout (random_grid only)
    grid_json = models.LongStringField(initial='')

# ─────────────────────────────────────────────────────────────
# 6.  SESSION INITIALISATION
# ─────────────────────────────────────────────────────────────
# 6. SESSION INITIALISATION  – balanced 50 : 50 assignment
def creating_session(subsession: Subsession):

    # ---- STEP 1–3: assign each Participant ----
    participants = subsession.session.get_participants()
    random.shuffle(participants)                     # optional; keeps it unpredictable

    n_total = len(participants)
    half    = n_total // 2                          # floor division

    for i, participant in enumerate(participants):
        if i < half:
            participant.vars['condition'] = 'random_grid'
        else:
            participant.vars['condition'] = 'avg_zones'

    # ---- STEP 4: copy into Player objects (for CSV export) ----
    for p in subsession.get_players():
        p.condition = p.participant.vars['condition']


# ─────────────────────────────────────────────────────────────
# 7.  PAGES
# ─────────────────────────────────────────────────────────────
class Intro(Page):
    form_model  = 'player'
    form_fields = ['gender', 'age', 'connect_id']

    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

    @staticmethod
    def before_next_page(player, timeout_happened):
        player.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


class Instructions(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == 1

# ─── Treatment 1: random_grid ────────────────────────────────
class avg_nozones(Page):
    """7×6 shuffled board"""
    form_model  = 'player'
    form_fields = ['chosen_initials']

    @staticmethod
    def is_displayed(player):
        return player.condition == 'random_grid'

    @staticmethod
    def vars_for_template(player):
        if not player.grid_json:
            grid = build_random_grid()
            player.grid_json = json.dumps(grid)
        else:
            grid = json.loads(player.grid_json)
        return dict(values_with_indices=grid)

    @staticmethod
    def error_message(player, values):
        tag = values.get('chosen_initials', '').upper()
        if tag not in TAG2ZONE:
            return "Please enter one of the two-letter tags on the board."

    @staticmethod
    def before_next_page(player, timeout_happened):
        assign_payoff(player, player.chosen_initials.upper())

# ─── Treatment 2: avg_zones ─────────────────────────────────
class AvgZones(Page):
    """Fixed Zone A / Zone B tables"""
    form_model  = 'player'
    form_fields = ['chosen_initials']

    @staticmethod
    def is_displayed(player):
        return player.condition == 'avg_zones'

    @staticmethod
    def vars_for_template(player):
        return dict(
            values_with_indices_a = GRID_ZONE_A,
            values_with_indices_b = GRID_ZONE_B,
        )

    @staticmethod
    def error_message(player, values):
        tag = values.get('chosen_initials', '').upper()
        if tag not in TAG2ZONE:
            return "Please enter one of the two-letter tags on the board."

    @staticmethod
    def before_next_page(player, timeout_happened):
        assign_payoff(player, player.chosen_initials.upper())

# ─── Shared pages ────────────────────────────────────────────
class Results(Page):
    @staticmethod
    def vars_for_template(player):
        return dict(total_points=player.total_points)


class Payoff(Page):
    @staticmethod
    def is_displayed(player):
        return player.round_number == C.NUM_ROUNDS

    @staticmethod
    def vars_for_template(player):
        rnd            = random.randrange(1, 200)
        final_points   = player.total_points
        bonus_amount   = C.bonus_pay if final_points > rnd else 0

        player.total_payoff   = C.base_pay + bonus_amount
        player.received_bonus = bonus_amount > 0
        player.end_time       = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # time in minutes
        start_dt = datetime.strptime(player.start_time, '%Y-%m-%d %H:%M:%S')
        end_dt   = datetime.strptime(player.end_time, '%Y-%m-%d %H:%M:%S')
        player.total_time = (end_dt - start_dt).total_seconds() / 60

        return dict(
            total_payoff   = player.total_payoff,
            received_bonus = player.received_bonus,
            bonus_amount   = bonus_amount,
            final_points   = final_points,
            start_time     = player.start_time,
            end_time       = player.end_time,
            total_time     = player.total_time,
        )

# ─────────────────────────────────────────────────────────────
# 8.  PAGE SEQUENCE
# ─────────────────────────────────────────────────────────────
page_sequence = [
    Intro,
    Instructions,
    avg_nozones,     # displayed only if condition == 'random_grid'
    AvgZones,        # displayed only if condition == 'avg_zones'
    Results,
    Payoff,
]
