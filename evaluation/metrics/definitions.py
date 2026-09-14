"""
Mathematical definitions and documentation for evaluation metrics.

Precision = TP / (TP + FP)
Recall    = TP / (TP + FN)
F1        = 2 * (Precision * Recall) / (Precision + Recall)

Zero-Denominator Policy:
- If (TP + FP) == 0:
    - If FN == 0 (Clean Scenario: zero expected, zero predicted): Precision is 1.0.
    - If FN > 0 (System missed issues without predicting anything): Precision is 0.0.
- If (TP + FN) == 0:
    - If FP == 0: Recall is 1.0.
    - If FP > 0: Recall is 0.0.
- If (Precision + Recall) == 0:
    - F1 is 0.0.
- Never produce NaN or unhandled ZeroDivisionError.
"""


def calculate_precision(tp: int, fp: int, fn: int = 0) -> float:
    """Calculate precision with explicit safe zero-denominator handling."""
    denominator = tp + fp
    if denominator == 0:
        # Zero predicted findings: if zero expected, perfect precision (clean PR); else 0.0
        return 1.0 if fn == 0 else 0.0
    return round(float(tp) / float(denominator), 4)


def calculate_recall(tp: int, fn: int) -> float:
    """Calculate recall with explicit safe zero-denominator handling."""
    denominator = tp + fn
    if denominator == 0:
        # Zero expected findings: no issues to recall, perfect score
        return 1.0
    return round(float(tp) / float(denominator), 4)


def calculate_f1(precision: float, recall: float) -> float:
    """Calculate F1 harmonic mean with safe zero-denominator handling."""
    denominator = precision + recall
    if denominator <= 0.0:
        return 0.0
    return round(2.0 * (precision * recall) / denominator, 4)


def calculate_rate(numerator: int, denominator: int, default: float = 0.0) -> float:
    """Safely calculate percentage rate (0.0 to 1.0)."""
    if denominator <= 0:
        return default
    return round(float(numerator) / float(denominator), 4)


def calculate_category_accuracy(matched: int, total: int) -> float:
    """Safely calculate category prediction accuracy."""
    return calculate_rate(matched, total)


def calculate_severity_accuracy(matched: int, total: int) -> float:
    """Safely calculate severity prediction accuracy."""
    return calculate_rate(matched, total)


def calculate_line_accuracy(matched: int, total: int) -> float:
    """Safely calculate line mapping accuracy."""
    return calculate_rate(matched, total)


def calculate_percentile(data: list[float], pct: float) -> float:
    """Calculate exact percentile value for a distribution."""
    if not data:
        return 0.0
    import math

    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(sorted_data[f], 2)
    d0 = sorted_data[f] * (c - k)
    d1 = sorted_data[c] * (k - f)
    return round(d0 + d1, 2)
