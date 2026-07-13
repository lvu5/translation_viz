import collections
import json
import os
import utils_fig
import matplotlib.pyplot as plt
from datetime import datetime
import numpy as np
os.chdir(os.path.dirname(os.path.abspath(__file__))+ "/../")

os.makedirs("computed/", exist_ok=True)

with open("data/users.json", "r") as f:
    data_users = json.load(f)

with open("data/submissions.json", "r") as f:
    data_submissions = json.load(f)

data_out = {}

user_counts = collections.defaultdict(set)
user_counts["registered"] = set(x["username"] for x in data_users)
user_counts["submitted"] = set(x["username"] for x in data_submissions)
user_counts["accepted"] = set(x["username"] for x in data_submissions if x["status"] == "accept")
user_counts["reviewers"] = set(x["reviewed_by"] for x in data_submissions if x["reviewed_by"] is not None)
user_counts["admins"] = set(x["username"] for x in data_users if "admin" in x["roles"])

data_out["user_counts"] = {k: len(v) for k, v in user_counts.items()}

# language distribution
language_counts = collections.Counter()
for submission in data_submissions:
    language_counts[submission["source_lang"].strip()] += 1
    language_counts[submission["target_lang"].strip()] += 1


data_out["language_counts"] = dict(language_counts.most_common())

def date_to_delta(date_str):
    # subtract fom 2026-05-01
    # 2026-05-26 23:23
    # remove micros?
    if date_str.count(":") == 2:
        date_str = date_str.rsplit(":", 1)[0]
    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    delta = date_obj - datetime(2026, 5, 1)
    return delta.days

# number of accepted, rejected, pending submissions
status_counts = collections.Counter()
delta_today = date_to_delta(datetime.now().strftime("%Y-%m-%d %H:%M"))
dates_pending = [0]*(delta_today+1)
dates_accepted = [0]*(delta_today+1)
dates_returned = [0]*(delta_today+1)
for submission in data_submissions:
    status_counts[submission["status"]] += 1
    dates = [submission["created_at"]] + [x["created_at"] for x in submission["comments"]]
    delta_first = date_to_delta(min(dates))
    delta_last = date_to_delta(max(dates))

    if submission["status"] == "accept":
        for i in range(delta_last+1, delta_today+1): 
            dates_accepted[i] += 1
        for i in range(delta_first, delta_last+1):
            dates_pending[i] += 1
    elif submission["status"] == "return":
        for i in range(delta_first, delta_last+1):
            dates_pending[i] += 1
        for i in range(delta_last, delta_today+1):
            dates_returned[i] += 1
    elif submission["status"] == "pending":
        for i in range(delta_first, delta_today+1):
            dates_pending[i] += 1

dates_accepted = np.array(dates_accepted)
dates_pending = np.array(dates_pending)
dates_returned = np.array(dates_returned)

# # derivative
# plt.plot(range(delta_today+1), [x2-x1 for x1, x2 in zip([0]+list(dates_accepted[:-1]), dates_accepted)], color="green", linewidth=2)
# plt.plot(range(delta_today+1), [x2-x1 for x1, x2 in zip([0]+list(dates_pending[:-1]), dates_pending)], color="orange", linewidth=2)
# plt.plot(range(delta_today+1), [x2-x1 for x1, x2 in zip([0]+list(dates_returned[:-1]), dates_returned)], color="red", linewidth=2)

plt.plot(range(delta_today+1), dates_accepted, color="green", linewidth=2, marker=".")
plt.plot(range(delta_today+1), dates_pending, color="orange", linewidth=2, marker=".")
plt.plot(range(delta_today+1), dates_returned, color="red", linewidth=2, marker=".")
plt.ylabel("Number of submissions")
plt.xlabel("Days since 2026-05-01")
plt.text(
    x=delta_today,
    y=dates_accepted[-1],
    s=f"Accepted: {status_counts['accept']}   ",
    ha="left", va="center"
)
plt.text(
    x=delta_today,
    y=dates_pending[-1],
    s=f"Pending: {status_counts['pending']}   ",
    ha="left", va="center",
)
plt.text(
    x=delta_today,
    y=dates_returned[-1],
    s=f"Returned: {status_counts['return']}   ",
    ha="left", va="center",
)

plt.gca().spines[["top", "right"]].set_visible(False)
plt.tight_layout(pad=1)

plt.show()

data_out["status_counts"] = dict(status_counts.most_common())

# number of quota_used per all submissions
data_out["quota_per_submission"] = f"{sum(x["quota_used"] for x in data_users if x["quota_used"]) / len(data_submissions):.1f}"

counter_passing = collections.Counter()
for submission in data_submissions:
    # how many systems pass
    if submission["translations"] is None:
        continue
    passing = sum(all(entry["verified"]) for entry in submission["translations"] if entry["verified"] is not None)
    counter_passing[passing-1] += 1

data_out["passing_counts"] = dict(counter_passing.most_common())
with open("computed/bake_results.json", "w") as f:
    json.dump(data_out, f, indent=2)