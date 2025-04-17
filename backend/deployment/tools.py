from typing_extensions import TypedDict, Literal
"""
user: memory about the user (eg. facts, achievements)
instructions: user preferences on KG structure
"""
class UpdateMemory(TypedDict):
    """ Decision on what memory type to update """
    update_type: Literal['annotated_resume', 'instructions', 'application', 'document', 'active_application']
