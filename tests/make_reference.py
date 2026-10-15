"""Generate reference values for the JS rating engine using the Python
`trueskill` package (pip install trueskill). Writes tests/reference.json.

Run:  python tests/make_reference.py
"""
import json
import os
import trueskill
from trueskill import Rating, TrueSkill

MU, SIGMA = 25.0, 25.0 / 3


def env_for(draw_probability):
    return TrueSkill(mu=MU, sigma=SIGMA, beta=SIGMA / 2, tau=SIGMA / 100,
                     draw_probability=draw_probability)


def case(name, teams, ranks, draw_probability=0.10):
    env = env_for(draw_probability)
    groups = [tuple(Rating(mu, sigma) for mu, sigma in team) for team in teams]
    out = env.rate(groups, ranks=ranks)
    return {
        "name": name,
        "drawProbability": draw_probability,
        "ranks": ranks,
        "teams": [[{"mu": mu, "sigma": sigma} for mu, sigma in team] for team in teams],
        "expected": [[{"mu": r.mu, "sigma": r.sigma} for r in team] for team in out],
    }


D = (MU, SIGMA)
cases = [
    case("1v1 win (defaults)", [[D], [D]], [0, 1]),
    case("1v1 draw (defaults)", [[D], [D]], [0, 0]),
    case("2v2 win", [[D, D], [D, D]], [0, 1]),
    case("3v2 uneven, bigger team wins", [[D, D, D], [D, D]], [0, 1]),
    case("2v3 uneven, smaller team wins", [[D, D], [D, D, D]], [0, 1]),
    case("3-team free-for-all (2v2v2), unsorted input",
         [[D, D], [D, D], [D, D]], [1, 0, 2]),
    case("3-team, top two tied", [[D, D], [D, D], [D, D]], [0, 0, 1]),
    case("3-team, bottom two tied", [[D, D], [D, D], [D, D]], [0, 1, 1]),
    case("3-team, all tied", [[D], [D, D], [D]], [0, 0, 0]),
    case("4-team mixed ratings and sizes",
         [[(30, 4), (22, 6)], [(25, 8.333)], [(18, 3), (27, 5), (24, 7)], [(26, 2)]],
         [2, 0, 1, 1]),
    case("1v1 upset with established ratings",
         [[(20, 2.5)], [(32, 2.0)]], [0, 1]),
    case("2v2 draw, unequal ratings, p=0.2",
         [[(28, 3), (24, 5)], [(21, 6), (23, 4)]], [0, 0], draw_probability=0.2),
    case("5-team, three-way tie for first, mixed ratings",
         [[(22, 3), (20, 2)], [(26, 5)], [(24, 6), (25, 4), (21, 7)], [(19, 2.5)], [(28.5, 6), (24.6, 7)]],
         [0, 3, 4, 0, 0]),
    case("3v2 uneven, established ratings, smaller wins",
         [[(26, 3), (23, 4), (21, 5)], [(27, 2.5), (25, 3.5)]], [1, 0]),
]

# ---------------------------------------------------------------------------
# End-to-end replay reference: margin factor + weighted update, computed
# independently in Python using the same spec as the app.
# ---------------------------------------------------------------------------
settings = {"mu": MU, "sigma": SIGMA, "beta": SIGMA / 2, "tau": SIGMA / 100,
            "drawProbability": 0.10, "minMargin": 0.75, "maxMargin": 1.25,
            "maxWeight": 1.5, "sigmaFloor": 0.5}
