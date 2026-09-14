data = {
    "messages": [
        HumanMessage(
            content="我最近在学习 Python3 基础教程，是入门级别的，大概要学 20 个小时，而且是完全免费的",
            additional_kwargs={},
            response_metadata={},
            id="de53ecf0-1c3d-4849-8b9c-11fa1f0b63ee",
        ),
        AIMessage(
            content="",
            additional_kwargs={"refusal": None},
            response_metadata={
                "token_usage": {
                    "completion_tokens": 92,
                    "prompt_tokens": 379,
                    "total_tokens": 471,
                    "completion_tokens_details": None,
                    "prompt_tokens_details": {
                        "audio_tokens": None,
                        "cache_write_tokens": None,
                        "cached_tokens": 128,
                        "image_tokens": None,
                        "text_tokens": None,
                    },
                    "prompt_cache_hit_tokens": 128,
                    "prompt_cache_miss_tokens": 251,
                },
                "model_provider": "deepseek",
                "model_name": "deepseek-flash",
                "system_fingerprint": "aeb56401ca74e127821c4f9126dcb669",
                "id": "039de8bf-a233-4297-89ef-28b8249c4742",
                "finish_reason": "tool_calls",
                "logprobs": None,
            },
            id="lc_run--01a09f72-607e-7701-b565-c1034342873e-0",
            tool_calls=[
                {
                    "name": "CourseInfo",
                    "args": {
                        "course_name": "Python3 基础教程",
                        "course_description": "入门级别",
                        "course_duration": "20 小时",
                        "is_free": "免费",
                    },
                    "id": "call_00_Hhf5IWvLs2CR66jbH3871085",
                    "type": "tool_call",
                }
            ],
            invalid_tool_calls=[],
            usage_metadata={
                "input_tokens": 379,
                "output_tokens": 92,
                "total_tokens": 471,
                "input_token_details": {"cache_read": 128},
                "output_token_details": {},
            },
        ),
        ToolMessage(
            content="Returning structured response: course_name='Python3 基础教程' course_description='入门级别' course_duration='20 小时' is_free='免费'",
            name="CourseInfo",
            id="4547ab2b-fcca-4a0d-9494-9fed2f3b712e",
            tool_call_id="call_00_Hhf5IWvLs2CR66jbH3871085",
        ),
    ],
    "structured_response": CourseInfo(
        course_name="Python3 基础教程",
        course_description="入门级别",
        course_duration="20 小时",
        is_free="免费",
    ),
}
