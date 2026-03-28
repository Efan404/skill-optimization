# tests/test_registry.py
import pytest
from scripts.skillsbench_registry import (
    CONDITIONS,
    PILOT_CONDITIONS,
    OPTIMIZED_CONDITION,
    TASKS,
    TASK_SHORT,
    AUTHOR_MODEL,
    IGNORED_JOB_NAMES,
    JOB_NAME_ALIASES,
    skill_yaml_path,
    parse_job_name,
    make_job_name,
)


class TestConditionConstants:
    def test_six_conditions(self):
        assert len(CONDITIONS) == 6

    def test_pilot_conditions_are_first_four(self):
        assert PILOT_CONDITIONS == CONDITIONS[:4]
        assert "self_generated_optimized" not in PILOT_CONDITIONS
        assert "curated_optimized" not in PILOT_CONDITIONS

    def test_optimized_mapping_not_string_concat(self):
        assert OPTIMIZED_CONDITION["self_generated_one_shot"] == "self_generated_optimized"
        assert OPTIMIZED_CONDITION["curated"] == "curated_optimized"
        assert len(OPTIMIZED_CONDITION) == 2

    def test_all_conditions_have_author_model(self):
        for c in CONDITIONS:
            assert c in AUTHOR_MODEL


class TestSkillYamlPath:
    def test_baseline_returns_none(self):
        assert skill_yaml_path("baseline", "overfull-hbox") is None

    def test_generic_scaffold_is_shared(self):
        path = skill_yaml_path("generic_scaffold", "overfull-hbox")
        assert path == "skills/skillsbench/generic_scaffold/generic_task_execution.yaml"
        assert skill_yaml_path("generic_scaffold", "db-wal-recovery") == path

    def test_curated_per_task(self):
        assert skill_yaml_path("curated", "overfull-hbox") == \
            "skills/skillsbench/curated/overfull_hbox.yaml"
        assert skill_yaml_path("curated", "db-wal-recovery") == \
            "skills/skillsbench/curated/db_wal_recovery.yaml"

    def test_optimized_uses_correct_dir(self):
        path = skill_yaml_path("self_generated_optimized", "overfull-hbox")
        assert path == "skills/skillsbench/self_generated_optimized/overfull_hbox.yaml"
        assert "one_shot" not in path

    def test_invalid_condition_raises(self):
        with pytest.raises(KeyError):
            skill_yaml_path("nonexistent", "overfull-hbox")


class TestParseJobName:
    def test_ignored_returns_none(self):
        assert parse_job_name("dev-00-overfull-baseline") is None
        assert parse_job_name("opencode-api-test") is None
        assert parse_job_name("overfull-baseline-gemini") is None

    def test_alias_smoke_baseline(self):
        result = parse_job_name("smoke-deepseek-baseline")
        assert result == ("overfull-hbox", "baseline", "deepseek/deepseek-chat", 1)

    def test_alias_feal_self_generated(self):
        result = parse_job_name("feal-self_generated-deepseek")
        assert result == (
            "feal-differential-cryptanalysis",
            "self_generated_one_shot",
            "deepseek/deepseek-chat",
            1,
        )

    def test_canonical_pilot_no_round(self):
        result = parse_job_name("dbwal-curated-deepseek")
        assert result == ("db-wal-recovery", "curated", "deepseek/deepseek-chat", 1)

    def test_canonical_with_round(self):
        result = parse_job_name("overfull-baseline-deepseek-r2")
        assert result == ("overfull-hbox", "baseline", "deepseek/deepseek-chat", 2)

    def test_canonical_long_condition_with_round(self):
        result = parse_job_name("feal-self_generated_one_shot-deepseek-r3")
        assert result == (
            "feal-differential-cryptanalysis",
            "self_generated_one_shot",
            "deepseek/deepseek-chat",
            3,
        )

    def test_unknown_returns_none(self):
        assert parse_job_name("totally-unknown-thing") is None


class TestMakeJobName:
    def test_basic(self):
        assert make_job_name("overfull-hbox", "baseline", 2) == \
            "overfull-baseline-deepseek-r2"

    def test_long_condition(self):
        assert make_job_name("db-wal-recovery", "self_generated_one_shot", 3) == \
            "dbwal-self_generated_one_shot-deepseek-r3"


from scripts.skillsbench_error_analysis import build_error_analysis


class TestBuildErrorAnalysis:
    def test_success_returns_none(self):
        result_json = {
            "verifier_result": {"rewards": {"reward": 1.0}},
            "exception_info": None,
        }
        ctrf = {
            "results": {
                "tests": [{"name": "test_a", "status": "passed"}],
                "summary": {"passed": 1, "failed": 0},
            }
        }
        assert build_error_analysis("overfull-hbox", result_json, ctrf, None, None) is None

    def test_timeout_classified_as_agent_system_failure(self):
        result_json = {
            "verifier_result": {"rewards": {"reward": 0.0}},
            "exception_info": {
                "exception_type": "AgentTimeoutError",
                "exception_message": "Agent execution timed out after 1800.0 seconds",
            },
        }
        ctrf = {
            "results": {
                "tests": [{"name": "test_a", "status": "failed"}],
                "summary": {"passed": 0, "failed": 1},
            }
        }
        ea = build_error_analysis("feal-differential-cryptanalysis", result_json, ctrf, None, None)
        assert ea["error_category"] == "agent_system_failure"
        assert ea["task_id"] == "feal-differential-cryptanalysis"
        assert "test_a" in ea["failed_tests"]

    def test_test_failure_classified_as_skill_failure(self):
        result_json = {
            "verifier_result": {"rewards": {"reward": 0.0}},
            "exception_info": None,
        }
        ctrf = {
            "results": {
                "tests": [
                    {"name": "test_pass", "status": "passed"},
                    {"name": "test_fail", "status": "failed"},
                ],
                "summary": {"passed": 1, "failed": 1},
            }
        }
        ea = build_error_analysis("db-wal-recovery", result_json, ctrf, None, None)
        assert ea["error_category"] == "skill_failure"
        assert ea["failed_tests"] == ["test_fail"]

    def test_all_canonical_fields_present(self):
        result_json = {
            "verifier_result": {"rewards": {"reward": 0.0}},
            "exception_info": None,
        }
        ctrf = {
            "results": {
                "tests": [{"name": "test_x", "status": "failed"}],
                "summary": {"passed": 0, "failed": 1},
            }
        }
        ea = build_error_analysis("overfull-hbox", result_json, ctrf, None, None)
        required_fields = {
            "task_id", "error_category", "failure_mode", "description",
            "failed_tests", "trajectory_summary", "optimization_hint",
        }
        assert set(ea.keys()) == required_fields
