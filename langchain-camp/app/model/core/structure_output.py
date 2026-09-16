"""
结构化输出
"""

from langchain.messages import HumanMessage
from pydantic import BaseModel, Field

from app.log import log_info


# 定义期望的输出结构
class CourseInfo(BaseModel):
    course_name: str = Field(..., description="课程名称")
    course_description: str = Field(..., description="课程描述")
    course_duration: str = Field(..., description="课程时长")
    is_free: str = Field(..., description="是否免费")


def structure_output(agent):

    user_input = (
        "我最近在学习 Python3 基础教程，是入门级别的，"
        "大概要学 20 个小时，而且是完全免费的"
    )

    response = agent.invoke({"messages": [HumanMessage(content=user_input)]})

    log_info(response)

    if "structured_response" in response:
        course_info = response["structured_response"]
        return course_info.model_dump()
