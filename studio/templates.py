from __future__ import annotations

from typing import Any


TEMPLATES: dict[str, dict[str, Any]] = {
    "adventure": {
        "id": "adventure",
        "name": "Adventure Game",
        "tagline": "Locations, inventory, scoring, and win/loss rules.",
        "spec_prompt": """Title:
Campus Cat Rescue

Rules:
- The player has energy, food, rescued cats, and a location.
- Moving costs energy.
- Food can be bought in the cafeteria.
- Cats can be rescued at the library and quad when food is available.
- The player wins after rescuing 3 cats.
- The player loses after energy runs out or 12 turns pass.

Personal changes I want:
- Add one more location.
- Add a reputation rule.
- Make rainy days change movement cost.""",
        "starter_code": '''TITLE = "Campus Cat Rescue"
DESCRIPTION = "Rescue campus cats before your energy or time runs out."
PROJECT_KIND = "adventure"

LOCATIONS = ["library", "cafeteria", "quad", "dorm"]


def starting_state():
    return {
        "location": "library",
        "energy": 10,
        "food": 1,
        "cats_rescued": 0,
        "turns": 0,
        "message": "You hear a cat somewhere nearby.",
    }


def describe_location(state):
    location = state["location"]
    if location == "library":
        place = "Quiet shelves, study tables, and one suspicious cardboard box."
    elif location == "cafeteria":
        place = "A busy cafeteria where you can buy extra cat food."
    elif location == "quad":
        place = "Open grass and benches. Cats like to hide here."
    else:
        place = "A dorm lobby with a sofa where you can rest."

    return (
        place
        + "\\nEnergy: "
        + str(state["energy"])
        + " | Food: "
        + str(state["food"])
        + " | Cats rescued: "
        + str(state["cats_rescued"])
        + " | Turns: "
        + str(state["turns"])
        + "\\n"
        + state["message"]
    )


def available_actions(state):
    if has_won(state) or has_lost(state):
        return []

    actions = []
    for location in LOCATIONS:
        if location != state["location"]:
            actions.append("go " + location)

    if state["location"] == "cafeteria" and state["energy"] >= 1:
        actions.append("buy food")

    if state["location"] in ["library", "quad"] and state["food"] > 0:
        actions.append("rescue cat")

    if state["location"] == "dorm":
        actions.append("rest")

    return actions


def apply_action(state, action):
    state = state.copy()
    state["turns"] = state["turns"] + 1

    if action.startswith("go "):
        destination = action[3:]
        if destination in LOCATIONS:
            state["location"] = destination
            state["energy"] = state["energy"] - 1
            state["message"] = "You walk to the " + destination + "."
        else:
            state["message"] = "That place is not on the map."

    elif action == "buy food":
        if state["location"] == "cafeteria" and state["energy"] >= 1:
            state["food"] = state["food"] + 2
            state["energy"] = state["energy"] - 1
            state["message"] = "You buy two servings of cat food."
        else:
            state["message"] = "You cannot buy food here."

    elif action == "rescue cat":
        if state["location"] in ["library", "quad"] and state["food"] > 0:
            state["food"] = state["food"] - 1
            state["cats_rescued"] = state["cats_rescued"] + 1
            state["message"] = "A cat accepts the food and follows you."
        else:
            state["message"] = "No cat is ready to be rescued here."

    elif action == "rest":
        if state["location"] == "dorm":
            state["energy"] = state["energy"] + 3
            state["message"] = "You rest in the dorm and recover energy."
        else:
            state["message"] = "You can only rest at the dorm."

    else:
        state["message"] = "Nothing happens."

    return state


def has_won(state):
    return state["cats_rescued"] >= 3


def has_lost(state):
    return state["energy"] <= 0 or state["turns"] >= 12


def score(state):
    return state["cats_rescued"] * 10 + state["food"] * 2 + state["energy"] - state["turns"]
''',
        "starter_tests": """[
  {
    "name": "Game starts in the library",
    "actions": [],
    "expect": {
      "state.location": "library",
      "state.energy": 10,
      "won": false,
      "lost": false
    }
  },
  {
    "name": "Rescuing a cat uses food",
    "actions": ["rescue cat"],
    "expect": {
      "state.cats_rescued": 1,
      "state.food": 0
    }
  },
  {
    "name": "Cafeteria sells food",
    "actions": ["go cafeteria", "buy food"],
    "expect": {
      "state.location": "cafeteria",
      "state.food": 3
    }
  },
  {
    "name": "Three rescues wins",
    "actions": ["rescue cat", "go cafeteria", "buy food", "go quad", "rescue cat", "go cafeteria", "buy food", "go library", "rescue cat"],
    "expect": {
      "won": true
    }
  }
]""",
    },
    "simulation": {
        "id": "simulation",
        "name": "Simulation App",
        "tagline": "State updates, parameters, loops, and tradeoffs.",
        "spec_prompt": """Title:
Coffee Shop Week

Rules:
- The shop tracks day, cash, beans, reputation, and price.
- Each action advances the day.
- Buying beans costs cash but allows more sales.
- Promotions cost cash and raise reputation.
- The simulation ends after 7 days.

Personal changes I want:
- Add a weather effect.
- Add different customer types.
- Make reputation affect sales more strongly.""",
        "starter_code": '''TITLE = "Coffee Shop Week"
DESCRIPTION = "Run a tiny coffee shop for one week and finish with enough cash."
PROJECT_KIND = "simulation"


def starting_state():
    return {
        "day": 1,
        "cash": 50,
        "beans": 8,
        "reputation": 2,
        "price": 4,
        "message": "The shop opens for the week.",
    }


def describe_state(state):
    return (
        "Day "
        + str(state["day"])
        + ": cash $"
        + str(state["cash"])
        + ", beans "
        + str(state["beans"])
        + ", reputation "
        + str(state["reputation"])
        + ", price $"
        + str(state["price"])
        + ".\\n"
        + state["message"]
    )


def available_actions(state):
    if has_won(state) or has_lost(state):
        return []
    actions = ["brew standard menu", "buy beans", "run promotion"]
    if state["price"] < 7:
        actions.append("raise price")
    if state["price"] > 2:
        actions.append("lower price")
    return actions


def apply_action(state, action):
    state = state.copy()
    state["day"] = state["day"] + 1

    if action == "brew standard menu":
        cups = min(state["beans"], 3 + state["reputation"])
        state["beans"] = state["beans"] - cups
        state["cash"] = state["cash"] + cups * state["price"]
        state["message"] = "You sell " + str(cups) + " cups of coffee."

    elif action == "buy beans":
        state["cash"] = state["cash"] - 12
        state["beans"] = state["beans"] + 8
        state["message"] = "You restock beans for the next rush."

    elif action == "run promotion":
        state["cash"] = state["cash"] - 8
        state["reputation"] = state["reputation"] + 2
        state["message"] = "A promotion brings more attention."

    elif action == "raise price":
        state["price"] = state["price"] + 1
        state["reputation"] = max(0, state["reputation"] - 1)
        state["message"] = "Higher prices may reduce goodwill."

    elif action == "lower price":
        state["price"] = state["price"] - 1
        state["reputation"] = state["reputation"] + 1
        state["message"] = "Lower prices make customers happier."

    else:
        state["message"] = "That business decision is unavailable."

    return state


def has_won(state):
    return state["day"] > 7 and state["cash"] >= 90


def has_lost(state):
    return state["cash"] < 0 or state["beans"] < 0 or (state["day"] > 7 and state["cash"] < 90)


def score(state):
    return state["cash"] + state["beans"] * 2 + state["reputation"] * 5
''',
        "starter_tests": """[
  {
    "name": "Simulation starts with enough cash",
    "actions": [],
    "expect": {
      "state.day": 1,
      "state.cash": 50,
      "lost": false
    }
  },
  {
    "name": "Buying beans costs cash",
    "actions": ["buy beans"],
    "expect": {
      "state.cash": 38,
      "state.beans": 16
    }
  },
  {
    "name": "Promotion raises reputation",
    "actions": ["run promotion"],
    "expect": {
      "state.reputation": 4
    }
  }
]""",
    },
    "decision": {
        "id": "decision",
        "name": "Decision Helper",
        "tagline": "Input validation, recommendation rules, and scoring.",
        "spec_prompt": """Title:
Study Plan Helper

Rules:
- The user builds a study profile through action buttons.
- The state tracks available hours, difficulty, focus, and stress.
- Recommendations appear once enough information is collected.
- A stronger plan has enough hours and controlled stress.

Personal changes I want:
- Add a sleep rule.
- Add different course types.
- Make the final recommendation more specific.""",
        "starter_code": '''TITLE = "Study Plan Helper"
DESCRIPTION = "Build a small study profile and recommend a plan."
PROJECT_KIND = "decision"


def starting_state():
    return {
        "hours": 2,
        "difficulty": 1,
        "focus": 2,
        "stress": 1,
        "steps": 0,
        "recommendation": "Collect more information.",
    }


def describe_state(state):
    return (
        "Hours: "
        + str(state["hours"])
        + " | Difficulty: "
        + str(state["difficulty"])
        + " | Focus: "
        + str(state["focus"])
        + " | Stress: "
        + str(state["stress"])
        + "\\nRecommendation: "
        + state["recommendation"]
    )


def available_actions(state):
    if has_won(state) or has_lost(state):
        return []
    return [
        "add study hour",
        "mark course harder",
        "improve focus",
        "add stress",
        "make recommendation",
    ]


def apply_action(state, action):
    state = state.copy()
    state["steps"] = state["steps"] + 1

    if action == "add study hour":
        state["hours"] = state["hours"] + 1
    elif action == "mark course harder":
        state["difficulty"] = state["difficulty"] + 1
    elif action == "improve focus":
        state["focus"] = state["focus"] + 1
        state["stress"] = max(0, state["stress"] - 1)
    elif action == "add stress":
        state["stress"] = state["stress"] + 1
    elif action == "make recommendation":
        if state["hours"] >= state["difficulty"] * 2 and state["stress"] <= 4:
            state["recommendation"] = "Use two focused sessions and one review quiz."
        elif state["stress"] > 4:
            state["recommendation"] = "Use a shorter plan and schedule rest first."
        else:
            state["recommendation"] = "Add one more study hour before choosing a plan."
    return state


def has_won(state):
    return state["recommendation"] != "Collect more information." and state["steps"] >= 3


def has_lost(state):
    return state["stress"] >= 7


def score(state):
    return state["hours"] * 5 + state["focus"] * 4 - state["difficulty"] * 3 - state["stress"] * 2
''',
        "starter_tests": """[
  {
    "name": "Profile starts with two hours",
    "actions": [],
    "expect": {
      "state.hours": 2,
      "state.recommendation": "Collect more information."
    }
  },
  {
    "name": "Adding study hour changes hours",
    "actions": ["add study hour"],
    "expect": {
      "state.hours": 3
    }
  },
  {
    "name": "Recommendation can finish the helper",
    "actions": ["add study hour", "improve focus", "make recommendation"],
    "expect": {
      "won": true
    }
  }
]""",
    },
}


def template_list() -> list[dict[str, str]]:
    return [
        {
            "id": template["id"],
            "name": template["name"],
            "tagline": template["tagline"],
        }
        for template in TEMPLATES.values()
    ]


def get_template(template_id: str) -> dict[str, Any]:
    return TEMPLATES.get(template_id) or TEMPLATES["adventure"]
