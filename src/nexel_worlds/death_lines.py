"""A line for a death, said to everyone (#383): the server picks one of the lines that fit the death (its cause, the
creature that bit by its kind, what was in hand, the food starved with, the water, the night), never the last death's,
and the death event carries which one ([pool, i]) and the item it names, no words (tests/test_event_refs.py): each
reader fills it in from LINES (the rules' table: the page's death.js; {name} the one who died, {who} who did it,
{item} / {Item} the item)."""

import random

LINES = {
    # by cause (sim/combat.py CAUSES; admin and dev: "struck")
    "killed": ["{who} and {name} were building something together. Now it's all {who}'s.", "In {who}'s defence, {name} was right there.",
               "{who} says {name} started it. {name} would disagree, but can't right now.", "{name} asked {who} for directions. {who} pointed down."],
    "bitten": ["{name} tried to pet it. It had other plans, and several teeth.", "{name} was eaten a little. Then a lot.",
               "{name} went looking for wildlife and found it."],
    "burnt": ["{name} wanted to see what the hob was cooking. The answer: {name}.", "{name} hugged a hob. Hobs are not huggers.",
              "Recipe: one hob, one {name}. Serves nobody."],
    "fell": ["{name} took the stairs. All of them. At once.", "{name} jumped to see what was down there. The ground, mostly.",
             "{name} forgot to build the ladder first.", "{name} trusted the ground to be closer."],
    "starvation": ["{name} was too busy building a farm to eat.", "{name} skipped breakfast, then lunch, then everything.",
                   "{name} starved in a world made largely of berries.", "{name}'s last words: \"just one more block.\""],
    "fire": ["{name} checked if the fire was hot. Confirmed.", "{name} mistook the fire for a very warm rug.",
             "{name} got cozy by the fire. Then too cozy. Then fire."],
    "struck": ["{name} annoyed someone with a keyboard.", "The sky deleted {name}. No reason given.",
               "{name} was struck down from above. Someone upstairs is having a day."],
    # bitten, by the creature's kind (sim/entities.py CREATURES that bite)
    "tusker": ["{name} tried to ride the tusker. The tusker declined, firmly.", "{name} was in the tusker's way. The tusker is never in anyone's way.",
               "{name} asked the tusker to stop. Tuskers don't have that button."],
    "pincer": ["{name} lost a fight to something the size of a shoe.", "The pincer took {name} apart. Pincers love taking things apart.",
               "{name} underestimated the pincer. Everyone does. Once."],
    "strawman": ["{name} was killed by a scarecrow. The crows are thrilled.", "{name} punched the strawman. The strawman punched back. Nobody saw that coming.",
                 "The strawman hasn't moved in years. Today it moved, for {name}."],
    "grumblestump": ["{name} sat on a stump. The stump stood up.", "{name} tried to chop the grumblestump for wood. The grumblestump tried {name} back.",
                     "The grumblestump grumbled about {name} all day. Now it's quiet."],
    "snapbloom": ["{name} stopped to smell the flowers. The flowers stopped {name}.", "{name} picked a flower. The flower picked back.",
                  "Killed by a flower. {name} would like this kept quiet."],
    "wyrm": ["{name} poked the sleeping wyrm, just to check. It is now awake.", "{name} called the wyrm \"just a big worm\". It heard.",
             "{name} found the wyrm's nap. The wyrm found {name}'s everything."],
    "mossback": ["{name} thought the mossback was a hill. Climbed it.", "The mossback is slow. {name} was slower, apparently.",
                 "{name} lost a race to a mossback. Then lost everything else."],
    "nyxwing": ["{name} looked up at the stars. One of them looked back, and had wings.", "The nyxwing came down from the dark for exactly one thing: {name}.",
                "{name} waited up all night to see the nyxwing. Saw it."],
    "sporeling": ["{name} was killed by a mushroom. A walking one, but still.", "{name} lost to a sporeling. The sporeling is telling everyone.",
                  "{name} tried to eat a sporeling. The sporeling had the same idea."],
    # what was in hand (any death but a starving one or one from the sky; empty hands only when somebody did it)
    "hand_none": ["{name} brought fists to this. Just fists.", "{name} had nothing in hand but hope."],
    "hand_weapon": ["{name} died holding a perfectly good {item}.", "{name}'s {item} is on the ground now, still clean."],
    "hand_tool": ["{name} tried to fix it with the {item}. Not that kind of problem.", "{name} fought back with the {item}. Bravely. Uselessly."],
    "hand_food": ["{name} died holding the {item}. Didn't even get one bite.", "{name}'s last meal: almost the {item}."],
    "hand_other": ["{name} went down clutching the {item}. Worth it, probably.", "{name} chose to face death with the {item}. An interesting choice."],
    # starved with food on you; where and when
    "fed": ["{name} starved with {item} in the pocket. A tragedy and a mystery.", "{name} was saving the {item} for later. There was no later."],
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