game_types = [
    {"id": "warmup", "name": "Warmup game", "weight": 0.3, "target": 5},
    {"id": "mini", "name": "Mini", "weight": 0.6, "target": 7},
    {"id": "full", "name": "Full field 7s", "weight": 1.0, "target": 15},
    {"id": "drill", "name": "Drill", "weight": 0.4, "target": 10},
]
players = [{"id": "p%d" % i, "name": "P%d" % i, "active": True} for i in range(1, 9)]
games = [
    # deliberately out of chronological order in the list
    {"id": "g3", "date": "2026-09-02", "createdAt": 3, "typeId": "full", "scoringTarget": 15,
     "teams": [{"playerIds": ["p1", "p3", "p5", "p7"], "score": 15}, {"playerIds": ["p2", "p4", "p6", "p8"], "score": 13}]},
    {"id": "g1", "date": "2026-09-01", "createdAt": 1, "typeId": "warmup", "scoringTarget": 5,
     "teams": [{"playerIds": ["p1", "p2", "p3", "p4"], "score": 5}, {"playerIds": ["p5", "p6", "p7", "p8"], "score": 1}]},
    {"id": "g2", "date": "2026-09-01", "createdAt": 2, "typeId": "mini", "scoringTarget": 7,
     "teams": [{"playerIds": ["p1", "p5"], "score": 7}, {"playerIds": ["p2", "p6", "p8"], "score": 7}, {"playerIds": ["p3", "p4", "p7"], "score": 2}]},
    {"id": "g4", "date": "2026-09-02", "createdAt": 4, "typeId": "drill", "scoringTarget": 10,
     "teams": [{"playerIds": ["p2", "p3"], "score": 12}, {"playerIds": ["p6", "p7"], "score": 4}]},  # bonus points
    {"id": "g5", "date": "2026-09-03", "createdAt": 5, "typeId": "full", "scoringTarget": 15,
     "teams": [{"playerIds": ["p1", "p2", "p3"], "score": 9}, {"playerIds": ["p4", "p5", "p6"], "score": 9}]},  # draw
    {"id": "g6", "date": "2026-09-03", "createdAt": 6, "typeId": "mini", "scoringTarget": 7,
     "teams": [{"playerIds": ["p8"], "score": 3}, {"playerIds": ["p7", "p6"], "score": 7}, {"playerIds": ["p1", "p4"], "score": 5}, {"playerIds": ["p2", "p3", "p5"], "score": 0}]},
    {"id": "g7", "date": "2026-09-04", "createdAt": 7, "typeId": "full", "scoringTarget": 13,  # per-game target override
     "teams": [{"playerIds": ["p1", "p2", "p3", "p4", "p5"], "score": 4}, {"playerIds": ["p6", "p7", "p8"], "score": 13}]},
]


def py_replay(games):
    type_by_id = {t["id"]: t for t in game_types}
    ratings = {p["id"]: (MU, SIGMA) for p in players}
    env = env_for(settings["drawProbability"])
    ordered = sorted(games, key=lambda g: (g["date"], g["createdAt"], g["id"]))
    for g in ordered:
        scores = [t["score"] for t in g["teams"]]
        ranks = [sum(1 for s2 in scores if s2 > s) for s in scores]
        if all(s == scores[0] for s in scores):
            mf = 1.0
        else:
            top, bottom = max(scores), min(scores)
            m = (top - bottom) / max(g["scoringTarget"], top)
            m = min(1.0, max(0.0, m))
            mf = settings["minMargin"] + (settings["maxMargin"] - settings["minMargin"]) * m
        w = min(settings["maxWeight"], max(0.0, type_by_id[g["typeId"]]["weight"] * mf))
        groups = [tuple(Rating(*ratings[pid]) for pid in t["playerIds"]) for t in g["teams"]]
        out = env.rate(groups, ranks=ranks)
        for t, team in zip(g["teams"], out):
            for pid, r in zip(t["playerIds"], team):
                om, os_ = ratings[pid]
                nm = om + w * (r.mu - om)
                ns = max(settings["sigmaFloor"], os_ + w * (r.sigma - os_))
                ratings[pid] = (nm, ns)
    return {pid: {"mu": m, "sigma": s} for pid, (m, s) in ratings.items()}


replay = {
    "data": {"version": 1, "settings": settings, "gameTypes": game_types,
             "players": players, "games": games},
    "expected": py_replay(games),
    "expectedWithoutG4": py_replay([g for g in games if g["id"] != "g4"]),
}

out = {"generatedBy": "trueskill %s" % trueskill.__version__, "cases": cases, "replay": replay}
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference.json")
with open(path, "w") as fh:
    json.dump(out, fh, indent=1)
print("wrote", path)
print("1v1 win:", cases[0]["expected"])
