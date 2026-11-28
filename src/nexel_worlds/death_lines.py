"""A line for a death, said to everyone (#383): the server picks one of the lines that fit the death (its cause, the
creature that bit by its kind, what was in hand, the food starved with, the water, the night), never the last death's,
and the death event carries which one ([pool, i]) and the item it names, no words (tests/test_event_refs.py): each
reader fills it in from LINES (the rules' table: the page's death.js; {name} the one who died, {who} who did it,
{item} / {Item} the item)."""

import random

LINES = {
    # by cause (sim/combat.py CAUSES; admin and dev: "struck")
    "killed": ["{who} and {name} built a house. {who} kept it.", "In {who}'s defence, {name} was right there.",
               "{who} says {name} started it. No reply.", "{name} asked {who} for the way out. Got it."],
    "bitten": ["{name} tried to pet it. It had teeth.", "{name} was eaten a little. Then a lot.",
               "{name} went looking for wildlife and found it."],
    "burnt": ["{name} checked what the hob was cooking: {name}.", "{name} hugged a hob. Hobs are not huggers.",
              "Recipe: one hob, one {name}. Serves nobody."],
    "fell": ["{name} took the stairs. All of them. At once.", "{name} wanted to see the bottom. Saw it.",
             "{name} forgot to build the ladder first.", "{name} trusted the ground to be closer."],
    "starvation": ["{name} was too busy building a farm to eat.", "{name} skipped breakfast, then lunch, then everything.",
                   "{name} starved in a world made largely of berries.", "{name}'s last words: \"just one more block.\""],
    "fire": ["{name} checked if the fire was hot. Confirmed.", "{name} mistook the fire for a very warm rug.",
             "{name} got cozy by the fire. Then too cozy. Then fire."],
    "struck": ["{name} annoyed someone with a keyboard.", "The sky deleted {name}. No reason given.",
               "Someone upstairs is having a day. Sorry, {name}."],
    # bitten, by the creature's kind (sim/entities.py CREATURES that bite)
    "tusker": ["{name} tried to ride a tusker. The tusker said no.", "{name} was in a tusker's way. Briefly.",
               "{name} asked a tusker to stop. Tuskers can't."],
    "pincer": ["{name} lost a fight to something the size of a shoe.", "The pincer took {name} apart. Pincers love that.",
               "{name} underestimated the pincer. Everyone does. Once."],
    "strawman": ["{name} was killed by a scarecrow. Crows cheered.", "{name} punched a strawman. It punched back.",
                 "The strawman never moves. It moved for {name}."],
    "skeleton": ["{name} heard the rattle and lingered to listen.", "A skeleton swiped {name}. Its eyes, the last light.",
                 "{name} met a skeleton at night. Soon, two."],
    "redknee": ["{name} saw it rear up and watched.", "{name} is wrapped in silk, for later.",
                "A redknee pounced. {name} was the landing."],
    "grumblestump": ["{name} sat on a stump. The stump stood up.", "{name} tried to chop a grumblestump. It chopped back.",
                     "The grumblestump grumbled at {name}. Then acted."],
    "snapbloom": ["{name} stopped to smell a flower. It stopped {name}.", "{name} picked a flower. The flower picked back.",
                  "Killed by a flower. {name} would like this kept quiet."],
    "wyrm": ["{name} poked a sleeping wyrm. It's awake now.", "{name} called the wyrm \"just a big worm\". It heard.",
             "{name} woke the wyrm. The wyrm had breakfast."],
    "mossback": ["{name} thought the mossback was a hill. Climbed it.", "The mossback is slow. {name} was slower, apparently.",
                 "{name} lost a race to a mossback. Then the rest."],
    "nyxwing": ["{name} looked up at a star. It had wings.", "The dark grew wings and took {name}.",
                "{name} waited up all night to see the nyxwing. Saw it."],
    "sporeling": ["{name} was killed by a mushroom. A walking one.", "{name} lost to a sporeling. It's telling everyone.",
                  "{name} tried to eat a sporeling. It ate first."],
    # what was in hand (any death but a starving one or one from the sky; empty hands only when somebody did it)
    "hand_none": ["{name} brought fists to this. Just fists.", "{name} had nothing in hand but hope."],
    "hand_weapon": ["{name} died holding a perfectly good {item}.", "{name}'s {item} is on the ground now, still clean."],
    "hand_tool": ["{name} tried the {item}. Not that kind of problem.", "{name} fought back with the {item}. Uselessly."],
    "hand_food": ["{name} died holding the {item}. Not one bite.", "{name}'s last meal: almost the {item}."],
    "hand_other": ["{name} went down clutching the {item}. Worth it?", "{name} faced death with the {item}. Bold choice."],
    # starved with food on you; where and when
    "fed": ["{name} starved carrying {item}. A mystery.", "{name} saved the {item} for later. No later."],
    "water": ["{name} took a swim. The swim took {name}.", "{name} died wet. Will wake dry. Small mercies."],
    "night": ["{name} was out after dark. The dark noticed.", "{name} should have gone to bed. The bed was right there."],
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
