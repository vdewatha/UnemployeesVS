from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import date

# User profile schema

class Item(BaseModel):
    """ This is a single item in the user's Annotated Resume """
    content : str = Field(
        description="The content of the item",
        default=None
    )
    interview_notes: Optional[str] = Field(
        description="Interview notes relevant to the item",
        default=None
    )

class ItemCollection(BaseModel):
    """ This is a collection of items in the user's annotated resume """
    items: list[Item] = Field(
        description="The items in the collection",
        default_factory=list
    )
    notes: Optional[str] = Field(
        description="Notes relevant to the collection",
        default=None
    )

class AnnotatedResume(BaseModel):
    """This is the annotate resume of the user you are chatting with"""

    # required categories
    contact_info: ItemCollection = Field(
        description="""
            The user's contact information which may include the following and more
            (1) name (do not use nicknames), 
            (2) permanent address (or school/local address), 
            (3) phone number, and 
            (4) email address
            """,
            default=None
    )

    objective: Optional[Item] = Field(
        description="""
            A brief statement of the type of position for which the user wishes to be considered. 

            May be stated 
            (1) by job title, 
            (2) by level or type, 
            (3) in terms of the skills the user wishes to use or develop, or 
            (4) as a combination of all three.
            """,
        default=None
    )

    education: ItemCollection = Field(
        description="""
            The user's education history which may include the following and more
            (1) begin with most recent degree (omit high school if college degree has been earned),
            (2) other degrees received or anticipated, major (concentration), minor, and certificate program
            (3) date the degree was granted or expected
            (4) university name and location
            (5) GPA (if 3.0 or higher)
            (6) academic honors, scholarships, and awards
            (7) may include a section that involves relevant coursework
            (8) study abroad experiences (if any)
            """,
        default=None
    )

    technical_skills: ItemCollection = Field(
        description="Technical skills that the user has",
        default=None
    )

    experience: Optional[ItemCollection] = Field(
        description="""
            Work experience that the user has 
            (1) list job/positon title
            (2) organization/company name
            (3) location (city, state)
            (4) dates

            ALWAYS start with action verbs, such as "collaborated," "developed," "managed," "created," etc. to describe job tasks, activities, and accomplishments.
            
            Provide specific examples of accomplishments using statistics and numbers.

            Include paid paid experiences such as full-time, part-time, internships, summer jobs, assistantships, etc.

            Include unpaid internships, extended research, projects, and extracurricular activities, coursework, or class projects that often lead to valuable knowledge and skills.
            """,
        default=None
    )

    activities: Optional[ItemCollection] = Field(
        description="""
            Activities that the user has participated in or out of school, if not already covered under experiences. Include activities where the user has developed significant transferable skills, such as leadership and teamwork.
            """,
        default=None
    )

    skills: ItemCollection = Field(
        description="""
            Skills that the user has which may include
            (1) computer skills (hardware, software, programming languages, etc.)
            (2) foreign language proficiency (literate, fluent)
            """,
        default=None
    )

    non_academic_honors_and_awards: Optional[ItemCollection] = Field(
        description="Any non-academic awards and honors that the user has received",
        default=None
    )

    professional_affiliations: Optional[ItemCollection] = Field(
        description="Professional affiliations that the user has",
        default=None
    )

    other: Optional[ItemCollection] = Field(
        description="Any other pertinent information about the user such as citizenship, special licenses, certificates, clearances",
        default=None
    )

    references: Optional[ItemCollection] = Field(
        description="References that the user has",
        default=None
    )
# Job Posting schema

class Company(BaseModel):
    """ Employer details """
    name: Optional[str] = Field(description="The name of the company.", default=None)
    location: Optional[str] = Field(description="The primary location of the company or job.", default=None)
    industry: Optional[str] = Field(description="The industry in which the company operates.", default=None)

