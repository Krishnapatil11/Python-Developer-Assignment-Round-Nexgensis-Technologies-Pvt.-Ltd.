"""
================================================================================
FastBox Mystery Delivery System
================================================================================
Author  : FastBox Logistics Simulator
Purpose : Simulate one full day of delivery operations for FastBox.
          - Reads warehouse, agent, and package data from data.json
          - Assigns each package to the nearest available agent
          - Simulates pickup → delivery routes with distance tracking
          - Applies random delivery delays (Bonus)
          - Renders ASCII route map (Bonus)
          - Handles a new agent joining mid-day (Bonus)
          - Exports top performer to CSV (Bonus)
          - Saves final report to report.json
================================================================================
"""

import sys           # For stdout encoding fix
import json          # For reading/writing JSON files
import math          # For Euclidean distance (math.sqrt)
import random        # For bonus: random delivery delays
import csv           # For bonus: CSV export
import os            # For file path management
import time          # For delay simulation output

# Fix Windows console encoding to support all characters
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 : UTILITY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def euclidean_distance(point_a: list, point_b: list) -> float:
    """
    Calculate straight-line (Euclidean) distance between two 2D coordinates.

    Formula: sqrt((x2-x1)^2 + (y2-y1)^2)

    Args:
        point_a : [x, y] coordinate of the first point
        point_b : [x, y] coordinate of the second point

    Returns:
        Float distance rounded to 4 decimal places.
    """
    dx = point_b[0] - point_a[0]
    dy = point_b[1] - point_a[1]
    return round(math.sqrt(dx ** 2 + dy ** 2), 4)


