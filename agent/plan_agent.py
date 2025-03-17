import asyncio

from model.agent import Agent
from boundary.llms.moonshot import moonshotChatReceiver
from prompts import system_prompt
from util.text_extractor import json_extractor
import boundary.googleCalendar

m_chat = moonshotChatReceiver(
    system_prompt=system_prompt.STUDY_PLAN_PROMPT,
    use_json=True
)

planAgent = Agent(m_chat, name="your_study_planner")






if __name__ == '__main__':
    mySchedule = """
    SEM Course Calendar Spring 2025 

    Week
    Dates
    SEM Project 
    Class Session 1
    Monday
    Class Session 2
    Wednesday
    Friday Recitations
    & Deadlines 
    #1
    Jan 13-15


    Course Kickoff;
    Activity: Activity Spaces
    Agile Methods; Activities: 
    SEM Terminology, XP


    #2
    Jan 20-22
    + Jan 24


    MLK Jr Day - No Class
    Lean Methods;
    Activity: Waste & Kanban
    Friday Recitation: TypeScript, React, Redux, StoryBook
    #3
    Jan 27-29
    Task 1: 
    Practice Library
    No Class - Building Maintenance (this week’s classes are on Wed and Friday)
    Project Context; Activities: Failure vs Success at Scale;
    Intro SEM Project Task 1
    Friday Class:
    Method Frameworks: DAD;
    Activities: RUP, DAD Exploration Quiz (due 2/5)
    #4
    Feb 3-5



    Task 2: 
    Method Selection
    Method Frameworks: SAFe & LeSS; Activity: LeSS Exploration Quiz (due 2/5); Intro Field Project
    Task 1 due Wed 2/5;
    Intro Task 2; 
    SE Measurement;
    Activity: GQM
    Field Project: Company selection due Sunday night; 
    Coding Warm-up due Sunday 2/9
    #5
    Feb 10-12
    + 14
    SEM Incident Response Application Introduction; 
    Activity: Reverse-Engineering
    Presentations on Method Frameworks Comparison
    Friday Class:
    DoD Workshop; 
    Task 2 due Sunday 2/16
    #6
    Feb 17-19
    Sprint 1
    Intro Sprint 1;
    Activity: Sprint Planning
    Cross-Team Coordination;
    Project Working Session
    Field Project: Interviewee and questions due Sunday night
    #7
    Feb 24-26
    Risks Management;
    Project Working Session
    Cross-Team Coordination;
    Project Working Session
    Sprint 1 due Sunday 3/2 
    (be ready to demo during Monday class after break)


    Mar 3-5
    Spring Break - No Classes
    #8
    Mar 10-12
    Activity: Sprint 1 Review
    Activity: Retrospective;
    Root Cause Analysis


    #9
    Mar 17-19
    Sprint 2
    Intro Sprint 2
    Activity: Sprint Planning
    Cross-Team Coordination;
    Project Working Session


    #10
    Mar 24-26
    Improvement Frameworks: CMMi and Essence; Activity: SEMAT Essence Reflection
    Activity: Backlog Refinement
    Sprint 2 due Sunday 3/30
    #11
    Mar 31 - Apr 2
    Activity: Sprint 2 Review
    Activity: Retrospective


    #12
    Apr 7-9
    Sprint 3
    Intro Sprint 3;
    Activity: Sprint Planning
    Field Project Presentations


    #13
    April 14-16
    Cross-Team Coordination; 
    Project Working Session
    Cross-Team Coordination; 
    Project Working Session
    Sprint 3 due Sunday 4/20
    #14
    April 21-23
    + 25
    Course Review
    Final Project Working Session
    Friday Class:
    SEM Project Final Presentations
    CATME peer and course evaluations due Friday night
    Examination Period
    No Classes - No Exam
    """

    # This is a test code for the plan agent. The plan agent is responsible for generating a study plan based on the user's schedule.
    # The plan agent takes a string of Markdown text as input, and generates a JSON array of tasks and due dates.
    # The plan agent can be tested by running this code and passing in a Markdown string as the argument to the send_message() method.
    plan = asyncio.run(planAgent.send_message(mySchedule,is_debug=True))
    print(plan)

