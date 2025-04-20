from radiko_timeshift_recorder.programs import Program


def test_program_serialization_deserialization(sample_program: Program):
    json_string = sample_program.model_dump_json()

    deserialized_program = Program.model_validate_json(json_string)

    assert deserialized_program == sample_program