def load_data(filepath: str) -> dict:
    """
    Read and parse the JSON input file.

    Args:
        filepath : Path to data.json

    Returns:
        Parsed dictionary with 'warehouses', 'agents', 'packages' keys.

    Raises:
        FileNotFoundError if the file doesn't exist.
        json.JSONDecodeError if the file contains invalid JSON.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"[ERROR] Data file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)   # Parse JSON → Python dict

    # Basic validation
    required_keys = {"warehouses", "agents", "packages"}
    missing = required_keys - data.keys()
    if missing:
        raise ValueError(f"[ERROR] Missing required keys in data.json: {missing}")

    print(f"[✔] Data loaded from '{filepath}'")
    print(f"    Warehouses : {list(data['warehouses'].keys())}")
    print(f"    Agents     : {list(data['agents'].keys())}")
    print(f"    Packages   : {[p['id'] for p in data['packages']]}")
    return data


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 : PACKAGE → AGENT ASSIGNMENT
# ─────────────────────────────────────────────────────────────────────────────

def assign_packages_to_agents(packages: list, agents: dict, warehouses: dict) -> dict:
    """
    Assign every package to the nearest agent based on Euclidean distance
    from the agent's current position to the package's warehouse.

    Strategy: For each package, iterate over all agents and pick the one
              with the minimum distance to that package's warehouse.

    Args:
        packages   : List of package dicts (id, warehouse, destination)
        agents     : Dict of agent_id → [x, y] position
        warehouses : Dict of warehouse_id → [x, y] position

    Returns:
        assignment : Dict mapping agent_id → list of package dicts assigned to them
    """
    # Initialise empty list for every agent
    assignment = {agent_id: [] for agent_id in agents}

    print("\n[STEP 2] Assigning packages to nearest agents …")
    print(f"{'Package':<10} {'Warehouse':<12} {'Nearest Agent':<15} {'Distance':>10}")
    print("-" * 52)

    for pkg in packages:
        warehouse_id  = pkg["warehouse"]
        warehouse_pos = warehouses[warehouse_id]

        best_agent    = None
        best_distance = float("inf")   # Start with an infinitely large distance

        # Check every agent and track the closest one to this warehouse
        for agent_id, agent_pos in agents.items():
            dist = euclidean_distance(agent_pos, warehouse_pos)
            if dist < best_distance:
                best_distance = dist
                best_agent    = agent_id

        # Assign package to the nearest agent
        assignment[best_agent].append(pkg)
        print(f"{pkg['id']:<10} {warehouse_id:<12} {best_agent:<15} {best_distance:>10.4f}")

    return assignment


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 : DELIVERY SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def simulate_deliveries(
    assignment: dict,
    agents: dict,
    warehouses: dict,
    apply_delays: bool = True
) -> dict:
    """
    Simulate each agent's delivery route for the day.

    Route for each package:
        Agent's current position → Warehouse (pick-up) → Destination (drop-off)

    After delivering a package, the agent's position updates to the destination,
    so multiple packages compound the total distance realistically.

    Args:
        assignment   : Output of assign_packages_to_agents()
        agents       : Dict of agent_id → [x, y] starting position
        warehouses   : Dict of warehouse_id → [x, y] position
        apply_delays : If True, add random delay simulation (Bonus feature)

    Returns:
        results : Dict with per-agent delivery statistics and log entries.
    """
    results = {}

    print("\n[STEP 3] Simulating deliveries …\n")

    for agent_id, packages in assignment.items():
        # Agent starts at their initial position (make a copy to avoid mutation)
        current_pos      = list(agents[agent_id])
        total_distance   = 0.0
        delivered_log    = []   # Detailed log of each delivery

        print(f"  Agent {agent_id} (start: {current_pos})")

        if not packages:
            print(f"    ↳ No packages assigned. Agent stays idle.\n")
            results[agent_id] = {
                "packages_delivered": 0,
                "total_distance"    : 0.0,
                "efficiency"        : 0.0,
                "log"               : []
            }
            continue

        for pkg in packages:
            warehouse_pos = warehouses[pkg["warehouse"]]
            destination   = pkg["destination"]

            # Leg 1: Travel from current position to the warehouse
            d_to_warehouse = euclidean_distance(current_pos, warehouse_pos)

            # Leg 2: Travel from warehouse to the delivery destination
            d_to_dest      = euclidean_distance(warehouse_pos, destination)

            leg_total = d_to_warehouse + d_to_dest
            total_distance += leg_total

            # ── Bonus: Random Delay ────────────────────────────────────────
            delay_minutes = 0
            if apply_delays:
                # 40% chance of a delay between 5 and 30 minutes
                if random.random() < 0.4:
                    delay_minutes = random.randint(5, 30)

            # Update agent's position to the delivery destination
            current_pos = list(destination)

            # Build a log entry for this delivery
            log_entry = {
                "package"           : pkg["id"],
                "warehouse"         : pkg["warehouse"],
                "destination"       : destination,
                "dist_to_warehouse" : round(d_to_warehouse, 4),
                "dist_to_dest"      : round(d_to_dest, 4),
                "leg_total"         : round(leg_total, 4),
                "delay_minutes"     : delay_minutes,
                "status"            : "DELIVERED"
            }
            delivered_log.append(log_entry)

            delay_note = f"  ⏱ Delayed by {delay_minutes} min" if delay_minutes else ""
            print(
                f"    [PKG] {pkg['id']} | {pkg['warehouse']} -> dest{destination} "
                f"| dist: {leg_total:.2f}{delay_note}"
            )

        # ── Efficiency = total_distance / packages_delivered ────────────────
        # Lower is better (less distance per package)
        packages_delivered = len(packages)
        efficiency = round(total_distance / packages_delivered, 4) if packages_delivered else 0.0

        total_distance = round(total_distance, 4)

        results[agent_id] = {
            "packages_delivered": packages_delivered,
            "total_distance"    : total_distance,
            "efficiency"        : efficiency,
            "log"               : delivered_log
        }

        print(
            f"    ─ Total distance: {total_distance:.4f} | "
            f"Packages: {packages_delivered} | Efficiency: {efficiency:.4f}\n"
        )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 : BONUS – NEW AGENT JOINING MID-DAY
# ─────────────────────────────────────────────────────────────────────────────

def add_midday_agent(agents: dict, new_agent_id: str, position: list) -> dict:
    """
    (Bonus) Simulate a new delivery agent joining operations mid-day.

    The new agent is added to the agents dictionary so that future
    (re-)assignments can consider them.

    Args:
        agents       : Existing agents dictionary
        new_agent_id : Identifier for the new agent (e.g., "A4")
        position     : [x, y] starting coordinates

    Returns:
        Updated agents dictionary with the new agent included.
    """
    if new_agent_id in agents:
        print(f"[⚠] Agent {new_agent_id} already exists. Skipping.")
        return agents

    agents[new_agent_id] = position
    print(f"\n[BONUS] New agent '{new_agent_id}' joined mid-day at position {position}!")
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 : BONUS – ASCII ROUTE MAP
# ─────────────────────────────────────────────────────────────────────────────

def draw_ascii_map(warehouses: dict, agents: dict, packages: list, grid_size: int = 20):
    """
    (Bonus) Render a simplified ASCII grid map showing warehouse (W),
    agent (A), and package destination (P) positions.

    The world coordinates are scaled down to fit within grid_size × grid_size.

    Args:
        warehouses : Dict of warehouse positions
        agents     : Dict of agent positions
        packages   : List of package dicts
        grid_size  : Size of the ASCII canvas (default 20×20)
    """
    # Find world bounds for coordinate scaling
    all_x = ([v[0] for v in warehouses.values()] +
              [v[0] for v in agents.values()]     +
              [p["destination"][0] for p in packages])
    all_y = ([v[1] for v in warehouses.values()] +
              [v[1] for v in agents.values()]     +
              [p["destination"][1] for p in packages])

    max_x = max(all_x) or 1
    max_y = max(all_y) or 1

    # Build empty grid
    grid = [["·" for _ in range(grid_size)] for _ in range(grid_size)]

    def scale(val, max_val):
        """Map world coordinate to grid index."""
        return min(int(val / max_val * (grid_size - 1)), grid_size - 1)

    # Plot warehouses
    for wid, pos in warehouses.items():
        gx, gy = scale(pos[0], max_x), scale(pos[1], max_y)
        grid[grid_size - 1 - gy][gx] = f"W"   # Y-axis flipped for readability

    # Plot agents
    for aid, pos in agents.items():
        gx, gy = scale(pos[0], max_x), scale(pos[1], max_y)
        grid[grid_size - 1 - gy][gx] = "A"

    # Plot package destinations
    for pkg in packages:
        gx, gy = scale(pkg["destination"][0], max_x), scale(pkg["destination"][1], max_y)
        grid[grid_size - 1 - gy][gx] = "P"

    print("\n[BONUS] ASCII Route Map (W=Warehouse, A=Agent, P=Package Dest, ·=Empty)")
    print("┌" + "─" * (grid_size * 2) + "┐")
    for row in grid:
        print("│ " + " ".join(row) + " │")
    print("└" + "─" * (grid_size * 2) + "┘")

    # Legend
    print("  Legend: W=Warehouse  A=Agent  P=Package Destination  ·=Empty\n")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 : REPORT GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_report(results: dict) -> dict:
    """
    Build the final summary report from simulation results.

    Determines the best agent as the one with the LOWEST efficiency score
    (i.e., least distance travelled per package delivered).

    Args:
        results : Dict returned by simulate_deliveries()

    Returns:
        report : Dict containing per-agent stats and 'best_agent' key.
    """
    report = {}
    best_agent    = None
    best_score    = float("inf")   # We want the MINIMUM efficiency

    for agent_id, stats in results.items():
        report[agent_id] = {
            "packages_delivered": stats["packages_delivered"],
            "total_distance"    : stats["total_distance"],
            "efficiency"        : stats["efficiency"]
        }
        # Only consider agents who actually delivered something
        if stats["packages_delivered"] > 0 and stats["efficiency"] < best_score:
            best_score = stats["efficiency"]
            best_agent = agent_id

    report["best_agent"] = best_agent
    return report


def save_report(report: dict, filepath: str):
    """
    Write the final report dictionary to a JSON file with pretty formatting.

    Args:
        report   : Dict produced by generate_report()
        filepath : Destination path for report.json
    """
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print(f"[✔] Report saved to '{filepath}'")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 : BONUS – CSV EXPORT OF TOP PERFORMER
# ─────────────────────────────────────────────────────────────────────────────

def export_top_performer_csv(report: dict, results: dict, filepath: str):
    """
    (Bonus) Export the best agent's detailed delivery log to a CSV file.

    Columns: Package, Warehouse, Destination, Dist_To_Warehouse,
             Dist_To_Dest, Leg_Total, Delay_Minutes, Status

    Args:
        report   : Final report dict (contains 'best_agent' key)
        results  : Full simulation results with per-package logs
        filepath : Output CSV file path
    """
    best_agent = report.get("best_agent")
    if not best_agent:
        print("[⚠] No best agent found. CSV not exported.")
        return

    log = results[best_agent].get("log", [])

    fieldnames = [
        "package", "warehouse", "destination",
        "dist_to_warehouse", "dist_to_dest",
        "leg_total", "delay_minutes", "status"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for entry in log:
            # Flatten destination list to string for CSV readability
            row = dict(entry)
            row["destination"] = str(row["destination"])
            writer.writerow(row)

    print(f"[✔] Top performer ({best_agent}) CSV saved to '{filepath}'")


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 : MAIN ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("        FastBox Mystery Delivery System")
    print("=" * 60)

    # ── File Paths ──────────────────────────────────────────────────────────
    BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
    DATA_FILE   = os.path.join(BASE_DIR, "data.json")
    REPORT_FILE = os.path.join(BASE_DIR, "report.json")
    CSV_FILE    = os.path.join(BASE_DIR, "top_performer.csv")

    # ── Step 1: Load & Parse JSON ────────────────────────────────────────────
    print("\n[STEP 1] Loading data …")
    data       = load_data(DATA_FILE)
    warehouses = data["warehouses"]
    agents     = data["agents"]
    packages   = data["packages"]

    # ── Bonus: New Agent Joins Mid-Day ────────────────────────────────────────
    # A new agent "A4" joins at position [25, 50] after morning operations
    agents = add_midday_agent(agents, "A4", [25, 50])

    # ── Bonus: ASCII Map ──────────────────────────────────────────────────────
    draw_ascii_map(warehouses, agents, packages)

    # ── Step 2: Assign Packages to Nearest Agent ─────────────────────────────
    assignment = assign_packages_to_agents(packages, agents, warehouses)

    # ── Step 3: Simulate Deliveries (with random delays as bonus) ────────────
    random.seed(42)   # Fix seed for reproducible results; remove for true randomness
    results = simulate_deliveries(assignment, agents, warehouses, apply_delays=True)

    # ── Step 4: Generate Summary Report ─────────────────────────────────────
    print("[STEP 4] Generating report …")
    report = generate_report(results)

    # ── Step 5: Save Report to report.json ───────────────────────────────────
    print("[STEP 5] Saving report …")
    save_report(report, REPORT_FILE)

    # ── Bonus: Export Top Performer to CSV ───────────────────────────────────
    export_top_performer_csv(report, results, CSV_FILE)

    # ── Print Final Report to Console ────────────────────────────────────────
    print("\n" + "=" * 60)
    print("           📋  FINAL DELIVERY REPORT")
    print("=" * 60)
    for agent_id, stats in report.items():
        if agent_id == "best_agent":
            continue
        print(
            f"  {agent_id} → Delivered: {stats['packages_delivered']}  |  "
            f"Distance: {stats['total_distance']:.2f}  |  "
            f"Efficiency: {stats['efficiency']:.2f}"
        )
    print(f"\n  🏆  Best Agent (most efficient): {report['best_agent']}")
    print("=" * 60)

    # ── Validate: Total packages check ───────────────────────────────────────
    total_delivered = sum(
        v["packages_delivered"]
        for k, v in report.items()
        if k != "best_agent"
    )
    print(f"\n  ✅ Total packages delivered: {total_delivered} / {len(packages)}")
    if total_delivered != len(packages):
        print("  ⚠ WARNING: Package count mismatch! Some packages may be undelivered.")

    print("\n[DONE] Simulation complete.\n")


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()
