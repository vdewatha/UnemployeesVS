from utils import *
from prompts import *
from schema import *
from tools import *
import configuration


from trustcall import create_extractor
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, END, START
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs, HumanMessage, SystemMessage

from datetime import datetime
import uuid
import operator
from typing import Annotated, List

# Model initialization
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)


class ParentState(MessagesState):
  """ Parent state for the system """
  final_report: Optional[str] = None
  active_application: Optional[Application] = None
  annotated_resume: Optional[AnnotatedResume] = None
  applications: Optional[JobApplications] = None
  documents: Optional[DocumentCollection] = None
  max_interviews: int = 3
  human_analyst_feedback: Optional[str] = None
  analysts: Optional[list[Analyst]] = None
  sections: Annotated[List, operator.add] = None

# Agent


def hunter(state: ParentState, config: RunnableConfig, store: BaseStore):

    """Load memories from the store and use them to personalize the chatbot's response."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    # hunter_role = configurable.hunter_role
    
    namespace = ("active_application", user_id)
    memories = store.search(namespace)
    if memories:
        active_application = memories[0].value
    else:
        active_application = None

    # Retrieve profile memory from the store
    namespace = ("annotated_resume", user_id)
    memories = store.search(namespace)
    if memories:
        resume = memories[0].value
    else:
        resume = None

    # Retrieve custom instructions
    namespace = ("instructions", user_id)
    memories = store.search(namespace)
    if memories:
        instructions = memories[0].value
    else:
        instructions = None

    # Retrieve job applications
    namespace = ("applications", user_id)
    memories = store.search(namespace)
    if memories:
        job_applications = memories[0].value
    else:
        job_applications = None

    # Retrieve documents
    namespace = ("documents", user_id)
    memories = store.search(namespace)
    if memories:
        documents = memories[0].value
    else:
        documents = None
    
    system_msg = MODEL_SYSTEM_MESSAGE.format(
        # hunter_role=hunter_role,
        annotated_resume=resume, job_applications=job_applications, 
        documents=documents,  instructions=instructions
    )

    # Respond using memory as well as the chat history
    # TODO: Add more tools and allow parallel tool calls
    response = model.bind_tools(
        [UpdateMemory], parallel_tool_calls=False
    ).invoke([SystemMessage(content=system_msg)]+state["messages"])

    return {"messages": [response]}

# Update resume
def update_resume(state: ParentState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Define the namespace for the memories
    namespace = ("annotated_resume", user_id)

    # Retrieve the most recent memories for context
    existing_items = store.search(namespace)

    # Format the existing memories for the Trustcall extractor
    tool_name = "AnnotatedResume"
    existing_memories = (
        [(existing_item.key, tool_name, existing_item.value)
          for existing_item in existing_items] if existing_items else None
    )

    # Merge the chat history and the instruction
    TRUSTCALL_INSTRUCTION_FORMATTED=TRUSTCALL_INSTRUCTION.format(time=datetime.now().isoformat())
    updated_messages=list(merge_message_runs(messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]))

    profile_extractor = create_extractor(
      model,
      tools=[AnnotatedResume],
      tool_choice="AnnotatedResume",
  )
    # Invoke the extractor
    result = profile_extractor.invoke({"messages": updated_messages, 
                                         "existing": existing_memories})

    # Save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
    tool_calls = state['messages'][-1].tool_calls
    return {"messages": [{"role": "tool", "content": "updated resume", "tool_call_id":tool_calls[0]['id']}]}

# Update job applications
def update_job_applications(state: MessagesState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Define the namespace for the memories
    namespace = ("applications", user_id)

    # Retrieve the most recent memories for context
    existing_items = store.search(namespace)

    # Format the existing memories for the Trustcall extractor
    tool_name = "JobApplications"
    existing_memories = ([(existing_item.key, tool_name, existing_item.value)
                          for existing_item in existing_items]
                          if existing_items
                          else None
                        )

    # Merge the chat history and the instruction
    TRUSTCALL_INSTRUCTION_FORMATTED=TRUSTCALL_INSTRUCTION.format(time=datetime.now().isoformat())
    updated_messages=list(merge_message_runs(messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]))

    # Initialize the spy for visibility into the tool calls made by Trustcall
    spy = Spy()
    
    # Create the Trustcall extractor for updating the JobApplications list 
    todo_extractor = create_extractor(
    model,
    tools=[JobApplications],
    tool_choice=tool_name,
    enable_inserts=True
    ).with_listeners(on_end=spy)

    # Invoke the extractor
    result = todo_extractor.invoke({"messages": updated_messages, 
                                    "existing": existing_memories})

    # Save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
        
    # Respond to the tool call made in agent, confirming the update
    tool_calls = state['messages'][-1].tool_calls

    # Extract the changes made by Trustcall and add the the ToolMessage returned to agent
    application_update_msg = extract_tool_info(spy.called_tools, tool_name)
    return {"messages": [{"role": "tool", "content": application_update_msg, "tool_call_id":tool_calls[0]['id']}]}

# Update instructions
def update_instructions(state: ParentState, config: RunnableConfig, store: BaseStore):

    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id
    
    namespace = ("instructions", user_id)

    existing_memory = store.get(namespace, "user_instructions")
        
    # Format the memory in the system prompt
    system_msg = CREATE_INSTRUCTIONS.format(current_instructions=existing_memory.value if existing_memory else None)
    new_memory = model.invoke([SystemMessage(content=system_msg)]+state['messages'][:-1] + [HumanMessage(content="Please update the instructions based on the conversation")])

    # Overwrite the existing memory in the store 
    key = "user_instructions"
    store.put(namespace, key, {"memory": new_memory.content})
    tool_calls = state['messages'][-1].tool_calls
    return {"messages": [{"role": "tool", "content": "updated instructions", "tool_call_id":tool_calls[0]['id']}]}

# Update documents
def update_documents(state: ParentState, config: RunnableConfig, store: BaseStore):
    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Define the namespace for the memories
    namespace = ("documents", user_id)

    # Retrieve the most recent memories for context
    existing_items = store.search(namespace)

    # Format the existing memories for the Trustcall extractor
    tool_name = "DocumentCollection"
    existing_memories = ([(existing_item.key, tool_name, existing_item.value)
                          for existing_item in existing_items]
                          if existing_items
                          else None
                        )

    # Merge the chat history and the instruction
    TRUSTCALL_INSTRUCTION_FORMATTED=TRUSTCALL_INSTRUCTION.format(time=datetime.now().isoformat())
    updated_messages=list(merge_message_runs(messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]))

    # Initialize the spy for visibility into the tool calls made by Trustcall
    spy = Spy()
    
    # Create the Trustcall extractor for updating the DocumentCollection
    todo_extractor = create_extractor(
    model,
    tools=[DocumentCollection],
    tool_choice=tool_name,
    enable_inserts=True
    ).with_listeners(on_end=spy)

    # Invoke the extractor
    result = todo_extractor.invoke({"messages": updated_messages, 
                                    "existing": existing_memories})

    # Save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
        
    # Respond to the tool call made in agent, confirming the update
    tool_calls = state['messages'][-1].tool_calls

    # Extract the changes made by Trustcall and add the the ToolMessage returned to agent
    document_update_msg = extract_tool_info(spy.called_tools, tool_name)
    return {"messages": [{"role": "tool", "content": document_update_msg, "tool_call_id":tool_calls[0]['id']}]}

# begin_interview
def begin_interview(state: ParentState, config: RunnableConfig, store: BaseStore):
    """Reflect on the chat history and update the memory collection."""
    
    # Get the user ID from the config
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    # Define the namespace for the memories
    namespace = ("active_application", user_id)

    # Retrieve the most recent memories for context
    existing_items = store.search(namespace)

    # Format the existing memories for the Trustcall extractor
    tool_name = "Application"
    existing_memories = ([(existing_item.key, tool_name, existing_item.value)
                          for existing_item in existing_items]
                          if existing_items
                          else None
                        )

    # Merge the chat history and the instruction
    TRUSTCALL_INSTRUCTION_FORMATTED=TRUSTCALL_INSTRUCTION.format(time=datetime.now().isoformat())
    updated_messages=list(merge_message_runs(messages=[SystemMessage(content=TRUSTCALL_INSTRUCTION_FORMATTED)] + state["messages"][:-1]))

    # Invoke the extractor
    active_app_extractor= create_extractor(
      model,
      tools=[Application],
      tool_choice="Application",
  )
    result = active_app_extractor.invoke({"messages": updated_messages, 
                                         "existing": existing_memories})

    # Save the memories from Trustcall to the store
    for r, rmeta in zip(result["responses"], result["response_metadata"]):
        store.put(namespace,
                  rmeta.get("json_doc_id", str(uuid.uuid4())),
                  r.model_dump(mode="json"),
            )
    tool_calls = state['messages'][-1].tool_calls
    return {"messages": [{"role": "tool", "content": "updated active application", "tool_call_id":tool_calls[0]['id']}]}

# route messages
def route_message(
        state: ParentState, config: RunnableConfig, store: BaseStore
    ) -> Literal[
        END, 
        "update_instructions", 
        "update_job_applications", 
        "update_resume", 
        "update_documents",
        "begin_interview"
    ]:

    """Reflect on the memories and chat history to decide whether to update the memory collection or begin an interview."""
    message = state['messages'][-1]
    if len(message.tool_calls) ==0:
        return END
    else:
        tool_call = message.tool_calls[0]
        if tool_call['name'] == 'UpdateMemory':
            if tool_call['args']['update_type'] == "annotated_resume":
                return "update_resume"
            elif tool_call['args']['update_type'] == "application":
                return "update_job_applications"
            elif tool_call['args']['update_type'] == "document":
                return "update_documents"
            elif tool_call['args']['update_type'] == "instructions":
                return "update_instructions"
            elif tool_call['args']['update_type'] == "active_application":
                return "begin_interview"
            else:
                print(f"error: {tool_call['args']['update_type']}")
                raise ValueError
        else:
            raise ValueError(f"error: {tool_call['args']}")

# Create analysts
def create_analysts(
        state: ParentState, config: RunnableConfig, store: BaseStore
    ):
    
    """ Create analysts """
    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    namespace = ("active_application", user_id)
    memories = store.search(namespace)
    if memories:
        active_application = memories[0].value
    else:
        active_application = None
    print(f'Active application: {active_application}')
    
    # job = state['active_application']['posting']
    job = active_application['posting']
    # interview_notes = state['active_application']['interview_notes'] # TODO: add past interview notes to prompt
    max_analysts = state.get('max_analysts', 2)
    human_analyst_feedback = state.get('human_analyst_feedback', '')
        
    # Enforce structured output
    structured_llm = model.with_structured_output(Perspectives)

    # System message
    system_message = ANALYST_INSTRUCTIONS.format(
        job=job,
        human_analyst_feedback=human_analyst_feedback, 
        max_analysts=max_analysts
    )

    # Generate question 
    analysts = structured_llm.invoke(
        [SystemMessage(content=system_message)]+[HumanMessage(content="Generate the set of analysts.")]
    )
    
    # Write the list of analysis to state
    return {
        "analysts": analysts.analysts
    }

# Human feedback
def human_feedback(state: ParentState):
    """ No-op node that should be interrupted on """
    # TODO: ask the user if there's any specific things they know the company is looking for
    pass

# Continue interrupt
def should_continue(state: ParentState):
    """ Return the next node to execute """

    # Check if human feedback
    human_analyst_feedback=state.get('human_analyst_feedback', None)
    if human_analyst_feedback:
        return "create_analysts"
    
    # Otherwise end
    return "conduct_interview"

# Conduct Interview Subgraph
from langchain_core.messages import get_buffer_string
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

# Interview State
class InterviewState(MessagesState):
    # active_application: Application
    final_report: str
    sections: Annotated[list, operator.add] # Final key we duplicate in outer state for Send() API
    max_num_turns: int # Number turns of conversation
    analyst: Analyst # Analyst asking questions
    interview: str # Interview transcript
  
# generate questions
def generate_question(state: InterviewState, config: RunnableConfig, store: BaseStore):
    """ Node to generate a question """

    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    namespace = ("annotated_resume", user_id)
    memories = store.search(namespace)
    if memories:
        annotated_resume = memories[0].value
    else:
        annotated_resume = None
    
    # Get state
    analyst = state["analyst"]
    messages = state["messages"]

    # Generate question 
    
    system_message = QUESTION_INSTRUCTIONS.format(
        annotated_resume=annotated_resume,
        goals=analyst.persona,
    )
    question = model.invoke([SystemMessage(content=system_message)]+messages)
    question.name = "expert"
    
    # Write messages to state
    return {"messages": [question]}

# generate answer
def generate_answer(state: InterviewState, config: RunnableConfig, store: BaseStore):
    
    """ Node to answer a question """

    # Get state
    # analyst = state["analyst"]
    analyst = state["analyst"]
    messages = state["messages"]
    # context = state["context"]

    configurable = configuration.Configuration.from_runnable_config(config)
    user_id = configurable.user_id

    namespace = ("annotated_resume", user_id)
    memories = store.search(namespace)
    if memories:
        annotated_resume = memories[0].value
    else:
        annotated_resume = None

    namespace = ("documents", user_id)
    memories = store.search(namespace)
    if memories:
        documents = memories[0].value
    else:
        documents = None

        
    # Answer question
    system_message = ANSWER_INSTRUCTIONS.format(
        goals=analyst.persona,
        annotated_resume=annotated_resume,
        documents=documents
    )
    answer = model.invoke([SystemMessage(content=system_message)]+messages)
            
    # Name the message as coming from the candidate
    answer.name = "candidate"
    
    # Append it to state
    return {"messages": [answer]}

# save interview
def save_interview(state: InterviewState):
    
    """ Save interviews """

    # Get messages
    messages = state["messages"]
    
    # Convert interview to a string
    interview = get_buffer_string(messages)
    
    # Save to interviews key
    return {"interview": interview}

# conditional edge
def route_messages(state: InterviewState, 
                   name: str = "expert"):

    """ Route between question and answer """
    
    # Get messages
    messages = state["messages"]
    max_num_turns = state.get('max_num_turns', 2)

    # Check the number of expert answers 
    num_responses = len(
        [m for m in messages if isinstance(m, AIMessage) and m.name == name]
    )

    # End if expert has answered more than the max turns
    if num_responses >= max_num_turns:
        return 'save_interview'

    # This router is run after each question - answer pair 
    # Get the last question asked to check if it signals the end of discussion
    last_question = messages[-2]
    
    if "Thank you so much for your help" in last_question.content:
        return 'save_interview'
    return "ask_question"

# WEAKNESSES_INSTRUCTIONS = """critiquing the candidate's shortcomings and specific areas for improvement relating to the candidate's specific skills, experiences, or accomplishments."""

# STRENGTHS_INSTRUCTIONS = """the candidate's strengths and accomplishments relating to the candidate's specific skills, experiences, or accomplishments, and the job requirements."""

# EVALUATION_INSTRUCTIONS = """holistically evaluating the candidate's ability to meet the requirements for the job. Rate the candidate's overall fit for the job based on the interview on a scale of 0 through 100."""

# write section

# FOCUS_INSTRUCTIONS = {
#     "weaknesses": WEAKNESSES_INSTRUCTIONS,
#     "strengths": STRENGTHS_INSTRUCTIONS,
#     "evaluation": EVALUATION_INSTRUCTIONS
# }

# write sections
def write_section(state: InterviewState):
    """ Node to answer a question """

    # Get state
    interview = state["interview"]
    analyst = state["analyst"]
    # focus_instructions = FOCUS_INSTRUCTIONS[focus]
    # Write section using either the gathered source docs from interview (context) or the interview itself (interview)
    system_message = SECTION_WRITER_INSTRUCTIONS.format()
    section = model.invoke([SystemMessage(content=system_message)]+[HumanMessage(content=f"Here's the interview transpcript:\n{interview}")]) 
                
    # Append it to state
    print(section.content)
    return {"sections": [section.content]} 

# finalize interview
def finalize_interview(state: ParentState):
    """ The is the "reduce" step where we gather all the sections, combine them, and reflect on them to write the final interview report. """
    # Save full final report

    sections = state["sections"]
    formatted_str_sections = "\n\n".join([f"{section}" for section in sections])
    
    # Summarize the sections into a final report
    
    instructions = FINALIZE_INTERVIEW_INSTRUCTIONS.format(sections=formatted_str_sections)
    final_report = model.invoke([instructions]+[HumanMessage(content=f"Write the report conclusion")]) 
    return {"final_report": final_report}

interview_builder = StateGraph(InterviewState)
interview_builder.add_node("ask_question", generate_question)
interview_builder.add_node("answer_question", generate_answer)
interview_builder.add_node(save_interview)
interview_builder.add_node(write_section)

interview_builder.add_edge(START, "ask_question")
interview_builder.add_edge("ask_question", "answer_question")
interview_builder.add_conditional_edges("answer_question", route_messages,['ask_question','save_interview'])
interview_builder.add_edge("save_interview", "write_section")
interview_builder.add_edge("write_section", END)

# across_thread_memory = InMemoryStore()
# memory = MemorySaver()
# interview_graph = interview_builder.compile(
#   checkpointer=memory,
#   store=across_thread_memory
# ).with_config(run_name="Conduct Interviews")


from langgraph.constants import Send

def initiate_all_interviews(state: ParentState):
    """ This is the "map" step where we run each interview sub-graph using Send API """    

    # Check if human feedback
    human_analyst_feedback=state.get('human_analyst_feedback')
    if human_analyst_feedback:
        # Return to create_analysts
        return "create_analysts"

    # Otherwise kick off interviews in parallel via Send() API
    else:
        # topic = state["topic"]
        return [Send("conduct_interview", {"analyst": analyst,
                                           "messages": [HumanMessage(
                                               content=f"Let's begin the interview."
                                           )
                                                       ]}) for analyst in state["analysts"]]
# Create the graph + all nodes
builder = StateGraph(ParentState, config_schema=configuration.Configuration)

# Define the flow of the memory extraction process
builder.add_node(hunter)
builder.add_node(update_resume)
builder.add_node(update_job_applications)
builder.add_node(update_documents)
builder.add_node(update_instructions)
builder.add_node(begin_interview)
builder.add_node(create_analysts) 
builder.add_node(human_feedback)
builder.add_node("conduct_interview", interview_builder.compile())
builder.add_node(finalize_interview)

builder.add_edge(START, "hunter")
builder.add_conditional_edges("hunter", route_message)
builder.add_edge("update_resume", "hunter")
builder.add_edge("update_job_applications", "hunter")
builder.add_edge("update_documents", "hunter")
builder.add_edge("update_instructions", "hunter")
builder.add_edge("begin_interview", "create_analysts")
builder.add_edge("create_analysts", "human_feedback")
builder.add_conditional_edges("human_feedback", initiate_all_interviews, ["create_analysts", "conduct_interview"])
builder.add_edge("conduct_interview", "finalize_interview")
builder.add_edge("finalize_interview", "hunter")

# Store for long-term (across-thread) memory
across_thread_memory = InMemoryStore()

# Checkpointer for short-term (within-thread) memory
within_thread_memory = MemorySaver()

# We compile the graph with the checkpointer and store
graph = builder.compile(checkpointer=within_thread_memory, store=across_thread_memory)
