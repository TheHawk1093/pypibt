import argparse
import time
from datetime import datetime
from pathlib import Path

from pypibt import (
    PIBT,
    get_grid,
    get_scenario,
    is_valid_mapf_solution,
    save_configs_for_visualizer,
)

# Create results directory
RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)


def calculate_metrics(plan, starts, goals, computation_time):
    """Calculate solution metrics"""
    if not plan:
        return {'success': False, 'computation_time': computation_time}
    
    number_of_agents = len(starts)
    makespan = len(plan) - 1
    
    # Calculate sum of costs (total path lengths)
    sum_of_costs = 0
    for agent_id in range(number_of_agents):
        goal_position = goals[agent_id]
        agent_path_length = 0
        for timestep in range(len(plan)):
            if plan[timestep][agent_id] != goal_position:
                agent_path_length = timestep + 1
        sum_of_costs += agent_path_length
    
    # Check if all agents reached their goals
    final_positions = plan[-1]
    all_reached_goals = all(final_positions[i] == goals[i] for i in range(number_of_agents))
    
    return {
        'number_of_agents': number_of_agents,
        'success': all_reached_goals,
        'makespan': makespan,
        'sum_of_costs': sum_of_costs,
        'average_path_length': sum_of_costs / number_of_agents,
        'total_timesteps': len(plan),
        'computation_time': computation_time
    }


def save_metrics_to_file(metrics, configuration, output_path):
    """Save metrics to file"""
    with open(output_path, 'w') as file:
        file.write("PIBT EXECUTION RESULTS\n")
        file.write("=" * 70 + "\n\n")
        
        file.write("CONFIGURATION:\n")
        file.write(f"  Map File:         {configuration['map_file']}\n")
        file.write(f"  Scenario File:    {configuration['scenario_file']}\n")
        file.write(f"  Number of Agents: {configuration['number_of_agents']}\n")
        file.write(f"  Random Seed:      {configuration['random_seed']}\n")
        file.write(f"  Execution Time:   {configuration['timestamp']}\n\n")
        
        if metrics['success']:
            file.write("SOLUTION METRICS:\n")
            file.write(f"  Status:                SUCCESS\n")
            file.write(f"  Makespan:              {metrics['makespan']}\n")
            file.write(f"  Sum of Costs:          {metrics['sum_of_costs']}\n")
            file.write(f"  Average Path Length:   {metrics['average_path_length']:.2f}\n")
            file.write(f"  Total Timesteps:       {metrics['total_timesteps']}\n")
            file.write(f"  Computation Time:      {metrics['computation_time']:.4f} seconds\n")
            file.write(f"  Time per Agent:        {metrics['computation_time']/metrics['number_of_agents']:.6f} seconds\n")
        else:
            file.write("SOLUTION METRICS:\n")
            file.write(f"  Status:                FAILED\n")
            file.write(f"  Computation Time:      {metrics['computation_time']:.4f} seconds\n")


def generate_output_name(map_file_path, scenario_file_path, number_of_agents, random_seed):
    """Generate output name from map and scenario file names"""
    # Extract filenames without extensions
    map_name = Path(map_file_path).stem
    scenario_name = Path(scenario_file_path).stem
    
    # Build output name: map_scenario_agentsN_seedS
    output_name = f"{map_name}_{scenario_name}_agents{number_of_agents}_seed{random_seed}"
    
    return output_name


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='PIBT Multi-Agent Path Finding Solver')
    parser.add_argument(
        "-m", "--map-file",
        type=str,
        default="assets/random-32-32-10.map",
        help="Path to map file"
    )
    parser.add_argument(
        "-i", "--scenario-file",
        type=str,
        default="assets/random-32-32-10-random-1.scen",
        help="Path to scenario file"
    )
    parser.add_argument(
        "-N", "--number-of-agents",
        type=int,
        default=200,
        help="Number of agents to use"
    )
    parser.add_argument(
        "-s", "--random-seed",
        type=int,
        default=0,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--max-timestep",
        type=int,
        default=1000,
        help="Maximum timesteps allowed"
    )
    arguments = parser.parse_args()
    
    # Display loading information
    map_filename = Path(arguments.map_file).name
    scenario_filename = Path(arguments.scenario_file).name
    print(f"Loading map: {map_filename}")
    print(f"Loading scenario: {scenario_filename}")
    print(f"Number of agents: {arguments.number_of_agents}")
    
    # Load problem instance
    grid = get_grid(arguments.map_file)
    start_positions, goal_positions = get_scenario(arguments.scenario_file, arguments.number_of_agents)
    
    # Generate output name automatically from input files
    output_base_name = generate_output_name(
        arguments.map_file,
        arguments.scenario_file,
        arguments.number_of_agents,
        arguments.random_seed
    )
    output_paths_file = RESULTS_DIR / f"output_{output_base_name}.txt"
    output_metrics_file = RESULTS_DIR / f"metrics_{output_base_name}.txt"
    
    # Solve MAPF problem
    print("\nRunning PIBT algorithm...")
    start_time = time.time()
    pibt_solver = PIBT(grid, start_positions, goal_positions, seed=arguments.random_seed)
    solution_plan = pibt_solver.run(max_timestep=arguments.max_timestep)
    computation_time = time.time() - start_time
    
    # Validate and calculate metrics
    solution_is_valid = is_valid_mapf_solution(grid, start_positions, goal_positions, solution_plan)
    metrics = calculate_metrics(solution_plan, start_positions, goal_positions, computation_time)
    
    # Display results
    if metrics['success']:
        print(f"Status: SUCCESS")
        print(f"Makespan: {metrics['makespan']}")
        print(f"Sum of Costs: {metrics['sum_of_costs']}")
        print(f"Computation Time: {computation_time:.4f} seconds")
    else:
        print(f"Status: FAILED")
        print(f"Computation Time: {computation_time:.4f} seconds")
    
    # Save results to files
    print(f"\nSaving results to:")
    save_configs_for_visualizer(solution_plan, str(output_paths_file))
    print(f"  Paths: {output_paths_file}")
    
    configuration = {
        'map_file': arguments.map_file,
        'scenario_file': arguments.scenario_file,
        'number_of_agents': arguments.number_of_agents,
        'random_seed': arguments.random_seed,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_metrics_to_file(metrics, configuration, output_metrics_file)
    print(f"  Metrics: {output_metrics_file}")
    
    print("\nExecution complete.")


if __name__ == "__main__":
    main()
