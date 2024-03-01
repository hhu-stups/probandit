# ProBandit

An external banditfuzzer for ProB.

This is an extension of the original ProB banditfuzz extension which uses
external fuzzing.
External fuzzing hereby means that ProBandit is called in an external instance,
independent from the ProB instance under test.
This approach allows ProBandit to target different versions of ProB at the
same time rather than being bound to one singular version.

## Calling ProBandit

Dependencies:

* Python 3.8+

Run with `python3 -m probandit <config file path>`.

## Configuration Files

The configuration files are in YAML format and follow a simple pattern
consisting of two sections: `fuzzer` and `solvers`:

```yaml
fuzzer:
  path: <path string>
  targets:
    - <solver list>
  references:
    - <solver list>
  options:
    - <option list>

solvers:
  <solver name>:
    <setting>: <value>
```

### Fuzzer configuration

* `path`: Directory path to the ProB version with the desired fuzzer
  implementation. This does not necessarily have to be a ProB version which is
  used as target or reference solver.
  Rather, this instance is queried for the Banditfuzz generator and mutator
  capabilities to create and manipulate inputs for the solvers under test.

  **Note:** Available environment variables can be used and will be expanded,
  e.g. `$PROBDIR` (or any available variable).

* `targets`: A list of target solvers to use in this ProBandit run. The solvers
  need to be defined under the `solvers:`-section (see below).
* `references`: A list of reference solvers to use in this ProBandit run. The
  solvers need to be defined under the `solvers:`-section (see below).
* `options`: A list of options that is forwarded to the Banditfuzz
  implementation linked under the `path` setting. See the respective
  readme for more information as of which options are available.

### Solver configuration

Under the `solvers:`-section, the user can define custom identifiers for
each needed configuration of ProB that should be tested.
For instance, defining two different versions of ProB as available solvers
might look like this:

```yaml
solvers:
  prob_1.13.0: /* Config for ProB 1.13.0 */
  prob_1.12.3: /* Config for ProB 1.12.3 */
```

The respective solver configuration options are as follows:

* `path`: Path to the ProB distribution. If the path is a directory, ProBandit
  will attempt to access the `probcli` executable therein.

  **Note:** Available environment variables can be used and will be expanded,
  e.g. `$PROBDIR` (or any available variable).


## References

The original ProB BanditFuzz article. This work is an extension in that it
makes use of external fuzzing as described above.

```bibtex
@InProceedings(dunkelau2023banditfuzz,
  Author    = {Dunkelau, Jannik and Leuschel, Michael},
  Title     = {Performance Fuzzing with Reinforcement-Learning and Well-Defined Constraints for the {B} Method},
  Booktitle = {iFM 2023},
  Year      = 2023,
  Month     = nov,
  Series    = {LNCS},
  Volume    = 14300,
  Pages     = {237--256},
  Publisher = {Springer},
  doi       = {10.1007/978-3-031-47705-8_13}
)
```
