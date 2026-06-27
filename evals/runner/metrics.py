"""Shared metrics for the eval tiers.

The Greybeard product promise is **precision over recall**, so the headline
number is the **false-alarm rate** — how often the skill fires (a candidate
``accept``, or a review ``VIOLATION``/``ADVISORY``) on an item that should have
stayed silent. We report it explicitly rather than hiding it inside accuracy.
"""

from __future__ import annotations


def compute_classification_metrics(pairs, positive_labels):
    """Compute precision/recall/false-alarm metrics for a set of predictions.

    ``pairs`` is an iterable of ``(expected, predicted)`` labels. A prediction of
    ``None`` (the model was not run / abstained) is counted as ``skipped`` and
    excluded from the rates.

    ``positive_labels`` is the set of labels that count as the skill *firing*
    (e.g. ``{"accept"}`` for Tier 1, ``{"VIOLATION", "ADVISORY"}`` for Tier 2).

    Returns a dict with counts plus precision, recall, false_alarm_rate and
    accuracy. Rates are ``None`` when their denominator is zero.
    """
    positive_labels = set(positive_labels)
    total = 0
    scored = 0
    skipped = 0
    correct = 0
    tp = fp = tn = fn = 0

    for expected, predicted in pairs:
        total += 1
        if predicted is None:
            skipped += 1
            continue
        scored += 1
        exp_pos = expected in positive_labels
        pred_pos = predicted in positive_labels
        if predicted == expected:
            correct += 1
        if exp_pos and pred_pos:
            tp += 1
        elif not exp_pos and pred_pos:
            fp += 1
        elif not exp_pos and not pred_pos:
            tn += 1
        else:  # exp_pos and not pred_pos
            fn += 1

    return {
        "total": total,
        "scored": scored,
        "skipped": skipped,
        "correct": correct,
        "truePositive": tp,
        "falsePositive": fp,
        "trueNegative": tn,
        "falseNegative": fn,
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "falseAlarmRate": _ratio(fp, fp + tn),
        "accuracy": _ratio(correct, scored),
    }


def _ratio(numerator, denominator):
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)
