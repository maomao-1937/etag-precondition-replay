# Verification

```sh
python -I -m unittest discover -s tests -v
python -I examples/run_examples.py
```

The CLI tests exercise condition precedence, strong and weak matching, case-sensitive methods, representation existence with and without a current tag, quoted commas and backslashes, Latin-1 octets, empty lists, bounded input and output failures. The example runner checks both exit codes and complete JSON reports from the example files. GitHub Actions runs both commands on Ubuntu and Windows with Python 3.11.
