from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from app.schemas import CandidateProfile, InterviewPlan, ModelConfig
from app.services.pdf import extract_pdf_text
from app.services.providers import generate_plan


class InterviewState(TypedDict, total=False):
    resume_bytes: bytes
    job_description: str
    model_config: ModelConfig
    profile: CandidateProfile
    resume_text: str
    plan: InterviewPlan


def extract_resume(state: InterviewState) -> InterviewState:
    return {"resume_text": extract_pdf_text(state["resume_bytes"])}


def generate_interview_plan(state: InterviewState) -> InterviewState:
    plan = generate_plan(
        state["job_description"],
        state["resume_text"],
        state["model_config"],
        state.get("profile"),
    )
    return {"plan": plan}


def build_interview_graph():
    graph = StateGraph(InterviewState)
    graph.add_node("extract_resume", extract_resume)
    graph.add_node("generate_plan", generate_interview_plan)
    graph.add_edge(START, "extract_resume")
    graph.add_edge("extract_resume", "generate_plan")
    graph.add_edge("generate_plan", END)
    return graph.compile()
