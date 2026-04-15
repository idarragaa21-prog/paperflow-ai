from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services.meta_runs_service import _preset_to_analysis_type, run_meta_analysis


def test_preset_to_analysis_type_rejects_unknown_preset():
    with pytest.raises(ValueError, match="Unsupported preset"):
        _preset_to_analysis_type("meta_unknown_future")


@pytest.mark.asyncio
async def test_run_meta_analysis_rejects_dataset_preset_mismatch():
    dataset = SimpleNamespace(
        id=uuid4(),
        matrix_version_id=uuid4(),
        preset="meta_binary_random",
        file_path="datasets/fake.csv",
    )
    with pytest.raises(ValueError, match="Preset mismatch"):
        await run_meta_analysis(  # type: ignore[arg-type]
            db=None,
            project_id=uuid4(),
            dataset=dataset,
            preset="meta_continuous_md",
            title="mismatch",
            input_params={},
            user_id=uuid4(),
        )
