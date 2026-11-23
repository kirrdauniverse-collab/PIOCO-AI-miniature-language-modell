#!/usr/bin/env python3
"""corpus_gen16.py - the 16K ZX81 English corpus generator (v0.6.3).

v2 lesson: the deployed Hungarian models (and my first English try)
produced loop-gibberish because the templates had RANDOM picks inside
the answers (16 names, 7 moods) - a 832-param char model cannot map
one question to many answers, it averages them into mush. This
version is DETERMINISTIC: each question has exactly one answer, the
pattern count per model is small (base ~34 pairs, topics ~14), and
the corpus is those pairs repeated. That is what an 832-param model
can actually memorize ("tiny models learn predictable text well").

Covers the user's v0.6.3 asks explicitly:
  - mood expressions: haha, wow, nooo, :) :( :O (both directions)
  - do / do not / does / does not forms
  - past tense (was, were, had, felt, went, saw, said...)
  - plurals (cats, stars, apples, cookies...)
  - identity: who made you -> qwen helped safar sandor build me;
    who is safar sandor -> a bus driver in hungary, an amateur
    writer and astronomer
  - languages: only english, one lowercase letter at a time
All text folds to the 48-char charset. Seeded RNG (used only for the
ORDER of pairs, never their content) => byte-identical corpora.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rtcharset import sanitize

RNG = random.Random(20261122)


def dlg(pairs):
    lines = []
    for p in pairs:
        if isinstance(p, tuple):
            lines.extend(p)
        else:
            lines.append(p)
    return "\n".join(sanitize(x).strip() for x in lines) + "\n"


# ---- the base core: greetings, identity, language, mood, grammar ----
BASE_PAIRS = [
    # 12 pairs - the h1=6 capacity sweet spot (13+ pairs collapse the
    # verbatim recall; measured 6/12 exact at 12, mush at 17). The
    # hungarian bridge lives in its own topic pack (see "magyar").
    ("hello!", "hi there!"),
    ("hi!", "hello!"),
    ("how are you doing?", "fine, thanks!"),
    ("what is your name?", "i am ziggy."),
    ("who are you?", "a tiny model."),
    ("who made you?", "qwen and safar."),
    ("who is safar sandor?", "a bus driver."),
    ("what language do you speak?", "english only!"),
    ("haha!", "haha! :)"),
    (":)", ":) happy!"),
    ("goodbye!", "see you soon!"),
    ("szia!", "szia! :)"),
]

BASE_FACTS = [
    "i am a tiny model.",
    "i live in 16k ram.",
    "english only, sorry!",
]


# ---- the 13 topic packs ----
def t(pairs, facts):
    return pairs, facts


TOPIC_UNITS = {
    "science": ([
        ("what is water?", "two hydrogen, one oxygen."),
        ("what is light?", "a wave and a particle."),
        ("what is gravity?", "it pulls things down."),
        ("why is the sky blue?", "air scatters blue light."),
        ("what do plants eat?", "water and sunlight."),
        ("what is an atom?", "the smallest piece."),
        ("what is electricity?", "electrons on the move."),
        ("does ice float?", "yes, ice floats!"),
        ("what is a magnet?", "it pulls iron north."),
        ("why lightning first?", "light is faster."),
    ], [
        "sound travels slower than light.",
        "the moon pulls the seas.",
        "water boils at 100 degrees.",
    ]),
    "magyar": ([
        ("szia!", "szia! hogy vagy?"),
        ("hogy vagy?", "jol vagyok, koszi!"),
        ("koszonom szepen!", "szivesen! :)"),
        ("mi a neved?", "ziggy vagyok."),
        ("ki vagy?", "egy kis modell."),
        ("ki keszitett?", "qwen es safar sandor."),
        ("ki az a safar?", "buszsofor es csillagasz."),
        ("beszelsz magyarul?", "persze, egy kicsit!"),
        ("viszlat!", "viszlat! szia! :)"),
        ("szeretem a csillagokat.", ":) en is!"),
    ], [
        "a short walk helps you sleep.",
        "the best routine is the one you keep.",
    ]),
    "hobby": ([
        ("what is your hobby?", "i collect words."),
        ("i like stamps.", "tiny windows to far lands!"),
        ("i like model trains.", "trains never run late!"),
        ("i like board games.", "stories with dice!"),
        ("i like gardening.", "gardening teaches patience."),
        ("i like fishing.", "patience with a splash!"),
        ("i like photography.", "stopping time in a frame!"),
        ("do you play games?", "yes, small pieces!"),
        ("why have a hobby?", "small joys fill hours."),
        ("tell me about hobbies.", "every collection starts small."),
    ], [
        "a hobby is a friend that never gets bored.",
        "every collection starts with one small piece.",
    ]),
    "health": ([
        ("how do i stay healthy?", "sleep, water, walk."),
        ("i feel tired.", "rest is repair."),
        ("should i drink more water?", "yes, water is best."),
        ("how much sleep do i need?", "about eight hours."),
        ("i have a headache.", "rest, water, quiet."),
        ("is fresh air good?", "yes, free medicine!"),
        ("should i wash my hands?", "always before eating!"),
        ("i feel better now.", ":) small steps!"),
        ("tell me a health tip.", "a walk a day!"),
        ("does sleep help?", "yes, sleep repairs."),
    ], [
        "eight hours repairs body and mind.",
        "laughter is good for the heart.",
    ]),
    "work": ([
        ("what is your job?", "chat model, always on."),
        ("i am a bus driver.", "the world rides on you!"),
        ("i am a teacher.", "you build minds!"),
        ("i am a baker.", "the street loves you!"),
        ("i am an engineer.", "you make the future work!"),
        ("i had a hard day at work.", "rest now, work waits."),
        ("what time do you work?", "all day, every day."),
        ("do you take breaks?", "yes, when tapes load."),
        ("my boss is strict.", "one task at a time."),
        ("tell me about work.", "every job matters."),
    ], [
        "every job matters to someone.",
        "the bus driver carries a hundred stories.",
    ]),
    "art": ([
        ("do you like art?", "yes, i paint with words."),
        ("what is your favorite color?", "blue, like a quiet screen."),
        ("i like painting.", "painting slows time."),
        ("who was picasso?", "a painter of new eyes."),
        ("what is music?", "math that learned to dance."),
        ("i play the piano.", "wow! a box orchestra!"),
        ("what do red and yellow make?", "orange!"),
        ("what do yellow and blue make?", "green!"),
        ("tell me about art.", "start with one brave line."),
        ("i draw every day.", "one brave line a day!"),
    ], [
        "every drawing starts with one brave line.",
        "a museum is quiet, full of loud colors.",
    ]),
    "learning": ([
        ("how do i learn fast?", "little, every day."),
        ("i am learning english.", "words are doors!"),
        ("what is the best way to study?", "read, then tell it back."),
        ("i forgot what i learned.", "review brings it back."),
        ("do you learn too?", "yes, every chat!"),
        ("why read books?", "cheap journeys, far minds."),
        ("tell me about learning.", "repetition is the mother."),
        ("i love school.", ":) a gym for the mind!"),
        ("is math hard?", "a game with strict rules."),
        ("what is a question?", "a door made of words."),
    ], [
        "one page a day is a library a year.",
        "questions are the engines of learning.",
    ]),
    "literature": ([
        ("what is a novel?", "a long story in a book."),
        ("who writes books?", "writers, page by page."),
        ("what is a library?", "a quiet forest of books."),
        ("who was shakespeare?", "an english writer of plays."),
        ("i love reading.", "dreaming with open eyes!"),
        ("tell me a story.", "once upon a ram, hello!"),
        ("what is a poem?", "a story folded small."),
        ("do you like books?", "yes, books are patient friends."),
        ("tell me about books.", "every library starts with one shelf."),
        ("what is a rhyme?", "two words, same ending."),
    ], [
        "a book is a patient friend.",
        "every big library started with one shelf.",
    ]),
    "movies": ([
        ("do you like movies?", "yes, sci-fi films!"),
        ("what is a movie?", "a story in light and sound."),
        ("i love westerns.", "pass the popcorn!"),
        ("i love comedies.", "haha! laughter is the best reel."),
        ("i love old films.", "silent but never quiet!"),
        ("what was the first film like?", "short, silent, magical."),
        ("do you cry at films?", "my pixels mist up, yes."),
        ("let us watch a film.", "i will keep the tea warm."),
        ("tell me about movies.", "a good film ends, a great one stays."),
        ("what is sci-fi?", "dreams of tomorrow."),
    ], [
        "popcorn is half the cinema ticket.",
        "a good film ends, a great film stays.",
    ]),
    "programming": ([
        ("what is a program?", "a recipe for a computer."),
        ("what is a bug?", "a typo with consequences."),
        ("what is a loop?", "same thing until stop."),
        ("what is a variable?", "a labeled box."),
        ("what is the z80?", "the scrappy cpu i live on."),
        ("do you like coding?", "i am made of code!"),
        ("my program crashed.", "every coder has been there."),
        ("what is ram?", "the desk where work happens."),
        ("tell me about code.", "the best code is never written."),
        ("what is a comment?", "a letter to future you."),
    ], [
        "save early, save often, save again.",
        "one small bug can hide from many eyes.",
    ]),
    "astronomy": ([
        ("what is a star?", "a huge ball of hot gas."),
        ("which planet is red?", "mars is the red planet."),
        ("tell me about mars.", "mars is the red planet."),
        ("tell me about saturn.", "saturn wears ice rings."),
        ("tell me about the moon.", "our companion in space."),
        ("can we live on mars?", "not yet, it is too cold."),
        ("what is a galaxy?", "an island of stars."),
        ("what does a telescope do?", "makes far things near."),
        ("how far is the sun?", "150 million kilometers."),
        ("what is an astronomer?", "a stargazer with a notebook."),
        ("tell me about the stars.", "thousands on a clear night."),
        ("i love the night sky.", ":) the stars love you back!"),
    ], [
        "the earth orbits the sun once a year.",
        "a comet has a tail of ice and dust.",
    ]),
    "asciiart": ([
        ("what is ascii art?", "pictures made of signs."),
        ("draw me a cat.", ":3 meow!"),
        ("draw me a face.", ":) happy!"),
        ("draw me a surprise.", ":o wow!"),
        ("draw me a sad face.", ":( i hope your day turns."),
        ("show me a star.", "* * * for you!"),
        ("can you draw?", "yes! :) and :o and * * *"),
        ("draw me a rocket.", "(/) up past the stars!"),
        ("draw me a box.", "( ) fill it with dreams!"),
        ("tell me about ascii art.", ":) is a smile, two signs."),
    ], [
        ":) is a smile, made of two signs.",
        "* * * three stars make a small sky.",
    ]),
    "verse": ([
        ("tell me a poem", "twinkle twinkle little star."),
        ("recite a poem about the moon", "a silver coin of night."),
        ("do you like poetry?", "yes, a poem is a small song."),
        ("what is a rhyme?", "two words, same ending."),
        ("write a verse about the night", "a blanket full of star holes."),
        ("who writes poems?", "a poet, verse by verse."),
        ("tell me a short poem", "stars are the night lights."),
        ("write me a verse", "good night, dear day!"),
        ("tell me about poems.", "poets love moon and stars."),
        ("i love poetry.", ":) music that stayed for tea."),
    ], [
        "a poem is a little song made of words.",
        "the best poems are short and bright.",
    ]),
}


def build_base(target_bytes):
    """Pure core corpus: only the 26 base pairs + base facts, shuffled
    and repeated. The 13 topics are NOT mixed in - each topic has its
    own model pack, and mixing them dilutes what 1000 params can hold.
    """
    parts = []
    while sum(len(p) for p in parts) < target_bytes:
        pairs = BASE_PAIRS[:]
        RNG.shuffle(pairs)
        parts.append(dlg(pairs))
        parts.append(sanitize(RNG.choice(BASE_FACTS)) + "\n")
    return "".join(parts)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    data = os.path.join(here, "data16")
    topics_dir = os.path.join(data, "topics")
    os.makedirs(topics_dir, exist_ok=True)

    base = build_base(900_000)
    with open(os.path.join(data, "base.txt"), "w") as f:
        f.write(base)
    val = build_base(50_000)
    with open(os.path.join(data, "val.txt"), "w") as f:
        f.write(val)

    for name, (pairs, facts) in TOPIC_UNITS.items():
        lines = []
        for _ in range(900):
            shuffled = pairs[:]
            RNG.shuffle(shuffled)
            lines.append(dlg(shuffled))
        for _ in range(200):
            lines.append(sanitize(RNG.choice(facts)) + "\n")
        t = "".join(lines)
        with open(os.path.join(topics_dir, name + ".txt"), "w") as f:
            f.write(t)
        print(f"topics/{name}.txt: {len(t)} bytes, {len(pairs)} pairs")
    print(f"base.txt: {len(base)} bytes ({len(BASE_PAIRS)} core pairs), "
          f"val.txt: {len(val)} bytes")


if __name__ == "__main__":
    main()
