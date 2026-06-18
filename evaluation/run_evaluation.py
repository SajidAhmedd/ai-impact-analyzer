"""
Script to run evaluation and display results.

Usage:
    python evaluation/run_evaluation.py
    python evaluation/run_evaluation.py --case case_001
"""

import sys
import argparse
sys.path.insert(0, ".")

from app.evaluation.evaluator import Evaluator


def main():
    parser = argparse.ArgumentParser(description="Run evaluation tests")
    parser.add_argument("--case", type=str, help="Run specific case ID")
    parser.add_argument("--save", action="store_true", help="Save report to file")
    args = parser.parse_args()

    print("=" * 60)
    print("AI Change Impact Analyzer - Evaluation")
    print("=" * 60)

    evaluator = Evaluator()

    case_ids = [args.case] if args.case else None

    print(f"\nRunning {len(evaluator.test_cases) if not case_ids else len(case_ids)} test case(s)...")
    print("This may take several minutes.\n")

    report = evaluator.run_evaluation(case_ids=case_ids)

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        print(f"\n[{status}] {result.case_id}: {result.case_name}")
        print(f"  Overall Score: {result.score:.1%}")
        print(f"  Technical:     {result.technical_score:.1%}")
        print(f"  Operational:   {result.operational_score:.1%}")
        print(f"  Risk:          {result.risk_score:.1%}")
        print(f"  Synthesis:     {result.synthesis_score:.1%}")
        print(f"  Time:          {result.execution_time_ms:.0f}ms")

        if result.errors:
            print(f"  Errors: {result.errors}")

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total Cases:   {report.total_cases}")
    print(f"Passed:        {report.passed_cases}")
    print(f"Failed:        {report.failed_cases}")
    print(f"Average Score: {report.average_score:.1%}")

    if args.save:
        path = evaluator.save_report(report)
        print(f"\nReport saved to: {path}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()