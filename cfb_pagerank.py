#!/usr/bin/env python3
"""Rank college football teams with PageRank.

Each completed game adds an edge loser -> winner, so "rank" flows toward
teams that beat teams who beat other teams.

Data: ESPN's public scoreboard API (no key required).

Usage: python3 cfb_pagerank.py [year] [--fcs] [--top N]
By Ryan Jones
https://www.ryanmjones.com
"""
import argparse
import json
import urllib.request
from collections import defaultdict

# Using the free ESPN API for as long as it will let me.

URL = ("https://site.api.espn.com/apis/site/v2/sports/football/college-football/"
       "scoreboard?dates={year}&seasontype={stype}&week={week}&groups={group}&limit=500")


def fetch(year, stype, week, group):
    with urllib.request.urlopen(URL.format(year=year, stype=stype, week=week, group=group)) as r:
        return json.load(r).get("events", [])


def load_games(year, group):
    """Return {game_id: (loser, winner, margin)} for all completed games."""
    games = {}
    # Regular season (seasontype=2) weeks, then postseason (seasontype=3).
    slots = [(2, w) for w in range(1, 17)] + [(3, 1)]
    for stype, week in slots:
        for ev in fetch(year, stype, week, group):
            comp = ev["competitions"][0]
            if not comp["status"]["type"]["completed"]:
                continue
            teams = comp["competitors"]
            if len(teams) != 2:
                continue
            w = next((t for t in teams if t.get("winner")), None)
            l = next((t for t in teams if not t.get("winner")), None)
            if not w or not l or w is l:
                continue  # ties / missing data
            margin = int(w["score"]) - int(l["score"])
            games[ev["id"]] = (l["team"]["displayName"], w["team"]["displayName"], margin)
    return games


def pagerank(edges, damping=0.85, iters=100):
    """edges: list of (src, dst, weight). Returns {node: score}."""
    nodes = {n for s, d, _ in edges for n in (s, d)}
    out_w = defaultdict(float)
    incoming = defaultdict(list)
    for s, d, w in edges:
        out_w[s] += w
        incoming[d].append((s, w))
    n = len(nodes)
    rank = {v: 1 / n for v in nodes}
    for _ in range(iters):
        # Undefeated teams have no out-edges; spread their rank evenly.
        sink = sum(rank[v] for v in nodes if out_w[v] == 0)
        rank = {
            v: (1 - damping) / n
            + damping * (sink / n + sum(rank[s] * w / out_w[s] for s, w in incoming[v]))
            for v in nodes
        }
    return rank


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("year", type=int, nargs="?", default=2025)
    ap.add_argument("--fcs", action="store_true", help="use FCS games instead of FBS")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--margin", action="store_true",
                    help="weight edges by margin of victory (capped at 28)")
    args = ap.parse_args()

    games = load_games(args.year, 81 if args.fcs else 80)
    edges = [(l, w, min(m, 28) if args.margin else 1) for l, w, m in games.values()]

    record = defaultdict(lambda: [0, 0])
    for l, w, _ in games.values():
        record[w][0] += 1
        record[l][1] += 1

    ranks = sorted(pagerank(edges).items(), key=lambda kv: -kv[1])
    print(f"{args.year} — {len(games)} games, {len(record)} teams\n")
    for i, (team, score) in enumerate(ranks[: args.top], 1):
        w, l = record[team]
        print(f"{i:>3}. {team:<35} {w:>2}-{l:<2}  {score * 1000:.2f}")


if __name__ == "__main__":
    main()
