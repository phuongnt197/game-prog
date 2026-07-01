from __future__ import annotations

import base64
import json
from typing import Any

from .harness import RESULT_PREFIX


def _world(
    width: int,
    height: int,
    start: list[int],
    goal: list[int],
    *,
    gems: list[list[int]] | None = None,
    walls: list[list[int]] | None = None,
    energy: int = 20,
    gem_values: dict[str, int] | None = None,
    cards: dict[str, list[int]] | None = None,
    hands: dict[str, list[list[int]]] | None = None,
    route: list[Any] | None = None,
    targets: list[list[int]] | None = None,
    stdin: str = "",
) -> dict[str, Any]:
    return {
        "width": width,
        "height": height,
        "start": start,
        "goal": goal,
        "gems": gems or [],
        "walls": walls or [],
        "energy": energy,
        "gem_values": gem_values or {},
        "cards": cards or {},
        "hands": hands or {},
        "route": route or [],
        "targets": targets or [],
        "stdin": stdin,
    }


ASSIGNMENTS: list[dict[str, Any]] = [
    {
        "id": "cs1-01-first-step",
        "order": 1,
        "week": 1,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 1: Intro, basics",
        "title": "First Step",
        "concept": "Call one command",
        "summary": "Move the agent one square to the flag.",
        "instructions": "Use one command: move_right()",
        "starter_code": "# Move to the flag.\n",
        "world": _world(3, 3, [0, 1], [1, 1]),
        "objectives": [{"type": "reach_goal"}],
        "required_terms": ["move_right"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "cs1-02-sequence",
        "order": 2,
        "week": 1,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 1: Intro, basics",
        "title": "Two-Step Path",
        "concept": "Sequence",
        "summary": "Write commands in order.",
        "instructions": "Reach the flag two squares away.",
        "starter_code": "# Commands run from top to bottom.\n",
        "world": _world(4, 3, [0, 1], [2, 1]),
        "objectives": [{"type": "reach_goal"}],
        "required_terms": ["move_right"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "cs1-03-collect",
        "order": 3,
        "week": 1,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 1: Intro, basics",
        "title": "Pick Up the Gem",
        "concept": "Command with an effect",
        "summary": "Move, then collect the gem.",
        "instructions": "Stand on the gem, use collect(), and finish on the flag.",
        "starter_code": "# Move to the gem, then collect it.\n",
        "world": _world(4, 3, [0, 1], [2, 1], gems=[[2, 1]]),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["collect"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "cs1-04-argument",
        "order": 4,
        "week": 2,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 2: Basic I/O, variables, strings",
        "title": "Long Step",
        "concept": "Function arguments",
        "summary": "Use a number to control a command.",
        "instructions": "Use move_right(3) to reach the flag.",
        "starter_code": "# move_right can take a number.\n",
        "world": _world(5, 3, [0, 1], [3, 1]),
        "objectives": [{"type": "reach_goal"}],
        "required_terms": ["move_right(3"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "cs1-05-variable",
        "order": 5,
        "week": 2,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 2: Basic I/O, variables, strings",
        "title": "Store the Distance",
        "concept": "Variables",
        "summary": "Use a variable as a command argument.",
        "instructions": "Create a variable named steps, give it the correct distance, then use it with move_right.",
        "starter_code": "steps = 0\n# Change steps, then move.\n",
        "world": _world(5, 3, [0, 1], [3, 1]),
        "objectives": [{"type": "reach_goal"}],
        "required_terms": ["steps", "="],
        "exercise_type": "Agent mission",
    },
    {
        "id": "w02-03-signal-ready",
        "order": 6,
        "week": 2,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 2: Basic I/O, variables, strings",
        "title": "Signal Ready",
        "concept": "String output",
        "summary": "Store a short message and show it in the game trace.",
        "instructions": "Create a variable named message with the value 'ready', then call say(message).",
        "starter_code": "message = \"\"\n# Say the exact message: ready\n",
        "world": _world(3, 3, [1, 1], [1, 1]),
        "objectives": [{"type": "message_equals", "expected": "ready"}],
        "required_terms": ["message", "say"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "cs2-01-if",
        "order": 7,
        "week": 3,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 3: String processing, ifs",
        "title": "Check Before Collecting",
        "concept": "If statements",
        "summary": "Use an if statement to collect only when a gem is present.",
        "instructions": "Move to the gem. If on_gem() is true, collect().",
        "starter_code": "# Use if on_gem(): before collect().\n",
        "world": _world(4, 3, [0, 1], [2, 1], gems=[[2, 1]]),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["if", "on_gem"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "w03-02-blue-key-gate",
        "order": 8,
        "week": 3,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 3: String processing, ifs",
        "title": "Blue Key Gate",
        "concept": "String comparison",
        "summary": "Use a string value to choose the correct path.",
        "instructions": "Set key to 'blue'. If key is blue, move right to the flag; otherwise move down.",
        "starter_code": "key = \"\"\n# Use if to choose the correct path.\n",
        "world": _world(3, 3, [0, 1], [1, 1]),
        "objectives": [{"type": "reach_goal"}],
        "required_terms": ["key", "if", "blue"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "w03-03-starts-with-a",
        "order": 9,
        "week": 3,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 3: String processing, ifs",
        "title": "Starts With A",
        "concept": "String indexing",
        "summary": "Write a small function that checks the first letter of a word.",
        "instructions": "Define starts_with_a(word). The word will be non-empty. Return True if it starts with lowercase 'a', otherwise False.",
        "starter_code": "def starts_with_a(word):\n    # Return True or False.\n    pass\n",
        "world": _world(3, 3, [1, 1], [1, 1]),
        "objectives": [
            {"type": "function_tests", "function": "starts_with_a", "cases": [
                {"args": ["apple"], "expected": True},
                {"args": ["banana"], "expected": False},
                {"args": ["aip1"], "expected": True}
            ]}
        ],
        "required_terms": ["def", "return"],
        "exercise_type": "Function tests",
    },
    {
        "id": "cs2-02-while",
        "order": 10,
        "week": 4,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 4: ifs, loops",
        "title": "Walk Until the Flag",
        "concept": "While loops",
        "summary": "Use repetition instead of writing the same command many times.",
        "instructions": "Use while not at_goal(): and move_right().",
        "starter_code": "# Repeat until the agent reaches the flag.\n",
        "world": _world(7, 3, [0, 1], [5, 1]),
        "objectives": [{"type": "reach_goal"}],
        "required_terms": ["while", "at_goal"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "w04-02-loop-collect-trail",
        "order": 11,
        "week": 4,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 4: ifs, loops",
        "title": "Collect the Trail",
        "concept": "If inside a loop",
        "summary": "Repeat movement and collect gems only when present.",
        "instructions": "While the agent is not at the flag, collect if on_gem() is true, then move right.",
        "starter_code": "# Combine while, if, on_gem(), collect(), and move_right().\n",
        "world": _world(5, 3, [0, 1], [3, 1], gems=[[0, 1], [1, 1], [2, 1]]),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["while", "if", "on_gem", "collect"],
        "exercise_type": "Agent mission",
    },
    {
        "id": "w04-03-repeat-word",
        "order": 12,
        "week": 4,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 4: ifs, loops",
        "title": "Repeat Word",
        "concept": "String building loop",
        "summary": "Build a repeated string with a loop.",
        "instructions": "Define repeat_word(word, n), returning word repeated n times. Use a loop, not multiplication.",
        "starter_code": "def repeat_word(word, n):\n    result = \"\"\n    # Add a loop here.\n    return result\n",
        "world": _world(3, 3, [1, 1], [1, 1]),
        "objectives": [
            {"type": "function_tests", "function": "repeat_word", "cases": [
                {"args": ["ha", 3], "expected": "hahaha"},
                {"args": ["go", 1], "expected": "go"},
                {"args": ["x", 0], "expected": ""}
            ]}
        ],
        "required_terms": ["def", "while", "return"],
        "forbidden_terms": ["* n", "*n"],
        "exercise_type": "Function tests",
    },
    {
        "id": "cs2-03-for",
        "order": 13,
        "week": 5,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 5: Loops, lists",
        "title": "Collect a Row",
        "concept": "For loops",
        "summary": "Use a for loop to repeat a collect-and-move pattern.",
        "instructions": "Collect three gems in a row and end at the flag. Use for i in range(3): so the repeated behavior is visible in the replay.",
        "starter_code": "# Use for i in range(3): for the repeated work.\n",
        "world": _world(6, 3, [0, 1], [3, 1], gems=[[0, 1], [1, 1], [2, 1]]),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["for", "range", "collect"],
        "exercise_type": "Grid game",
    },
    {
        "id": "w05-02-count-positive",
        "order": 14,
        "week": 5,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 5: Loops, lists",
        "title": "Route List",
        "concept": "Loop over a list",
        "summary": "Use a list of action strings to drive the agent through a maze.",
        "instructions": "Create route = ['right', 'right', 'down', 'down']. Loop through route. If the action is 'right', move_right(); if it is 'down', move_down(). Collect the gem at the flag.",
        "starter_code": "route = []\n# Loop over route and move for each action.\n",
        "world": _world(4, 4, [0, 0], [2, 2], gems=[[2, 2]], walls=[[0, 2], [1, 2], [3, 0]]),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["route", "[", "for", "if"],
        "exercise_type": "Grid game",
    },
    {
        "id": "w05-03-perfect-squares",
        "order": 15,
        "week": 5,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 5: Loops, lists",
        "title": "Supply Stops",
        "concept": "Loop over numeric list values",
        "summary": "Use a list of step sizes to visit supply gems.",
        "instructions": "Use distances = [2, 1, 2]. For each distance, move_right(distance). If the agent is on a gem, collect it. Finish on the flag with all supplies collected.",
        "starter_code": "distances = []\n# Move by each distance and collect supplies.\n",
        "world": _world(7, 3, [0, 1], [5, 1], gems=[[2, 1], [3, 1], [5, 1]]),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["distances", "[", "for", "on_gem", "collect"],
        "exercise_type": "Grid game",
    },
    {
        "id": "w06-01-passing-scores",
        "order": 16,
        "week": 6,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 6: Loops, lists",
        "title": "Positive Crystals",
        "concept": "Filtering pattern",
        "summary": "Walk through crystal values and collect only the useful gems.",
        "instructions": "Use values = [5, -4, 3, -2, 4]. Move right once for each value. Collect only when the value is positive. The final score should be 12.",
        "starter_code": "values = []\n# Move through the crystals and collect only positive values.\n",
        "world": _world(
            7,
            3,
            [0, 1],
            [5, 1],
            gems=[[1, 1], [2, 1], [3, 1], [4, 1], [5, 1]],
            gem_values={"1,1": 5, "2,1": -4, "3,1": 3, "4,1": -2, "5,1": 4},
        ),
        "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 12}, {"type": "collected_count", "expected": 3}],
        "required_terms": ["values", "[", "for", "if", "collect"],
        "exercise_type": "Scored grid game",
    },
    {
        "id": "w06-02-largest-number",
        "order": 17,
        "week": 6,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 6: Loops, lists",
        "title": "Best Crystal",
        "concept": "Maximum pattern",
        "summary": "Find the best crystal value before deciding where to move.",
        "instructions": "Use values = [2, 9, 4]. Find the largest value and its position with a loop. Move to that crystal, collect it, and stop on the flag. The final score should be 9.",
        "starter_code": "values = [2, 9, 4]\nbest_value = values[0]\nbest_index = 0\n# Find the largest value and its index.\n# Then move to that crystal and collect it.\n",
        "world": _world(5, 3, [0, 1], [2, 1], gems=[[1, 1], [2, 1], [3, 1]], gem_values={"1,1": 2, "2,1": 9, "3,1": 4}),
        "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 9}, {"type": "collected_count", "expected": 1}],
        "required_terms": ["best_value", "best_index", "for", "if", "collect"],
        "exercise_type": "Scored grid game",
    },
    {
        "id": "w06-03-first-long-word",
        "order": 18,
        "week": 6,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 6: Loops, lists",
        "title": "First Safe Crystal",
        "concept": "Searching pattern",
        "summary": "Search a list and stop when the first useful gem is found.",
        "instructions": "Use values = [-3, -2, 6, 4]. Move right once for each value until you find the first positive value. Collect it and stop on the flag. Use break after collecting.",
        "starter_code": "values = [-3, -2, 6, 4]\n# Search from left to right for the first positive crystal.\n",
        "world": _world(
            6,
            3,
            [0, 1],
            [3, 1],
            gems=[[1, 1], [2, 1], [3, 1], [4, 1]],
            gem_values={"1,1": -3, "2,1": -2, "3,1": 6, "4,1": 4},
        ),
        "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 6}, {"type": "collected_count", "expected": 1}],
        "required_terms": ["values", "for", "if", "break", "collect"],
        "exercise_type": "Scored grid game",
    },
    {
        "id": "cs2-04-function",
        "order": 19,
        "week": 7,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 7: Lists, functions",
        "title": "Make a Helper",
        "concept": "Function definition",
        "summary": "Create a function for repeated game behavior.",
        "instructions": "Define collect_and_move(), then call it three times to collect the gem trail and reach the flag.",
        "starter_code": "def collect_and_move():\n    # Add commands here.\n    pass\n\n# Call your helper below.\n",
        "world": _world(6, 3, [0, 1], [3, 1], gems=[[0, 1], [1, 1], [2, 1]]),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["def", "collect_and_move"],
        "exercise_type": "Grid game",
    },
    {
        "id": "w07-02-card-points",
        "order": 20,
        "week": 7,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 7: Lists, functions",
        "title": "Card Gate",
        "concept": "Helper function in a game decision",
        "summary": "Use a card_points helper to decide which card room is safe to collect.",
        "instructions": "Define card_points(card). Then move through three card rooms. At each room, use card_points(card_at()). Collect only if the card is worth 0 points. The safe room is the flag.",
        "starter_code": "def card_points(card):\n    # Hearts have suit 3. Queen of spades is (10, 2).\n    pass\n\n# Move through the card rooms and collect only a zero-point room.\n",
        "world": _world(
            5,
            3,
            [0, 1],
            [3, 1],
            gems=[[1, 1], [2, 1], [3, 1]],
            cards={"1,1": [4, 3], "2,1": [10, 2], "3,1": [12, 0]},
        ),
        "objectives": [
            {"type": "reach_goal"},
            {"type": "collected_count", "expected": 1},
            {"type": "function_tests", "function": "card_points", "card_args": True, "cases": [
                {"args": [[10, 2]], "expected": 13},
                {"args": [[4, 3]], "expected": 1},
                {"args": [[12, 0]], "expected": 0}
            ]},
        ],
        "required_terms": ["def", "card_points", "card_at", "for", "if", "collect"],
        "exercise_type": "Card grid game",
    },
    {
        "id": "w07-03-count-hearts",
        "order": 21,
        "week": 7,
        "part": "Part 1: Programming Foundations",
        "stage": "Week 7: Lists, functions",
        "title": "Heart Scanner",
        "concept": "Function over a list of cards",
        "summary": "Use count_hearts to decide which room is safe.",
        "instructions": "Define count_hearts(hand). Use hands = [[(2,3),(5,3)], [(10,2)], [(4,0),(8,1)]]. Move right for each hand. Collect only when count_hearts(hand) is 0. Finish on the flag.",
        "starter_code": "def count_hearts(hand):\n    count = 0\n    # Count cards with suit 3.\n    return count\n\nhands = [[(2, 3), (5, 3)], [(10, 2)], [(4, 0), (8, 1)]]\n# Move through one room per hand and collect only safe rooms.\n",
        "world": _world(5, 3, [0, 1], [3, 1], gems=[[1, 1], [2, 1], [3, 1]]),
        "objectives": [
            {"type": "reach_goal"},
            {"type": "collected_count", "expected": 2},
            {"type": "function_tests", "function": "count_hearts", "card_args": True, "cases": [
                {"args": [[[2, 3], [10, 2], [5, 3]]], "expected": 2},
                {"args": [[[0, 0], [8, 1]]], "expected": 0},
                {"args": [[[1, 3], [7, 3], [12, 3]]], "expected": 3}
            ]},
        ],
        "required_terms": ["def", "count_hearts", "hands", "for", "if", "collect"],
        "exercise_type": "Card grid game",
    },
    {
        "id": "project-studio",
        "order": 22,
        "week": 9,
        "part": "Part 2: 2-stage AI and project studio",
        "stage": "Project unlock",
        "title": "AIP1 Studio Project",
        "concept": "Project",
        "summary": "Build a small app or game using the project templates.",
        "instructions": "Unlocked after the Week 1-7 exercise roadmap.",
        "starter_code": "",
        "world": _world(3, 3, [0, 1], [1, 1]),
        "objectives": [],
        "is_project": True,
        "exercise_type": "Project",
    },
]


def _assignment_by_id(assignment_id: str) -> dict[str, Any]:
    for assignment in ASSIGNMENTS:
        if assignment["id"] == assignment_id:
            return assignment
    raise KeyError(assignment_id)


def _same_objectives(assignment_id: str) -> list[dict[str, Any]]:
    return _assignment_by_id(assignment_id).get("objectives", [])

_assignment_by_id("w02-03-signal-ready").update(
    {
        "title": "Call Sign",
        "concept": "Basic input/output and strings",
        "summary": "Read a call sign, normalize it, print it, and show it in the game trace.",
        "instructions": "Read one line with input(). Remove spaces around it, convert it to uppercase, print it, and call say() with the same result. Your code must work for every debug map input.",
        "starter_code": "call_sign = input()\n# Clean it with strip(), convert to uppercase, print it, and say it.\n",
        "world": _world(3, 3, [1, 1], [1, 1], stdin="  alpha\n"),
        "objectives": [
            {"type": "message_equals", "expected": "ALPHA"},
            {"type": "stdout_equals", "expected": "ALPHA"},
        ],
        "required_terms": ["input", "strip", "upper", "print", "say"],
        "exercise_type": "I/O game",
        "test_cases": [
            {
                "name": "Alpha",
                "world": _world(3, 3, [1, 1], [1, 1], stdin="  alpha\n"),
                "objectives": [{"type": "message_equals", "expected": "ALPHA"}, {"type": "stdout_equals", "expected": "ALPHA"}],
            },
            {
                "name": "Beta",
                "world": _world(3, 3, [1, 1], [1, 1], stdin="beta  \n"),
                "objectives": [{"type": "message_equals", "expected": "BETA"}, {"type": "stdout_equals", "expected": "BETA"}],
            },
            {
                "name": "Gate 7",
                "world": _world(3, 3, [1, 1], [1, 1], stdin=" gate 7 \n"),
                "objectives": [{"type": "message_equals", "expected": "GATE 7"}, {"type": "stdout_equals", "expected": "GATE 7"}],
            },
        ],
    }
)

_assignment_by_id("w03-02-blue-key-gate").update(
    {
        "title": "Keycode Gate",
        "concept": "String parsing and conditionals",
        "summary": "Read a keycode, normalize it, and choose the correct route.",
        "instructions": "Read one keycode with input(). Remove spaces and compare it case-insensitively. If the key is blue, move right. If the key is red, move down. Collect if there is a gem.",
        "starter_code": "key = input()\n# Clean and normalize key, then choose the route.\n",
        "world": _world(3, 3, [0, 1], [1, 1], gems=[[1, 1]], stdin=" blue \n"),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["input", "strip", "lower", "if", "collect"],
        "exercise_type": "String gate game",
        "test_cases": [
            {
                "name": "Blue Gate",
                "world": _world(3, 3, [0, 1], [1, 1], gems=[[1, 1]], stdin=" blue \n"),
                "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
            },
            {
                "name": "Red Gate",
                "world": _world(3, 3, [0, 0], [0, 1], gems=[[0, 1]], stdin="RED\n"),
                "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
            },
        ],
    }
)

_assignment_by_id("w03-03-starts-with-a").update(
    {
        "title": "Command Decoder",
        "concept": "String indexing and commands",
        "summary": "Use the first letter of an input command to move the agent.",
        "instructions": "Read one command with input(). After stripping spaces and converting to lowercase, use the first character: r means move right, d means move down, u means move up. Collect if there is a gem.",
        "starter_code": "command = input()\n# Use command.strip().lower()[0] to decode the move.\n",
        "world": _world(3, 3, [0, 1], [1, 1], gems=[[1, 1]], stdin=" right \n"),
        "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
        "required_terms": ["input", "strip", "lower", "[", "if", "collect"],
        "exercise_type": "String command game",
        "test_cases": [
            {
                "name": "Right Command",
                "world": _world(3, 3, [0, 1], [1, 1], gems=[[1, 1]], stdin=" right \n"),
                "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
            },
            {
                "name": "Down Command",
                "world": _world(3, 3, [1, 0], [1, 1], gems=[[1, 1]], stdin="Down\n"),
                "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
            },
            {
                "name": "Up Command",
                "world": _world(3, 3, [1, 2], [1, 1], gems=[[1, 1]], stdin="  UP\n"),
                "objectives": [{"type": "reach_goal"}, {"type": "collect_all"}],
            },
        ],
    }
)



_assignment_by_id("cs2-03-for").update(
    {
        "test_cases": [
            {
                "name": "Row A",
                "world": _world(6, 3, [0, 1], [3, 1], gems=[[0, 1], [1, 1], [2, 1]]),
                "objectives": _same_objectives("cs2-03-for"),
            },
            {
                "name": "Row B",
                "world": _world(6, 4, [0, 2], [3, 2], gems=[[0, 2], [1, 2], [2, 2]]),
                "objectives": _same_objectives("cs2-03-for"),
            },
        ]
    }
)

_assignment_by_id("w05-02-count-positive").update(
    {
        "instructions": "Use route = get_route(). Loop through route and move for each action string. Support right, left, up, and down. Collect the gem at the flag.",
        "starter_code": "route = get_route()\n# Loop over route and move for each action.\n",
        "required_terms": ["get_route", "for", "if"],
        "test_cases": [
            {
                "name": "Corner Route",
                "world": _world(4, 4, [0, 0], [2, 2], gems=[[2, 2]], walls=[[0, 2], [1, 2], [3, 0]], route=["right", "right", "down", "down"]),
                "objectives": _same_objectives("w05-02-count-positive"),
            },
            {
                "name": "Upper Route",
                "world": _world(4, 3, [0, 1], [2, 0], gems=[[2, 0]], walls=[[1, 1]], route=["up", "right", "right"]),
                "objectives": _same_objectives("w05-02-count-positive"),
            },
        ],
    }
)

_assignment_by_id("w05-03-perfect-squares").update(
    {
        "instructions": "Use distances = get_route(). For each distance, move_right(distance). If the agent is on a gem, collect it. Finish on the flag with all supplies collected.",
        "starter_code": "distances = get_route()\n# Move by each distance and collect supplies.\n",
        "required_terms": ["get_route", "for", "on_gem", "collect"],
        "test_cases": [
            {
                "name": "Long Supplies",
                "world": _world(7, 3, [0, 1], [5, 1], gems=[[2, 1], [3, 1], [5, 1]], route=[2, 1, 2]),
                "objectives": _same_objectives("w05-03-perfect-squares"),
            },
            {
                "name": "Short Supplies",
                "world": _world(6, 3, [0, 1], [4, 1], gems=[[1, 1], [3, 1], [4, 1]], route=[1, 2, 1]),
                "objectives": _same_objectives("w05-03-perfect-squares"),
            },
        ],
    }
)

_assignment_by_id("w06-01-passing-scores").update(
    {
        "instructions": "Use values = get_route(). Move right once for each value. Collect only when the value is positive. Your code must work on every map, not just the visible one.",
        "starter_code": "values = get_route()\n# Move through the crystals and collect only positive values.\n",
        "required_terms": ["get_route", "for", "if", "collect"],
        "test_cases": [
            {
                "name": "Five Crystals",
                "world": _world(7, 3, [0, 1], [5, 1], gems=[[1, 1], [2, 1], [3, 1], [4, 1], [5, 1]], gem_values={"1,1": 5, "2,1": -4, "3,1": 3, "4,1": -2, "5,1": 4}, route=[5, -4, 3, -2, 4]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 12}, {"type": "collected_count", "expected": 3}],
            },
            {
                "name": "Four Crystals",
                "world": _world(6, 3, [0, 1], [4, 1], gems=[[1, 1], [2, 1], [3, 1], [4, 1]], gem_values={"1,1": -1, "2,1": 6, "3,1": -3, "4,1": 2}, route=[-1, 6, -3, 2]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 8}, {"type": "collected_count", "expected": 2}],
            },
        ],
    }
)

_assignment_by_id("w06-02-largest-number").update(
    {
        "instructions": "Use values = get_route(). Find the largest value and its index with a loop. Move to that crystal, collect it, and stop on the flag. Your code must work when the best crystal changes position.",
        "starter_code": "values = get_route()\nbest_value = values[0]\nbest_index = 0\n# Find the largest value and its index.\n# Then move to that crystal and collect it.\n",
        "required_terms": ["get_route", "best_value", "best_index", "for", "if", "collect"],
        "test_cases": [
            {
                "name": "Middle Best",
                "world": _world(5, 3, [0, 1], [2, 1], gems=[[1, 1], [2, 1], [3, 1]], gem_values={"1,1": 2, "2,1": 9, "3,1": 4}, route=[2, 9, 4]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 9}, {"type": "collected_count", "expected": 1}],
            },
            {
                "name": "First Best",
                "world": _world(5, 3, [0, 1], [1, 1], gems=[[1, 1], [2, 1], [3, 1]], gem_values={"1,1": 7, "2,1": 1, "3,1": 5}, route=[7, 1, 5]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 7}, {"type": "collected_count", "expected": 1}],
            },
            {
                "name": "Third Best",
                "world": _world(6, 3, [0, 1], [3, 1], gems=[[1, 1], [2, 1], [3, 1], [4, 1]], gem_values={"1,1": 1, "2,1": 3, "3,1": 8, "4,1": 2}, route=[1, 3, 8, 2]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 8}, {"type": "collected_count", "expected": 1}],
            },
        ],
    }
)

_assignment_by_id("w06-03-first-long-word").update(
    {
        "instructions": "Use values = get_route(). Move right once for each value until you find the first positive value. Collect it and stop on the flag. Use break after collecting.",
        "starter_code": "values = get_route()\n# Search from left to right for the first positive crystal.\n",
        "required_terms": ["get_route", "for", "if", "break", "collect"],
        "test_cases": [
            {
                "name": "Third Safe",
                "world": _world(6, 3, [0, 1], [3, 1], gems=[[1, 1], [2, 1], [3, 1], [4, 1]], gem_values={"1,1": -3, "2,1": -2, "3,1": 6, "4,1": 4}, route=[-3, -2, 6, 4]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 6}, {"type": "collected_count", "expected": 1}],
            },
            {
                "name": "Second Safe",
                "world": _world(5, 3, [0, 1], [2, 1], gems=[[1, 1], [2, 1], [3, 1]], gem_values={"1,1": -1, "2,1": 5, "3,1": 2}, route=[-1, 5, 2]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 5}, {"type": "collected_count", "expected": 1}],
            },
            {
                "name": "First Safe",
                "world": _world(5, 3, [0, 1], [1, 1], gems=[[1, 1], [2, 1], [3, 1]], gem_values={"1,1": 4, "2,1": -2, "3,1": 7}, route=[4, -2, 7]),
                "objectives": [{"type": "reach_goal"}, {"type": "score_equals", "expected": 4}, {"type": "collected_count", "expected": 1}],
            },
        ],
    }
)

_assignment_by_id("cs2-04-function").update(
    {
        "test_cases": [
            {
                "name": "Helper Row A",
                "world": _world(6, 3, [0, 1], [3, 1], gems=[[0, 1], [1, 1], [2, 1]]),
                "objectives": _same_objectives("cs2-04-function"),
            },
            {
                "name": "Helper Row B",
                "world": _world(6, 4, [0, 2], [3, 2], gems=[[0, 2], [1, 2], [2, 2]]),
                "objectives": _same_objectives("cs2-04-function"),
            },
        ]
    }
)

_assignment_by_id("w07-02-card-points").update(
    {
        "instructions": "Define card_points(card). Then move through card rooms while not at_goal(). At each room, use card_points(card_at()). Collect only if the current card is worth 0 points.",
        "starter_code": "def card_points(card):\n    # Hearts have suit 3. Queen of spades is (10, 2).\n    pass\n\n# Move through card rooms while not at_goal().\n# Collect only a zero-point room.\n",
        "required_terms": ["def", "card_points", "card_at", "while", "if", "collect"],
        "test_cases": [
            {
                "name": "Safe Third",
                "world": _world(5, 3, [0, 1], [3, 1], gems=[[1, 1], [2, 1], [3, 1]], cards={"1,1": [4, 3], "2,1": [10, 2], "3,1": [12, 0]}),
                "objectives": [{"type": "reach_goal"}, {"type": "collected_count", "expected": 1}, {"type": "function_tests", "function": "card_points", "card_args": True, "cases": [{"args": [[10, 2]], "expected": 13}, {"args": [[4, 3]], "expected": 1}, {"args": [[12, 0]], "expected": 0}]}],
            },
            {
                "name": "Safe Second",
                "world": _world(4, 3, [0, 1], [2, 1], gems=[[1, 1], [2, 1]], cards={"1,1": [10, 2], "2,1": [5, 1]}),
                "objectives": [{"type": "reach_goal"}, {"type": "collected_count", "expected": 1}, {"type": "function_tests", "function": "card_points", "card_args": True, "cases": [{"args": [[10, 2]], "expected": 13}, {"args": [[4, 3]], "expected": 1}, {"args": [[12, 0]], "expected": 0}]}],
            },
        ],
    }
)

_assignment_by_id("w07-03-count-hearts").update(
    {
        "instructions": "Define count_hearts(hand). Move through rooms while not at_goal(). Use hand_at() to inspect the current room. Collect only when count_hearts(hand_at()) is 0.",
        "starter_code": "def count_hearts(hand):\n    count = 0\n    # Count cards with suit 3.\n    return count\n\n# Move through rooms while not at_goal().\n# Collect only rooms with no hearts.\n",
        "required_terms": ["def", "count_hearts", "hand_at", "while", "if", "collect"],
        "test_cases": [
            {
                "name": "Two Safe Rooms",
                "world": _world(5, 3, [0, 1], [3, 1], gems=[[1, 1], [2, 1], [3, 1]], hands={"1,1": [[2, 3], [5, 3]], "2,1": [[10, 2]], "3,1": [[4, 0], [8, 1]]}),
                "objectives": [{"type": "reach_goal"}, {"type": "collected_count", "expected": 2}, {"type": "function_tests", "function": "count_hearts", "card_args": True, "cases": [{"args": [[[2, 3], [10, 2], [5, 3]]], "expected": 2}, {"args": [[[0, 0], [8, 1]]], "expected": 0}, {"args": [[[1, 3], [7, 3], [12, 3]]], "expected": 3}]}],
            },
            {
                "name": "One Safe Room",
                "world": _world(4, 3, [0, 1], [2, 1], gems=[[1, 1], [2, 1]], hands={"1,1": [[2, 3]], "2,1": [[10, 2], [4, 1]]}),
                "objectives": [{"type": "reach_goal"}, {"type": "collected_count", "expected": 1}, {"type": "function_tests", "function": "count_hearts", "card_args": True, "cases": [{"args": [[[2, 3], [10, 2], [5, 3]]], "expected": 2}, {"args": [[[0, 0], [8, 1]]], "expected": 0}, {"args": [[[1, 3], [7, 3], [12, 3]]], "expected": 3}]}],
            },
        ],
    }
)



def assignment_cases(assignment: dict[str, Any], include_hidden: bool = True) -> list[dict[str, Any]]:
    raw_cases = assignment.get("test_cases") or [
        {"name": "Map 1", "world": assignment["world"], "objectives": assignment.get("objectives", [])}
    ]
    cases = []
    for index, case in enumerate(raw_cases):
        if case.get("hidden") and not include_hidden:
            continue
        cases.append(
            {
                "index": index,
                "name": case.get("name") or f"Map {index + 1}",
                "world": case.get("world", assignment["world"]),
                "objectives": case.get("objectives", assignment.get("objectives", [])),
                "hidden": bool(case.get("hidden")),
            }
        )
    return cases


def public_assignment(assignment: dict[str, Any], unlocked: bool, completed: bool) -> dict[str, Any]:
    visible_cases = assignment_cases(assignment, include_hidden=False) if unlocked else []
    return {
        "id": assignment["id"],
        "order": assignment["order"],
        "week": assignment.get("week"),
        "part": assignment.get("part", ""),
        "stage": assignment["stage"],
        "title": assignment["title"],
        "concept": assignment["concept"],
        "summary": assignment["summary"],
        "instructions": assignment["instructions"],
        "exercise_type": assignment.get("exercise_type", "Agent mission"),
        "starter_code": assignment["starter_code"] if unlocked else "",
        "world": visible_cases[0]["world"] if visible_cases else (assignment["world"] if unlocked else None),
        "cases": [{"index": case["index"], "name": case["name"], "world": case["world"]} for case in visible_cases],
        "case_count": len(assignment_cases(assignment, include_hidden=True)) if unlocked else 0,
        "unlocked": unlocked,
        "completed": completed,
        "is_project": bool(assignment.get("is_project")),
    }


def get_assignment(assignment_id: str) -> dict[str, Any] | None:
    for assignment in ASSIGNMENTS:
        if assignment["id"] == assignment_id:
            return assignment
    return None


def assignment_ids() -> list[str]:
    return [assignment["id"] for assignment in ASSIGNMENTS]


def build_agent_program(
    student_code: str,
    assignment: dict[str, Any],
    *,
    world: dict[str, Any] | None = None,
    objectives: list[dict[str, Any]] | None = None,
    case_name: str = "Map 1",
) -> str:
    world_json = _py_json(world or assignment["world"])
    assignment_json = _py_json(
        {
            "id": assignment["id"],
            "case_name": case_name,
            "objectives": objectives if objectives is not None else assignment.get("objectives", []),
            "required_terms": assignment.get("required_terms", []),
            "forbidden_terms": assignment.get("forbidden_terms", []),
        }
    )
    code_json = repr(student_code)
    return f"""
import base64 as _aip1_base64
import io as _aip1_io
import json as _aip1_json
import sys as _aip1_sys
import contextlib as _aip1_contextlib
import traceback as _aip1_traceback

_AIP1_RESULT_PREFIX = {RESULT_PREFIX!r}
_AIP1_WORLD = _aip1_json.loads({world_json!r})
_AIP1_ASSIGNMENT = _aip1_json.loads({assignment_json!r})
_AIP1_STUDENT_CODE = {code_json}


class _AIP1Agent:
    def __init__(self, world):
        self.width = world["width"]
        self.height = world["height"]
        self.x = world["start"][0]
        self.y = world["start"][1]
        self.goal = tuple(world["goal"])
        self.walls = {{tuple(item) for item in world.get("walls", [])}}
        self.gems = {{tuple(item) for item in world.get("gems", [])}}
        self.gem_values = {{tuple(int(part) for part in key.split(",")): int(value) for key, value in world.get("gem_values", {{}}).items()}}
        self.cards = {{tuple(int(part) for part in key.split(",")): tuple(value) for key, value in world.get("cards", {{}}).items()}}
        self.hands = {{tuple(int(part) for part in key.split(",")): [tuple(card) for card in value] for key, value in world.get("hands", {{}}).items()}}
        self.collected = []
        self.score = 0
        self.energy = int(world.get("energy", 20))
        self.messages = []
        self.trace = []
        self.failed = False
        self.failure = ""
        self._trace("start", "Start")

    def _trace(self, action, detail=""):
        self.trace.append({{
            "action": action,
            "detail": str(detail),
            "x": self.x,
            "y": self.y,
            "energy": self.energy,
            "gems": [list(item) for item in sorted(self.gems)],
            "collected": len(self.collected),
            "score": self.score,
            "message": self.messages[-1] if self.messages else "",
        }})

    def move(self, dx, dy, label):
        steps = 1
        if isinstance(dx, tuple):
            dx, dy, label, steps = dx
        for _ in range(int(steps)):
            if self.energy <= 0:
                self.failed = True
                self.failure = "The agent ran out of energy."
                self._trace("blocked", self.failure)
                return
            nx = self.x + dx
            ny = self.y + dy
            if nx < 0 or nx >= self.width or ny < 0 or ny >= self.height or (nx, ny) in self.walls:
                self.failed = True
                self.failure = "The agent hit a wall or left the map."
                self._trace("blocked", self.failure)
                return
            self.x = nx
            self.y = ny
            self.energy -= 1
            self._trace(label, label)

    def collect(self):
        here = (self.x, self.y)
        if here not in self.gems:
            self.failed = True
            self.failure = "collect() was used where there was no gem."
            self._trace("collect failed", self.failure)
            return
        self.gems.remove(here)
        value = int(self.gem_values.get(here, 1))
        self.score += value
        self.collected.append(here)
        self._trace("collect", "Gem collected (" + ("+" if value >= 0 else "") + str(value) + ")")

    def say(self, message):
        self.messages.append(str(message))
        self._trace("say", str(message))

    def at_goal(self):
        return (self.x, self.y) == self.goal

    def on_gem(self):
        return (self.x, self.y) in self.gems

    def gem_value(self):
        return int(self.gem_values.get((self.x, self.y), 1 if self.on_gem() else 0))

    def card_at(self):
        return self.cards.get((self.x, self.y), None)

    def hand_at(self):
        return list(self.hands.get((self.x, self.y), []))


_aip1_agent = _AIP1Agent(_AIP1_WORLD)


def move_right(steps=1):
    _aip1_agent.move((1, 0, "move right", steps), 0, "move right")


def move_left(steps=1):
    _aip1_agent.move((-1, 0, "move left", steps), 0, "move left")


def move_up(steps=1):
    _aip1_agent.move((0, -1, "move up", steps), 0, "move up")


def move_down(steps=1):
    _aip1_agent.move((0, 1, "move down", steps), 0, "move down")


def collect():
    _aip1_agent.collect()


def say(message):
    _aip1_agent.say(message)


def at_goal():
    return _aip1_agent.at_goal()


def on_gem():
    return _aip1_agent.on_gem()


def get_energy():
    return _aip1_agent.energy


def get_score():
    return _aip1_agent.score


def gem_value():
    return _aip1_agent.gem_value()


def card_at():
    return _aip1_agent.card_at()


def hand_at():
    return _aip1_agent.hand_at()


def get_route():
    return list(_AIP1_WORLD.get("route", []))


def get_targets():
    return [tuple(item) for item in _AIP1_WORLD.get("targets", [])]


def get_position():
    return (_aip1_agent.x, _aip1_agent.y)


def _aip1_static_checks():
    checks = []
    code = _AIP1_STUDENT_CODE
    for term in _AIP1_ASSIGNMENT.get("required_terms", []):
        passed = term in code
        checks.append({{"name": "Uses " + term, "passed": passed, "details": "found" if passed else "missing"}})
    for term in _AIP1_ASSIGNMENT.get("forbidden_terms", []):
        passed = term not in code
        checks.append({{"name": "Removes " + term, "passed": passed, "details": "removed" if passed else "still present"}})
    return checks


def _aip1_cardify(value):
    if isinstance(value, list):
        if len(value) == 2 and all(isinstance(item, int) for item in value):
            return tuple(value)
        return [_aip1_cardify(item) for item in value]
    if isinstance(value, dict):
        return {{key: _aip1_cardify(item) for key, item in value.items()}}
    return value


def _aip1_normalize(value):
    if isinstance(value, tuple):
        return [_aip1_normalize(item) for item in value]
    if isinstance(value, list):
        return [_aip1_normalize(item) for item in value]
    if isinstance(value, dict):
        return {{str(key): _aip1_normalize(item) for key, item in value.items()}}
    return value


def _aip1_objective_checks():
    checks = []
    for objective in _AIP1_ASSIGNMENT.get("objectives", []):
        kind = objective.get("type")
        if kind == "reach_goal":
            passed = _aip1_agent.at_goal()
            checks.append({{"name": "Reach the flag", "passed": passed, "details": "at flag" if passed else "not at flag"}})
        elif kind == "collect_all":
            passed = len(_aip1_agent.gems) == 0
            checks.append({{"name": "Collect every gem", "passed": passed, "details": "all collected" if passed else str(len(_aip1_agent.gems)) + " left"}})
        elif kind == "collected_count":
            expected = int(objective.get("expected", 0))
            actual = len(_aip1_agent.collected)
            passed = actual == expected
            checks.append({{"name": "Collect " + str(expected) + " gems", "passed": passed, "details": "collected " + str(actual)}})
        elif kind == "score_equals":
            expected = int(objective.get("expected", 0))
            actual = _aip1_agent.score
            passed = actual == expected
            checks.append({{"name": "Score is " + str(expected), "passed": passed, "details": "score " + str(actual)}})
        elif kind == "score_at_least":
            expected = int(objective.get("expected", 0))
            actual = _aip1_agent.score
            passed = actual >= expected
            checks.append({{"name": "Score at least " + str(expected), "passed": passed, "details": "score " + str(actual)}})
        elif kind == "message_equals":
            expected = str(objective.get("expected", ""))
            actual = _aip1_agent.messages[-1] if _aip1_agent.messages else ""
            passed = actual == expected
            checks.append({{"name": "Says " + expected, "passed": passed, "details": "said " + repr(actual)}})
        elif kind == "message_in":
            expected = [str(item) for item in objective.get("expected", [])]
            actual = _aip1_agent.messages[-1] if _aip1_agent.messages else ""
            passed = actual in expected
            checks.append({{"name": "Says one accepted message", "passed": passed, "details": "said " + repr(actual)}})
        elif kind == "stdout_equals":
            expected = str(objective.get("expected", ""))
            actual = objective.get("stdout", "")
            passed = actual.strip() == expected.strip()
            checks.append({{"name": "Prints expected output", "passed": passed, "details": "printed " + repr(actual.strip())}})
        elif kind == "function_tests":
            fn_name = str(objective.get("function", ""))
            fn = globals().get(fn_name)
            if not callable(fn):
                checks.append({{"name": "Defines " + fn_name, "passed": False, "details": "function not found"}})
                continue
            cases = objective.get("cases", [])
            passed_count = 0
            details = []
            for index, case in enumerate(cases, 1):
                if not isinstance(case, dict):
                    continue
                args = case.get("args", [])
                kwargs = case.get("kwargs", {{}})
                expected = case.get("expected")
                if objective.get("card_args") or case.get("card_args"):
                    args = _aip1_cardify(args)
                    kwargs = _aip1_cardify(kwargs)
                try:
                    actual = fn(*args, **kwargs)
                    case_passed = _aip1_normalize(actual) == _aip1_normalize(expected)
                except Exception as exc:
                    actual = type(exc).__name__ + ": " + str(exc)
                    case_passed = False
                if case_passed:
                    passed_count += 1
                else:
                    details.append("case " + str(index) + " expected " + repr(expected) + " got " + repr(actual))
            total = len(cases)
            passed = total > 0 and passed_count == total
            detail = str(passed_count) + "/" + str(total) + " cases passed"
            if details:
                detail += "; " + "; ".join(details[:2])
            checks.append({{"name": "Passes " + fn_name + " tests", "passed": passed, "details": detail}})
    if _aip1_agent.failed:
        checks.append({{"name": "Agent stayed safe", "passed": False, "details": _aip1_agent.failure}})
    return checks


def _aip1_run():
    stdout = _aip1_io.StringIO()
    stdin = _aip1_io.StringIO(str(_AIP1_WORLD.get("stdin", "")))
    error = ""
    original_stdin = _aip1_sys.stdin
    try:
        _aip1_sys.stdin = stdin
        with _aip1_contextlib.redirect_stdout(stdout):
            try:
                exec(compile(_AIP1_STUDENT_CODE, "<student>", "exec"), globals(), globals())
            except Exception:
                error = _aip1_traceback.format_exc()
    finally:
        _aip1_sys.stdin = original_stdin
    stdout_text = stdout.getvalue().strip()
    for objective in _AIP1_ASSIGNMENT.get("objectives", []):
        if objective.get("type") == "stdout_equals":
            objective["stdout"] = stdout_text
    checks = _aip1_static_checks() + _aip1_objective_checks()
    if error:
        checks.append({{"name": "Program runs", "passed": False, "details": error}})
    else:
        checks.insert(0, {{"name": "Program runs", "passed": True, "details": "no Python error"}})
    passed = all(item.get("passed") for item in checks)
    return {{
        "ok": True,
        "case_name": _AIP1_ASSIGNMENT.get("case_name", "Map 1"),
        "passed": passed,
        "summary": {{"passed": sum(1 for item in checks if item.get("passed")), "total": len(checks)}},
        "checks": checks,
        "world": _AIP1_WORLD,
        "trace": _aip1_agent.trace,
        "stdout": stdout.getvalue().strip(),
        "error": error,
    }}


try:
    _aip1_payload = _aip1_run()
except Exception:
    _aip1_payload = {{"ok": False, "error": _aip1_traceback.format_exc(), "world": _AIP1_WORLD, "trace": _aip1_agent.trace}}

_aip1_encoded = _aip1_base64.b64encode(
    _aip1_json.dumps(_aip1_payload, ensure_ascii=False).encode("utf-8")
).decode("ascii")
print(_AIP1_RESULT_PREFIX + _aip1_encoded)
"""


def _world(
    width: int,
    height: int,
    start: list[int],
    goal: list[int],
    *,
    gems: list[list[int]] | None = None,
    walls: list[list[int]] | None = None,
    energy: int = 20,
    gem_values: dict[str, int] | None = None,
    cards: dict[str, list[int]] | None = None,
    hands: dict[str, list[list[int]]] | None = None,
    route: list[Any] | None = None,
    targets: list[list[int]] | None = None,
    stdin: str = "",
) -> dict[str, Any]:
    return {
        "width": width,
        "height": height,
        "start": start,
        "goal": goal,
        "gems": gems or [],
        "walls": walls or [],
        "energy": energy,
        "gem_values": gem_values or {},
        "cards": cards or {},
        "hands": hands or {},
        "route": route or [],
        "targets": targets or [],
        "stdin": stdin,
    }


def _py_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
