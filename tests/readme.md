Run these locally with

```
python -m unittest
```

or use `-s` to print logging to terminal

```
pytest -s tests
```

Run one test function

```
test_table_view
pytest tests/interface/test_plugins.py::test_table_view
pytest tests/interface/test_plugins.py::test_app
pytest tests/interface/test_plugins.py::test_init
```