class SalaryRange(BaseModel):
    """ Salary range offered """
    min: Optional[float] = Field(description="Minimum salary offered.", default=None)
    max: Optional[float] = Field(description="Maximum salary offered.", default=None)
    currency: Optional[str] = Field(
        description="Currency in which the salary is paid (e.g., USD, EUR).", default=None
    )

class RequiredExperience(BaseModel):
    """ Experience requirements for the job """
    years: Optional[int] = Field(description="Number of years of experience required.", default=None)
    field: Optional[str] = Field(description="Relevant field of experience.", default=None)

class EmploymentType(BaseModel):
    """ Type of employment offered """
    type: Literal["Full-time", "Part-time", "Contract", "Temporary", "Internship"] = Field(
        description="Type of employment offered.",
        default=None
    )

class JobLocationType(BaseModel):
    """ Type of job location """
    type: Literal["Remote", "On-site", "Hybrid"] = Field(
        description="Type of job location.",
        default=None
    )

class JobPosting(BaseModel):
    """ Job Posting details including job title, company, location, and job description. """

    job_title: Optional[str] = Field(description="The title of the job position.", default=None)
    company: Optional[Company] = Field(
        description="Company details including name and location.", 
        default=None
    )
    employment_type: Optional[EmploymentType] = Field(
        description="Type of employment offered.",
        default=None
    )
    job_description: Optional[str] = Field(
        description="A detailed description of the job responsibilities and expectations.", default=None
    )
    qualifications: Optional[list[str]] = Field(
        description="List of required qualifications and skills.", default=None
    )
    responsibilities: Optional[list[str]] = Field(
        description="Key responsibilities associated with the job.", default=None
    )
    salary_range: Optional[SalaryRange] = Field(
        description="Salary range offered for the position.", default=None
    )
    benefits: Optional[list[str]] = Field(
        description="List of benefits offered with the job.", default=None
    )
    required_experience: Optional[RequiredExperience] = Field(
        description="Experience requirements for the job.", default=None
    )
    job_location_type: Optional[str] = Field(
        description="Indicates whether the job is remote, on-site, or hybrid.", default=None
    )
    application_deadline: Optional[date] = Field(
        description="Deadline for submitting applications.", default=None
    )
    contact_email: Optional[str] = Field(
        description="Contact email for application submission.", default=None
    )
    posting_date: Optional[date] = Field(
        description="Date when the job was posted.", default=None
    )
# Job Application schema

class Application(BaseModel):
    """ This is an instance of a job application """
    posting: JobPosting = Field(
        description="The job posting to which the user is applying",
        default=None
    )
    status: Literal["In Progress", "Submitted", "Rejected", "Interview Scheduled", "Offer Extended", "Offer Accepted", "Offer Declined"] = Field(
        description="The status of the job application",
        default="In Progress"
    )
    interview_notes: Optional[str] = Field(
        description="Notes from the interview process",
        default=None
    )

# FIXME: removing a job application leaves an empty list
class JobApplications(BaseModel):
    """This is the set of job applications that the user is working on or has completed"""
    applications: list[Application] = Field(
        description="List of job applications that the user is working on or has completed",
        default_factory=list
    )
# Documents Schema
class Document(BaseModel):
    """ This is a user document with content and source """
    title: str
    content: str
    source: str

class DocumentCollection(BaseModel):
    """ Collection of user's documents """
    documents: list[Document] = Field(
        description="List of user's documents",
        default_factory=list
    )
# Analyst
class Analyst(BaseModel):
    # affiliation: str = Field(
    #     description="Primary affiliation of the analyst.",
    # )
    name: str = Field(
        description="Name of the analyst."
    )
    role: str = Field(
        description="Role of the analyst in the context of the job posting.",
    )
    description: str = Field(
        description="Description of the analyst focus, concerns, and motives.",
    )
    @property
    def persona(self) -> str:
        return f"Name: {self.name}\nRole: {self.role}\nDescription: {self.description}\n"

class Perspectives(BaseModel):
    analysts: list[Analyst] = Field(
        description="Comprehensive list of analysts with their roles.",
    )