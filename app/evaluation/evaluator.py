"""
Evaluation system for testing analysis quality.

Compares actual outputs against expected results
and calculates quality metrics.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
import structlog

from app.workflow.graph import run_analysis

logger = structlog.get_logger()


@dataclass
class EvaluationResult:
    """Result of evaluating a single test case."""
    case_id: str
    case_name: str
    passed: bool
    score: float  # 0-1
    technical_score: float
    operational_score: float
    risk_score: float
    synthesis_score: float
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    execution_time_ms: float = 0


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    timestamp: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    average_score: float
    results: List[EvaluationResult] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class Evaluator:
    """
    Evaluates analysis quality against expected results.

    Usage:
        evaluator = Evaluator()
        report = evaluator.run_evaluation()
        print(f"Score: {report.average_score:.1%}")
    """

    def __init__(self, test_cases_path: str = "evaluation/test_cases/sample_cases.json"):
        self.test_cases_path = Path(test_cases_path)
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> List[Dict]:
        """Load test cases from JSON file."""
        if not self.test_cases_path.exists():
            logger.warning("Test cases file not found", path=str(self.test_cases_path))
            return []

        with open(self.test_cases_path) as f:
            return json.load(f)

    def _check_mentions(self, text: str, keywords: List[str]) -> Tuple[int, int]:
        """Check how many keywords are mentioned in text."""
        text_lower = text.lower()
        found = sum(1 for kw in keywords if kw.lower() in text_lower)
        return found, len(keywords)

    def _evaluate_technical(self, analysis: Dict, expected: Dict) -> Tuple[float, Dict]:
        """Evaluate technical analysis."""
        if not analysis or analysis.get("error"):
            return 0.0, {"error": "No technical analysis"}

        details = {}
        scores = []

        # Check mentioned keywords
        summary = analysis.get("summary", "")
        systems = " ".join(analysis.get("affected_systems", []))
        full_text = f"{summary} {systems}"

        should_mention = expected.get("should_mention", [])
        found, total = self._check_mentions(full_text, should_mention)
        mention_score = found / total if total > 0 else 1.0
        scores.append(mention_score)
        details["keywords_found"] = f"{found}/{total}"

        # Check affected systems count
        min_systems = expected.get("affected_systems_min", 0)
        actual_systems = len(analysis.get("affected_systems", []))
        systems_score = 1.0 if actual_systems >= min_systems else actual_systems / max(min_systems, 1)
        scores.append(systems_score)
        details["affected_systems"] = f"{actual_systems} (min: {min_systems})"

        # Check migration required
        expected_migration = expected.get("migration_required")
        if expected_migration is not None:
            actual_migration = analysis.get("migration_required", False)
            migration_score = 1.0 if actual_migration == expected_migration else 0.0
            scores.append(migration_score)
            details["migration_match"] = actual_migration == expected_migration

        return sum(scores) / len(scores), details

    def _evaluate_operational(self, analysis: Dict, expected: Dict) -> Tuple[float, Dict]:
        """Evaluate operational analysis."""
        if not analysis or analysis.get("error"):
            return 0.0, {"error": "No operational analysis"}

        details = {}
        scores = []

        # Check mentioned keywords
        summary = analysis.get("summary", "")
        teams = " ".join(analysis.get("teams_impacted", []))
        workflows = " ".join(analysis.get("affected_workflows", []))
        full_text = f"{summary} {teams} {workflows}"

        should_mention = expected.get("should_mention", [])
        found, total = self._check_mentions(full_text, should_mention)
        mention_score = found / total if total > 0 else 1.0
        scores.append(mention_score)
        details["keywords_found"] = f"{found}/{total}"

        # Check teams impacted
        min_teams = expected.get("teams_impacted_min", 0)
        actual_teams = len(analysis.get("teams_impacted", []))
        teams_score = 1.0 if actual_teams >= min_teams else actual_teams / max(min_teams, 1)
        scores.append(teams_score)
        details["teams_impacted"] = f"{actual_teams} (min: {min_teams})"

        # Check training required
        expected_training = expected.get("training_required")
        if expected_training is not None:
            actual_training = analysis.get("training_required", False)
            training_score = 1.0 if actual_training == expected_training else 0.5
            scores.append(training_score)
            details["training_match"] = actual_training == expected_training

        return sum(scores) / len(scores), details

    def _evaluate_risk(self, analysis: Dict, expected: Dict) -> Tuple[float, Dict]:
        """Evaluate risk analysis."""
        if not analysis or analysis.get("error"):
            return 0.0, {"error": "No risk analysis"}

        details = {}
        scores = []

        # Check mentioned keywords
        summary = analysis.get("summary", "")
        risks_text = " ".join([r.get("risk", "") for r in analysis.get("risks", [])])
        full_text = f"{summary} {risks_text}"

        should_mention = expected.get("should_mention", [])
        found, total = self._check_mentions(full_text, should_mention)
        mention_score = found / total if total > 0 else 1.0
        scores.append(mention_score)
        details["keywords_found"] = f"{found}/{total}"

        # Check minimum risks
        min_risks = expected.get("min_risks", 0)
        actual_risks = len(analysis.get("risks", []))
        risks_score = 1.0 if actual_risks >= min_risks else actual_risks / max(min_risks, 1)
        scores.append(risks_score)
        details["risks_identified"] = f"{actual_risks} (min: {min_risks})"

        # Check risk level
        expected_levels = expected.get("expected_risk_level", [])
        if expected_levels:
            actual_level = analysis.get("overall_risk_level", "").lower()
            level_match = actual_level in [l.lower() for l in expected_levels]
            level_score = 1.0 if level_match else 0.5
            scores.append(level_score)
            details["risk_level"] = f"{actual_level} (expected: {expected_levels})"

        return sum(scores) / len(scores), details

    def _evaluate_synthesis(self, synthesis: Dict, expected: Dict) -> Tuple[float, Dict]:
        """Evaluate synthesis/final assessment."""
        if not synthesis or synthesis.get("error"):
            return 0.0, {"error": "No synthesis"}

        details = {}
        scores = []

        # Check recommendation
        expected_recs = expected.get("expected_recommendations", [])
        if expected_recs:
            actual_rec = synthesis.get("recommendation", "").lower()
            rec_match = actual_rec in [r.lower() for r in expected_recs]
            rec_score = 1.0 if rec_match else 0.3
            scores.append(rec_score)
            details["recommendation"] = f"{actual_rec} (expected: {expected_recs})"

        # Check if actions exist
        if expected.get("should_have_actions"):
            actions = synthesis.get("prioritized_actions", [])
            actions_score = 1.0 if len(actions) > 0 else 0.0
            scores.append(actions_score)
            details["has_actions"] = len(actions) > 0

        return sum(scores) / len(scores) if scores else 1.0, details

    def evaluate_case(self, case: Dict) -> EvaluationResult:
        """Evaluate a single test case."""
        case_id = case.get("id", "unknown")
        case_name = case.get("name", "Unknown")
        change_request = case.get("change_request", "")
        expected = case.get("expected", {})

        logger.info("Evaluating case", case_id=case_id, name=case_name)

        start_time = datetime.utcnow()
        errors = []

        try:
            # Run analysis
            result = run_analysis(change_request)

            # Evaluate each component
            tech_score, tech_details = self._evaluate_technical(
                result.get("technical_analysis", {}),
                expected.get("technical", {})
            )

            ops_score, ops_details = self._evaluate_operational(
                result.get("operational_analysis", {}),
                expected.get("operational", {})
            )

            risk_score, risk_details = self._evaluate_risk(
                result.get("risk_analysis", {}),
                expected.get("risk", {})
            )

            synth_score, synth_details = self._evaluate_synthesis(
                result.get("final_assessment", {}),
                expected.get("synthesis", {})
            )

            # Calculate overall score
            overall_score = (tech_score + ops_score + risk_score + synth_score) / 4

            execution_time = (datetime.utcnow() - start_time).total_seconds() * 1000

            return EvaluationResult(
                case_id=case_id,
                case_name=case_name,
                passed=overall_score >= 0.6,
                score=overall_score,
                technical_score=tech_score,
                operational_score=ops_score,
                risk_score=risk_score,
                synthesis_score=synth_score,
                details={
                    "technical": tech_details,
                    "operational": ops_details,
                    "risk": risk_details,
                    "synthesis": synth_details,
                },
                errors=errors,
                execution_time_ms=execution_time,
            )

        except Exception as e:
            logger.error("Evaluation failed", case_id=case_id, error=str(e))
            return EvaluationResult(
                case_id=case_id,
                case_name=case_name,
                passed=False,
                score=0.0,
                technical_score=0.0,
                operational_score=0.0,
                risk_score=0.0,
                synthesis_score=0.0,
                errors=[str(e)],
            )

    def run_evaluation(self, case_ids: List[str] = None) -> EvaluationReport:
        """
        Run evaluation on test cases.

        Args:
            case_ids: Optional list of case IDs to run. If None, runs all.
        """
        cases_to_run = self.test_cases
        if case_ids:
            cases_to_run = [c for c in self.test_cases if c.get("id") in case_ids]

        logger.info("Starting evaluation", total_cases=len(cases_to_run))

        results = []
        for case in cases_to_run:
            result = self.evaluate_case(case)
            results.append(result)

        passed = sum(1 for r in results if r.passed)
        avg_score = sum(r.score for r in results) / len(results) if results else 0

        report = EvaluationReport(
            timestamp=datetime.utcnow().isoformat(),
            total_cases=len(results),
            passed_cases=passed,
            failed_cases=len(results) - passed,
            average_score=avg_score,
            results=results,
        )

        logger.info(
            "Evaluation complete",
            passed=passed,
            failed=len(results) - passed,
            average_score=f"{avg_score:.1%}"
        )

        return report

    def save_report(self, report: EvaluationReport, path: str = None) -> Path:
        """Save evaluation report to file."""
        if path is None:
            path = f"evaluation/reports/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(report.to_json())

        return file_path
