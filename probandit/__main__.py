import logging
import os
import sys
import yaml

from probandit.fuzzing import BFuzzer
from probandit.solver import Solver

logging.basicConfig(level=logging.INFO)


def run_bf(bfuzzer, target_solvers, reference_solvers):
    bfuzzer.connect()
    bfuzzer.init_random_state()

    pred, raw_ast, env, margin = bf_iteration(bfuzzer, None, None, None,
                                              target_solvers,
                                              reference_solvers)

    for i in range(10):
        new_data = bf_iteration(bfuzzer, raw_ast, env, None,
                                target_solvers,
                                reference_solvers)

        if new_data is None:
            logging.warning("Skipped iteration due to solver error")
            continue
        new_pred, new_raw_ast, new_env, new_margin = new_data

        if new_margin > margin:
            logging.info("New best performance margin: %dms", new_margin)
            pred, raw_ast, env, margin = new_data


def bf_iteration(bfuzzer, raw_ast, env, mutation, target_solvers, reference_solvers):
    x, y, z, b = bfuzzer.get_random_state()
    logging.info("Prolog RNG: random(%d,%d,%d,%d)", x, y, z, b)
    if mutation == None:
        pred, raw_ast, env = bfuzzer.generate()
    else:
        pred, raw_ast, env = bfuzzer.mutate(raw_ast, env, mutation)

    logging.info("Next predicate: %s", pred)
    logging.info("Raw AST: %s", raw_ast)

    ref_results = eval_solvers(reference_solvers, pred, env)
    tar_results = eval_solvers(target_solvers, pred, env)

    if ref_results is None or tar_results is None:
        return None

    report_results(ref_results, label='Reference')
    report_results(tar_results, label='Target')

    # Get min ref and max target time
    ref_time = max([time for (answer, info, time) in ref_results.values()])
    tar_time = min([time for (answer, info, time) in tar_results.values()])

    new_performance_margin = tar_time - ref_time

    return pred, raw_ast, env, new_performance_margin


def eval_solvers(solvers, pred, env):
    results = {}
    for solver in solvers:
        try:
            answer, info, time = solver.solve(pred, env)
        except ValueError as e:
            logging.error("Parse error for %s over %s: %s", solver.id, pred, e)
            return None
        results[solver.id] = (answer, info, time)
    return results


def report_results(results, label='Results'):
    result_parts = []
    for solver_id, (answer, info, time) in results.items():
        if answer == 'yes':
            answer = info[0]
        result_parts.append(f"{solver_id}: {answer} ({time}ms)")
    result_line = ', '.join(result_parts)
    logging.info(f"{label}: {result_line}")


def correct_bf_path(bf_path):
    if not os.path.exists(bf_path):
        raise ValueError(
            f"Path to the BanditFuzzer at {bf_path} does not exist")

    # Check if the path is a file or a directory
    if os.path.isdir(bf_path):
        # It can be either the ProB directory or the BanditFuzz directory
        if os.path.exists(os.path.join(bf_path, 'banditfuzz.pl')):
            return os.path.join(bf_path, 'banditfuzz.pl')
        return os.path.join(bf_path, 'extensions', 'banditfuzz', 'banditfuzz.pl')
    else:
        return bf_path


if __name__ == '__main__':
    # First argument is the config file path
    if len(sys.argv) < 2:
        print("Usage: python probandit.py <config_file>")
        sys.exit(1)

    config_file = sys.argv[1]
    config = yaml.safe_load(open(config_file, 'r'))

    bf_path = os.path.expandvars(config['fuzzer']['path'])
    bf_path = correct_bf_path(bf_path)
    logging.info(f"Using BanditFuzzer at {bf_path}")

    bfuzzer = BFuzzer(bf_path=bf_path,
                      options=config['fuzzer'].get('options', []))

    target_is = config['fuzzer']['targets']
    target_solvers = [Solver(id=id, **(config['solvers'][id]))
                      for id in target_is]
    for solver in target_solvers:
        solver.start()

    reference_is = config['fuzzer']['references']
    reference_solvers = [Solver(id=id, **(config['solvers'][id]))
                         for id in reference_is]
    for solver in reference_solvers:
        solver.start()

    run_bf(bfuzzer, target_solvers, reference_solvers)
