from datetime import date, timedelta


def calculate_new_interval(success_streak: int, ease_factor: float, previous_interval: int) -> int:
    """Simple SRS interval calculator.

    - first successful repetition -> interval = 1 day
    - second -> 6 days
    - afterwards interval = round(previous_interval * ease_factor)
    """
    if success_streak <= 1:
        return 1
    if success_streak == 2:
        return 6
    return max(1, int(round(previous_interval * ease_factor)))


def update_user_item_on_result(item, was_correct: bool):
    today = date.today()
    if was_correct:
        item.success_streak = item.success_streak + 1
        item.interval_days = calculate_new_interval(item.success_streak, item.ease_factor, item.interval_days or 1)
        item.next_review_date = today + timedelta(days=item.interval_days)
    else:
        # failure — reset streak, set short interval and reduce ease factor slightly
        item.success_streak = 0
        item.interval_days = 1
        item.next_review_date = today + timedelta(days=1)
        item.ease_factor = max(1.3, item.ease_factor - 0.1)
    return item
