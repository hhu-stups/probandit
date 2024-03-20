import logging
from math import ceil
import os
import sys
import yaml

from probandit.agents import BfAgent
from probandit.fuzzing import BFuzzer
from probandit.solver import Solver

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


def run_bf(bfuzzer, target_solvers, reference_solvers, csv):
    samp_size = 1
    for opt in bfuzzer.options:
        if opt.startswith('samp_size('):
            samp_size = int(opt.strip().split('(')[1][:-1])

    pred, raw_ast, env, best_margin, results = bf_iteration(bfuzzer,
                                                            None, None, None,
                                                            target_solvers,
                                                            reference_solvers,
                                                            samp_size)

    sids = merged_solver_ids(target_solvers, reference_solvers)
    write_results(csv, pred, raw_ast, results, best_margin, sids)

    actions = bfuzzer.list_actions(env)

    outer_agent = BfAgent(actions=['mutate', 'generate'])
    inner_agent = BfAgent(actions=actions)

    solution_filter = None
    if 'solutions_only' in bfuzzer.options:
        solution_filter = 'solutions_only'
    elif 'min_one_solution' in bfuzzer.options:
        solution_filter = 'min_one_solution'

    while True:
        outer_action = outer_agent.sample_action()
        if outer_action == 'mutate':
            mutation = inner_agent.sample_action()
        else:
            mutation = None

        logging.info("Action: (%s, %s)", outer_action, mutation)

        new_data = bf_iteration(bfuzzer, raw_ast, env, mutation,
                                target_solvers, reference_solvers,
                                samp_size)

        if new_data is None:
            logging.warning("Skipped iteration due to solver error")
            continue
        new_pred, new_raw_ast, new_env, new_margin, results = new_data

        # Check for contradictions
        solutions = 0
        contras = 0
        for res in results.values():
            if res[0] == 'yes':
                if res[1][0] == 'solution':
                    solutions += 1
                elif res[1][0] == 'contradiction_found':
                    contras += 1

        if solutions > 0 and contras > 0:
            yes_results = [f"{k}: {v[1][1]}"
                            for k, v in results.items() if v[0] == 'yes']
            yes_line = ', '.join(yes_results)
            logging.warning("CONTRADICTION FOUND: %s; on %s", yes_line, new_pred)
            with open('bf_contradictions.txt', 'a') as f:
                f.write(f"{yes_line}; {new_pred}\n")
            continue

        # Check if solution filter applies
        filter_applies = False
        if solution_filter:
            yes_types = set()
            for (answer, info, time) in results.values():
                if answer == 'yes':
                    typ = info[0]
                    if solution_filter == 'solutions_only':
                        if typ not in ['solution', 'contradiction_found']:
                            filter_applies = True
                    yes_types.add(info[0])
                elif solution_filter == 'solutions_only':
                    filter_applies = True

            if solution_filter == 'min_one_solution':
                has_contraduction = 'contradiction_found' in yes_types
                has_solution = 'solution' in yes_types
                if not (has_contraduction and has_solution):
                    filter_applies = True

            if filter_applies:
                logging.info("Ignore results due to solution filter %s",
                             solution_filter)

        if not filter_applies and new_margin > best_margin:
            logging.info("New best performance margin: %dms", new_margin)
            pred, raw_ast, env = new_pred, new_raw_ast, new_env
            best_margin = new_margin
            write_results(csv, pred, raw_ast, results, best_margin, sids)

            reward = 1
        else:
            reward = 0

        outer_agent.receive_reward(outer_action, reward)
        if mutation:
            inner_agent.receive_reward(mutation, reward)


def bf_iteration(bfuzzer, raw_ast, env, mutation, target_solvers, reference_solvers, samp_size=1):
    x, y, z, b = bfuzzer.get_random_state()
    logging.info("Prolog RNG: random(%d,%d,%d,%d)", x, y, z, b)

    try:
        if mutation == None:
            pred, raw_ast, env = bfuzzer.generate()
        else:
            pred, raw_ast, env = bfuzzer.mutate(raw_ast, env, mutation)
    except TimeoutError:
        logging.error("Timeout error for mutation '%s'", mutation)
        bfuzzer.restart()
        return None

    logging.info("Next predicate: %s", pred)
    logging.info("Raw AST: %s", raw_ast)

    ref_results = eval_solvers(reference_solvers, pred, env, samp_size)
    if ref_results is None:
        return None
    tar_results = eval_solvers(target_solvers, pred, env, samp_size)
    if tar_results is None:
        return None

    report_results(ref_results, label='Reference')
    report_results(tar_results, label='Target')

    # Get min ref and max target time
    penalty = target_solvers[0].solver_timeout
    ref_time = max([time for (answer, info, time) in ref_results.values()])
    tar_time = min([time for (answer, info, time) in tar_results.values()])

    new_performance_margin = tar_time - ref_time

    solver_results = ref_results | tar_results

    return pred, raw_ast, env, new_performance_margin, solver_results


def eval_solvers(solvers, pred, env, samp_size=1, par2=True):
    results = {}
    for solver in solvers:
        try:
            logging.debug("Solving with %s, 1/%d", solver.id, samp_size)
            answer, info, time = solver.solve(pred, env, par2=par2)
            if samp_size > 1:
                time_sum = time
                for i in range(samp_size - 1):
                    logging.debug("Solving again, %d/%d", i+2, samp_size)
                    _, _, new_time = solver.solve(pred, env, par2=par2)
                    time_sum += new_time
                time = ceil(time_sum / samp_size)
            results[solver.id] = (answer, info, time)
        except ValueError as e:
            logging.error("Parse error for %s over %s: %s", solver.id, pred, e)
            return None
        except TimeoutError:
            logging.error("Timeout error for %s over %s", solver.id, pred)
            solver.interrupt()
            return None
    return results


def report_results(results, label='Results'):
    result_parts = []
    for solver_id, (answer, info, time) in results.items():
        if answer == 'yes':
            answer = info[0]
        result_parts.append(f"{solver_id}: {answer} ({time}ms)")
    result_line = ', '.join(result_parts)
    logging.info(f"{label}: {result_line}")


def write_results(csv, pred, raw_ast, results, margin, sids):
    line = f"{margin},"
    for sid in sids:
        if sid in results:
            line += f"{results[sid][2]},"
        else:
            line += ","
    line += f"\"{pred}\",\"{raw_ast}\"\n"
    csv.write(line)
    csv.flush()


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


def merged_solver_ids(target_solvers, reference_solvers):
    sids = [s.id for s in reference_solvers] + [s.id for s in target_solvers]
    return sorted(sids)


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

    port = config['fuzzer'].get('port', None)
    bfuzzer.connect(existing_port=port)
    bfuzzer.init_random_state()


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

    outfile = config['fuzzer'].get('csv', 'results.csv')

    with open(outfile, 'w') as csv:
        sids = merged_solver_ids(target_solvers, reference_solvers)
        header = 'margin,'
        header += ','.join(sids)
        header += ',pred,raw_ast\n'
        csv.write(header)
        run_bf(bfuzzer, target_solvers, reference_solvers, csv)
