from radiko_timeshift_recorder.job import Job


def test_job_serialization_deserialization(sample_job: Job):
    json_string = sample_job.model_dump_json()

    deserialized_program = Job.model_validate_json(json_string)

    assert deserialized_program == sample_job
