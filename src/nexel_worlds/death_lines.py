"""A line for a death, said to everyone (#383): the server picks one of the lines that fit the death (its cause, the
creature that bit by its kind, what was in hand, the food starved with, the water, the night), never the last death's,
and the death event carries which one ([pool, i]) and the item it names, no words (tests/test_event_refs.py): each
reader fills it in from LINES (the rules' table: the page's death.js; {name} the one who died, {who} who did it,
{item} / {Item} the item)."""

import random

LINES = {
    # by cause (sim/combat.py CAUSES; admin and dev: "struck")
    "killed": ["{who} will tell this story differently than {name} would.", "{who} says what happened to {name} was an accident. {who} is smiling.",
               "{name} and {who} had a disagreement. {who} won it.", "{who} waved. {name} should have waved back faster.",
               "{name}'s friendship with {who}: under review.", "Remember {who}. {name} certainly will."],
    "bitten": ["Something with teeth had a better day than {name}.", "Nature: one. {name}: nil.",
               "It looked friendlier from further away, {name} would like everyone to know.", "{name} was, briefly, a snack.",
               "Not everything that grows here wants a hug. {name} checked."],
    "burnt": ["{name} got a little too close to the cooking.", "The hob was hot. Hobs usually are. {name} knows now.",
              "{name}: well done. Not the good kind.", "Somebody's hob. Somebody's fault. {name}'s problem."],
    "fell": ["The ground was exactly where {name} left it.", "Gravity remains undefeated. {name} does not.",
             "{name} jumped just fine. Landing is a separate skill.", "That was more down than {name} planned.",
             "{name} checked the drop. The drop checked back.", "The view up there was lovely. The bottom, {name} reports, less so."],
    "starvation": ["{name} forgot one small thing: lunch.", "{name}'s stomach filed a complaint. Then it filed everything.",
                   "Busy, busy, busy, hungry, gone. Goodbye, {name}.", "A meal a day would have kept {name} around.",
                   "Next time, {name} brings a snack."],
    "fire": ["{name}: toasty. Too toasty.", "Fire looks cozy. {name} found out what it looks like from inside.",
             "{name} was standing in the warm part.", "Hot tip for {name}: don't stand in fire.", "{name} caught fire. It caught {name} back."],
    "struck": ["The sky had opinions about {name}.", "{name} was struck down from on high. Somebody up there pressed a button.",
               "Nobody saw that coming. Not even {name}."],
    # bitten, by the creature's kind (sim/entities.py CREATURES that bite)
    "tusker": ["The tusker had right of way. {name} did not.", "{name} stood between a tusker and wherever the tusker meant to go.",
               "Tusks: two. {name}'s plans: none."],
    "pincer": ["{name} was pinched, and pinched, and pinched again. Pincers are thorough.",
               "Small, sideways, and absolutely sure of itself. Sorry, {name}.", "The pincer will be telling the other pincers about {name}."],
    "strawman": ["The strawman did its job. {name} was the crow.", "Stuffed with straw, full of opinions, done with {name}.",
                 "A strawman is best kept in front. {name} kept it behind."],
    "grumblestump": ["That stump was not a stump, {name}.", "{name} rested by the wrong stump.",
                     "The grumblestump grumbled at {name}, then got to the point."],
    "snapbloom": ["{name} stopped to smell the flowers. The flowers stopped {name}.", "Pretty petals. Prettier teeth. Poor {name}.",
                  "Never lean in to sniff a snapbloom. {name} leaned in."],
    "wyrm": ["The wyrm barely woke up for {name}.", "Long, scaly, and in no mood for {name}.", "{name} found the wyrm. The wyrm found {name} first."],
    "mossback": ["The mossback moved. Nobody will believe {name}.", "Slow is not the same as harmless, {name} learned.",
                 "Under all that moss: a temper. {name} found it."],
    "nyxwing": ["The night has wings. Tonight, the wings were busy with {name}.", "{name} looked up. The nyxwing looked down.",
                "Dark, sudden, and very pleased with itself. {name}, less so."],
    "sporeling": ["{name} was beaten by a mushroom. Tell everyone.", "The sporeling was small. It made up for it in persistence, {name} found.",
                  "{name}: death by a thousand spores."],
    # what was in hand (any death but a starving one or one from the sky; empty hands only when somebody did it)
    "hand_none": ["{name} faced it with bare hands. Brave. Not clever, but brave.", "{name} brought nothing to this, and it showed."],
    "hand_weapon": ["{name}'s {item} watched the whole thing.", "{name} had the {item} out. Next time, swing it.",
                    "{name}'s {item} lies where {name} fell, unswung."],
    "hand_tool": ["{name}'s {item} is a tool, not a plan.", "{name} brought the {item} to a fight. Wrong kind of fight."],
    "hand_food": ["At least {name}'s {item} made it.", "{name} died holding the {item}. Priorities."],
    "hand_other": ["{name} clutched the {item} to the very end.", "The {item} is fine, thanks for asking. {name} is not."],
    # starved with food on you; where and when
    "fed": ["{name} starved with {item} in the pocket. Bold.", "The {item} was right there, {name}.", "{Item}: carried by {name}, admired, never eaten."],
    "water": ["At least {name} will wake up dry.", "Swimming was the easy part for {name}.", "The fish are being very quiet about {name}."],
    "night": ["Nothing good happens after dark. {name}, for instance.", "{name} should have been in bed by now.", "The stars saw everything, {name}."],
}


def fitting(code, kind=None, held=None, dropped=None, water=False, night=False, *, food, weapons, tools):
    """Every line that fits a death: [(pool, i, item)]."""
    code = "struck" if code in ("admin", "dev") else code
    out = []

    def add(pool, item=None):
        out.extend((pool, i, item) for i in range(len(LINES[pool])))
    add(code if code in LINES else "fell")
    if code == "bitten" and kind in LINES:
        add(kind)
    if code == "starvation":
        f = next((n for n in (dropped or {}) if n in food), None)
        if f:
            add("fed", f)
    elif code != "struck" and (held or code in ("killed", "bitten")):
        add("hand_" + ("none" if not held else "weapon" if held in weapons else "tool" if held in tools or held in ("hoe", "watering_can")
                       else "food" if held in food else "other"), held)
    if water:
        add("water")
    if night:
        add("night")
    return out


def pick(rng: random.Random, last, **situation):
    """One of them, never `last` (the last death's [pool, i]) when there is another: (pool, i, item)."""
    every = fitting(**situation)
    rest = [c for c in every if list(c[:2]) != list(last or [])] or every
    return rng.choice(rest)


def say(pool, i, *, name, who="someone", item=None):
    """The line in words (the page's death.js does the same from the rules' table)."""
    it = (item or "").replace("_", " ")
    return LINES[pool][i].format(name=name, who=who, item=it, Item=it[:1].upper() + it[1:])
