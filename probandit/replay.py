import logging
import sys

import yaml

from probandit.solver import Solver
from probandit.__main__ import eval_solvers


def read_csv(csv_file):
    with open(csv_file, 'r') as f:
        header = next(f).strip().split(',')
        body = []
        for line in f:
            row_values = []
            line = line.strip()
            pred_pos = line.find('"')

            # -1 skips trailing comma.
            for val in line[:pred_pos-1].split(','):
                row_values.append(int(val))

            [pred, raw] = line[pred_pos+1:].split('","')
            row_values.append(pred)
            row_values.append(raw[:-1])  # -1 removes trailing quote.

            body.append(row_values)

    results = []
    for row in body:
        result = {}
        for i, key in enumerate(header):
            result[key] = row[i]
        results.append(result)
    return results


def replay(result, target_solvers, reference_solvers, discard_socket_timeouts=False):
    pred = result['pred']
    logging.info('Replaying benchmark %s', pred)

    tar_results = eval_solvers(target_solvers.values(), pred, 1,
                               discard_socket_timeouts)
    ref_results = eval_solvers(reference_solvers.values(), pred, 1,
                               discard_socket_timeouts)

    tar_time = min([time for (answer, info, time) in tar_results.values()])
    ref_time = max([time for (answer, info, time) in ref_results.values()])

    replay_margin = tar_time - ref_time

    return replay_margin, ref_results | tar_results


def replay_results(results, target_solvers, reference_solvers,
                   independent=True, discard_socket_timeouts=False):
    counter = 0
    margin_factors = []
    margins = []
    for result in results:
        counter += 1
        orig_margin = result['margin']

        if orig_margin == 0:
            logging.info('Skipping benchmark %d with margin 0', counter)
            continue

        replay_margin, _ = replay(result, target_solvers, reference_solvers,
                                  discard_socket_timeouts=discard_socket_timeouts)

        margins.append(replay_margin)

        logging.info('Benchmark %d: Original margin %d, replay margin %d',
                     counter, orig_margin, replay_margin)
        margin_factors.append(replay_margin / orig_margin)

        if independent:
            # Reset all solvers; these are meant to be independent runs
            for solver in (target_solvers | reference_solvers).values():
                logging.debug('Restarting solver %s', solver.id)
                solver.restart()
    logging.info('Average margin factor: %f', sum(
        margin_factors) / len(margin_factors))

    return margins


if __name__ == '__main__':
    # First argument is the config file path
    if len(sys.argv) < 2:
        print("Usage: python probandit.py <config_file> <results_csv>")
        sys.exit(1)

    config_file = sys.argv[1]
    config = yaml.safe_load(open(config_file, 'r'))

    bf_options = config['fuzzer'].get('options', [])
    discard_socket_timeout = 'solutions_only' in bf_options

    csv_file = sys.argv[2]

    target_ids = config['fuzzer']['targets']
    target_solvers = {id: Solver(id=id, **(config['solvers'][id]))
                      for id in target_ids}
    for id, solver in target_solvers.items():
        logging.info('Starting solver %s', solver.id)
        solver.start()

    reference_ids = config['fuzzer']['references']
    reference_solvers = {id: Solver(id=id, **(config['solvers'][id]))
                         for id in reference_ids}
    for id, solver in reference_solvers.items():
        logging.info('Starting solver %s', solver.id)
        solver.start()

    logging.info('Reading results from %s', csv_file)
    results = read_csv(csv_file)

    logging.info('Replaying results independently')
    ind_margins = replay_results(results,
                                 target_solvers=target_solvers,
                                 reference_solvers=reference_solvers,
                                 independent=True,
                                 discard_socket_timeouts=discard_socket_timeout)

    logging.info('Replaying results without restarting solvers')
    dep_margins = replay_results(results,
                                 target_solvers=target_solvers,
                                 reference_solvers=reference_solvers,
                                 independent=False,
                                 discard_socket_timeouts=discard_socket_timeout)


    orig_margins = [result['margin'] for result in results]

    print('No.  ', '    Orig', '  Indiv.', '  % Orig', '    Dep.', '  % Orig')
    for i in range(len(orig_margins)):
        row = [
            f'# {i+1:03d}',
            f'{orig_margins[i]: 8d}',
            f'{ind_margins[i]: 8d}',
            f'{ind_margins[i]/orig_margins[i]: 4.2%}' if orig_margins[i] != 0 else '     N/A',
            f'{dep_margins[i]: 8d}',
            f'{ind_margins[i]/orig_margins[i]: 4.2%}' if orig_margins[i] != 0 else '     N/A',
        ]
        print(' '.join(row))
