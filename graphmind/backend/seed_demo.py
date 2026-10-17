from backend.graph_db import get_database


def main():
    database = get_database()
    database.seed_demo_data()
    print("GraphMind demo data is ready.")
    print(f"Connected to graph: {database.graph.name if hasattr(database.graph, 'name') else 'graphmind'}")
    print("Seed operation is repeatable; existing demo IDs are merged, not duplicated.")


if __name__ == "__main__":
    main()
