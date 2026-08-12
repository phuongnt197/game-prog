export const CELL_SIZE = 32;
export const DECISION_TIMEOUT_MS = 900;
export const RUN_DELAY_MS = 115;

export const ACTIONS = ["UP", "DOWN", "LEFT", "RIGHT", "STOP"];
export const DIRECTIONS = {
  UP: { x: 0, y: -1 },
  DOWN: { x: 0, y: 1 },
  LEFT: { x: -1, y: 0 },
  RIGHT: { x: 1, y: 0 },
  STOP: { x: 0, y: 0 },
};

export const LEVELS = {
  training: {
    label: "Starter Maze",
    description: "A smaller required map for developing the basic strategy.",
    targetScore: 600,
    required: true,
    rows: [
      "###############",
      "#P...........G#",
      "#.###.###.###.#",
      "#.....#.......#",
      "#.###.#.###.#.#",
      "#.............#",
      "###############",
    ],
  },
  classic: {
    label: "Classic Maze",
    description: "The larger required maze with a pursuing ghost.",
    targetScore: 850,
    required: true,
    rows: [
      "#####################", "#P....#.......#....G#", "#.###.#.#####.#.###.#",
      "#.....#...#...#.....#", "###.###.#.#.#.###.###", "#.......#.#.#.......#",
      "#.#####.#.#.#.#####.#", "#.......#...#.......#", "#####################",
    ],
  },
  corridors: {
    label: "Corridors",
    description: "An optional practice map with long narrow routes.",
    targetScore: 850,
    required: false,
    rows: [
      "#####################", "#P....#.......#.....#", "#.###.#.#####.#.###.#",
      "#.#...#...G...#...#.#", "#.#.#####.#.#####.#.#", "#.#.......#.......#.#",
      "#.#.#####.#.#####.#.#", "#...G...........G...#", "#####################",
    ],
  },
  arena: {
    label: "Arena",
    description: "An optional open-map stress test.",
    targetScore: 850,
    required: false,
    rows: [
      "#####################", "#P........#........G#", "#.###.###.#.###.###.#",
      "#.....#.......#.....#", "###.#.#.#####.#.#.###", "#...#.....G.....#...#",
      "#.###.###.#.###.###.#", "#G........#.........#", "#####################",
    ],
  },
};

export const CUSTOM_LEVEL_ID = "custom";
export const CUSTOM_LEVEL_LABEL = "My Level";
export const REQUIRED_LEVEL_IDS = Object.entries(LEVELS).filter(([, level]) => level.required).map(([id]) => id);
export const CUSTOM_LEVEL_MIN_FOOD = 10;
export const CUSTOM_LEVEL_ROWS = [
  "###############",
  "#P............#",
  "#.###.###.###.#",
  "#.............#",
  "#.###.#.#.###.#",
  "#.....#.#.....#",
  "#.###...###...#",
  "#G............#",
  "###############",
];

export const STARTER_CODE = `# Pacman Bot Lab
# You only need functions, variables, tuples, and lists.
#
# pacman:       (x, y) tuple
# food:         list of (x, y) tuples
# ghosts:       list of (x, y) tuples
# walls:        list of (x, y) tuples
# legal_actions: list containing UP, DOWN, LEFT, RIGHT, or STOP

def choose_action(pacman, food, ghosts, walls, legal_actions):
    best_action = "STOP"
    best_score = -100000

    for action in legal_actions:
        new_position = move(pacman, action)
        action_score = 0

        # Prefer positions closer to food.
        closest_food = 100000
        for pellet in food:
            pellet_distance = manhattan_distance(new_position, pellet)
            if pellet_distance < closest_food:
                closest_food = pellet_distance
        if food:
            action_score = action_score - closest_food * 2
        if new_position in food:
            action_score = action_score + 25

        # Avoid positions close to ghosts.
        for ghost in ghosts:
            ghost_distance = manhattan_distance(new_position, ghost)
            if ghost_distance == 0:
                action_score = action_score - 1000
            elif ghost_distance == 1:
                action_score = action_score - 120
            elif ghost_distance == 2:
                action_score = action_score - 35

        if action == "STOP":
            action_score = action_score - 5
        if action_score > best_score:
            best_score = action_score
            best_action = action

    return best_action
`;
