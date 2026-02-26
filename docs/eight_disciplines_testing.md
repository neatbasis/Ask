# Testing seams and pytest fixture strategy for Eight Disciplines input flow

This note captures the deterministic testing approach for an `EightDisciplines`/customer-issue CLI-style flow, where methods accept injectable I/O and a mutable `defaults` state map.

## Context

Example shape:

```python
class IssueCollector:
    def __init__(self, issue):
        self.EIGHT_DISCIPLINES = [
            'plan',
            'prerequisites',
            'team',
            'problem_description',
            'interim_containment_plan',
            'root_causes',
            'permanent_corrections',
            'corrective_actions',
            'preventive_measures',
        ]
        self.issue = issue
        self.feedback = []
```

In pytest terms, fixtures should target **dependency-injection seams** so tests stay deterministic and do not rely on real user interaction.

## Primary fixture points

### 1) Injectable I/O (`input_fn`, `print_fn`) — highest priority

Functions that accept these seams can be tested with scripted inputs and captured output:

- `prompt_for_rating(input_fn, print_fn)`
- `prompt_yn(prompt, default, input_fn, print_fn)`
- `prompt_text(prompt, allow_skip, input_fn)`
- `get_input(..., input_fn, print_fn)`
- `get_list_input(..., input_fn, print_fn)`
- `get_customer_contact(defaults, input_fn, print_fn)`
- `get_eight_disciplines_inputs(defaults, interactive=True, input_fn, print_fn)`
- `get_customer_feedback(defaults, input_fn, print_fn)`

### 2) `defaults` state fixture

Most `get_*` functions read/mutate a shared `defaults` dictionary. This should be a fixture so tests can cover both empty and pre-filled state.

Key call sites:

- `get_customer_contact(defaults, ...)`
- `get_issue(defaults)` / `CustomerIssue.from_defaults(defaults)`
- `get_eight_disciplines_inputs(defaults, ...)`
- `get_customer_feedback(defaults, ...)`

### 3) Interactive switch fixture (`interactive: bool`)

`get_eight_disciplines_inputs(..., interactive=False)` is a strong seam for normalization-focused tests with no prompting.

### 4) Pure normalization helpers (unit-level targets)

Even though these are not fixtures, test these directly because they define input semantics:

- `_normalize_optional`
- `_has_value`
- `_normalize_optional_list`
- `_has_list_value`

## Recommended pytest fixtures

```python
import pytest

@pytest.fixture
def inputs():
    # Override per test as needed
    return []

@pytest.fixture
def input_fn(inputs):
    queue = list(inputs)

    def _input(_prompt=""):
        if not queue:
            raise AssertionError("No scripted input left")
        return queue.pop(0)

    return _input

@pytest.fixture
def printed():
    return []

@pytest.fixture
def print_fn(printed):
    def _print(*args, **kwargs):
        printed.append(" ".join(str(a) for a in args))
    return _print

@pytest.fixture
def defaults():
    return {
        "customer_name": "",
        "customer_phone": "",
        "customer_email": "",
    }
```

## Suggested test matrix

1. Input validation paths for yes/no, rating, and free text (including retries).
2. Defaults handling: empty defaults and pre-populated defaults.
3. Non-interactive normalization path (`interactive=False`).
4. Round-trip checks for `from_defaults()` and `to_defaults()`.
5. Direct helper tests for normalization utilities.
