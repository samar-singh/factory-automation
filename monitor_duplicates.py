"""Monitor for duplicate review creation"""

import re
import time
from collections import defaultdict


def monitor_logs(log_file="factory_monitor.log", duration=120):
    """Monitor logs for duplicate reviews"""

    print(f"Monitoring {log_file} for {duration} seconds...")
    print("Looking for duplicate review patterns...\n")

    reviews_created = defaultdict(list)
    process_calls = []
    start_time = time.time()

    while time.time() - start_time < duration:
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()

            for line in lines:
                # Track review creation
                if "Created review request" in line and "REV-" in line:
                    match = re.search(r"REV-\d{8}-\d{6}-\d{4}", line)
                    if match:
                        review_id = match.group()
                        timestamp = line.split(" ")[0] if " " in line else "unknown"

                        # Extract email info if available
                        email_info = "unknown"
                        if "with" in line:
                            email_info = (
                                line.split("with")[0].split("request")[-1].strip()
                            )

                        reviews_created[review_id].append(
                            {
                                "time": timestamp,
                                "line": line.strip(),
                                "email": email_info,
                            }
                        )

                # Track process_complete_order calls
                if "process_complete_order" in line:
                    process_calls.append(line.strip())

            # Check for issues
            issues = []

            # Multiple reviews in short time
            review_times = sorted(reviews_created.keys())
            if len(review_times) > 1:
                for i in range(1, len(review_times)):
                    # If two reviews created within 30 seconds
                    prev_id = review_times[i - 1]
                    curr_id = review_times[i]

                    # Extract timestamps and compare
                    prev_time = prev_id.split("-")[1] + prev_id.split("-")[2]
                    curr_time = curr_id.split("-")[1] + curr_id.split("-")[2]

                    if prev_time[:8] == curr_time[:8]:  # Same date
                        issues.append(
                            f"Multiple reviews created close together: {prev_id} and {curr_id}"
                        )

            # Display current status
            print(
                f"\r[{int(time.time() - start_time)}s] Reviews: {len(reviews_created)}, Process calls: {len(process_calls)}",
                end="",
            )

            time.sleep(1)

        except Exception as e:
            print(f"\nError reading log: {e}")
            time.sleep(1)

    # Final report
    print("\n\n=== MONITORING COMPLETE ===")
    print(f"Total reviews created: {len(reviews_created)}")
    print(f"Total process_complete_order calls: {len(process_calls)}")

    if len(reviews_created) > 0:
        print("\nReviews created:")
        for review_id, entries in reviews_created.items():
            print(f"\n- {review_id}:")
            for entry in entries:
                print(f"  Time: {entry['time']}")
                print(f"  Email: {entry['email']}")

    if issues:
        print("\n⚠️  ISSUES DETECTED:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ No duplicate issues detected")


if __name__ == "__main__":
    print("=== DUPLICATE REVIEW MONITOR ===")
    print("Please process an email in the UI while this runs...\n")
    monitor_logs()
