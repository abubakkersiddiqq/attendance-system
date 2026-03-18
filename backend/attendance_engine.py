"""
attendance_engine.py — Core Business Logic
============================================
This module contains the pure math for:
  1. Calculating current attendance percentage
  2. Calculating how many classes a student can safely skip
  3. Calculating classes needed to reach a target percentage
"""

import math


def calculate_attendance_percentage(classes_attended: int, total_classes: int) -> float:
    """
    Calculate attendance percentage.

    Formula: attendance_percentage = (classes_attended / total_classes) * 100

    Example:
        >>> calculate_attendance_percentage(30, 40)
        75.0
    """
    if total_classes <= 0:
        return 0.0
    return round((classes_attended / total_classes) * 100, 2)


def calculate_safe_bunks(present: int, total: int, required: float = 0.75) -> int:
    """
    Calculate how many future classes a student can skip
    while still maintaining the required attendance threshold.

    Mathematical derivation:
    ──────────────────────────────────────────────────────
    We need:
        P / (T + x) ≥ R

    Where:
        P = classes attended (present)
        T = total classes conducted so far
        x = number of future classes to skip
        R = required attendance (e.g., 0.75 for 75%)

    Solving for x:
        P ≥ R × (T + x)
        P ≥ R×T + R×x
        P - R×T ≥ R×x
        x ≤ (P - R×T) / R

    So: safe_bunks = floor((P - R×T) / R)
    ──────────────────────────────────────────────────────

    Example:
        P=30, T=36, R=0.75
        safe_bunks = floor((30 - 0.75×36) / 0.75)
                   = floor((30 - 27) / 0.75)
                   = floor(3 / 0.75)
                   = floor(4.0)
                   = 4

    Args:
        present  : classes attended so far
        total    : total classes conducted so far
        required : minimum attendance fraction (default 0.75 = 75%)

    Returns:
        Number of classes the student can safely skip (min 0)
    """
    value = (present - required * total) / required
    return max(0, math.floor(value))


def calculate_classes_needed(present: int, total: int, required: float = 0.75) -> int:
    """
    Calculate how many CONSECUTIVE classes a student must attend
    to reach the required attendance percentage.

    Formula:
        (P + n) / (T + n) ≥ R
        P + n ≥ R×T + R×n
        n - R×n ≥ R×T - P
        n(1 - R) ≥ R×T - P
        n ≥ (R×T - P) / (1 - R)

    Returns 0 if already at or above the required threshold.

    Example:
        P=20, T=40, R=0.75
        n = ceil((0.75×40 - 20) / (1 - 0.75))
          = ceil((30 - 20) / 0.25)
          = ceil(40)
          = 40
    """
    current_pct = calculate_attendance_percentage(present, total)
    if current_pct >= required * 100:
        return 0
    numerator = required * total - present
    denominator = 1 - required
    if denominator <= 0:
        return 0
    return math.ceil(numerator / denominator)


def get_full_attendance_report(
    present: int,
    total: int,
    required_pct: float = 75.0,
) -> dict:
    """
    Build a complete attendance report combining all calculations.

    Args:
        present      : classes attended
        total        : total classes conducted
        required_pct : minimum attendance required (e.g., 75.0)

    Returns:
        A dict with all calculated metrics.
    """
    required_fraction = required_pct / 100
    percentage = calculate_attendance_percentage(present, total)
    safe_bunks = calculate_safe_bunks(present, total, required_fraction)
    classes_needed = calculate_classes_needed(present, total, required_fraction)
    is_below = percentage < required_pct

    # Status label
    if percentage >= 90:
        status = "EXCELLENT"
    elif percentage >= required_pct:
        status = "SAFE"
    elif percentage >= required_pct - 10:
        status = "WARNING"
    else:
        status = "CRITICAL"

    return {
        "classes_attended": present,
        "total_classes": total,
        "attendance_percentage": percentage,
        "required_percentage": required_pct,
        "safe_bunks": safe_bunks,
        "classes_needed_to_recover": classes_needed,
        "is_below_required": is_below,
        "status": status,
    }
